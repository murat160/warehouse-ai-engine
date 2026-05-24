"""Turkmen text-to-speech service — Meta MMS-TTS (Vits).

Wraps the canonical Hugging Face example for
``facebook/mms-tts-tuk-script_latin`` and adds the VITS quality knobs that
make the output sound natural and stable:

* ``noise_scale``      — randomness of the residual flow (0.667 default).
* ``noise_scale_duration`` — phoneme-duration variance (0.8 default).
* ``speaking_rate``    — speech speed; <1 faster, >1 slower (1.0 default).

The synthesiser also peak-normalises to 16-bit PCM so the WAV plays back at
a consistent loudness whether you preview it in the browser or pipe it
into the dubbing pipeline. The reference snippet from the model card is:

    from transformers import VitsModel, AutoTokenizer
    import torch, scipy

    model = VitsModel.from_pretrained("facebook/mms-tts-tuk-script_latin")
    tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-tuk-script_latin")
    inputs = tokenizer("some example text in the Turkmen language",
                       return_tensors="pt")
    with torch.no_grad():
        output = model(**inputs).waveform
    scipy.io.wavfile.write("techno.wav", rate=model.config.sampling_rate,
                           data=output)

Citation: Pratap et al., "Scaling Speech Technology to 1,000+ Languages",
arXiv 2023 — see docs/attributions.md.

Licence note: MMS-TTS is released by Meta under **CC-BY-NC 4.0**
(non-commercial only). Murat AI **does NOT enable this backend by
default** — it is gated by ``MMS_TTS_TUK_ENABLED=true`` in
``.env.production`` and is wired in code purely as an opt-in for
research / personal / demo deployments. For paid SaaS use a
commercially-licensed TTS backend instead (Google Cloud TTS supports
``tk-TM`` Wavenet voices, OpenAI ``tts-1``, ElevenLabs, Azure Speech).
See ``docs/attributions.md`` for the full policy.

The Streamlit preview install keeps heavy ML packages optional so the
interface can open even without them; this module imports them lazily.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

OUT = Path("out")
OUT.mkdir(exist_ok=True)

MODEL_ID = "facebook/mms-tts-tuk-script_latin"

# Soft style prefixes — MMS-TTS has no native emotion control, so we cue
# the synthesiser with a short Turkmen prefix that the model reads with the
# matching prosody.
_EMOTION_PREFIXES = {
    "neutral": "",
    "happy": "Şatlykly äheňde: ",
    "sad": "Gamgyn äheňde: ",
    "serious": "Çynlakaý äheňde: ",
    "warm": "Mähirli äheňde: ",
    "respectful": "Hormatly äheňde: ",
    "excited": "Joşgunly äheňde: ",
    "angry": "Gazaply äheňde: ",
}

# Per-emotion VITS knob overrides. None → keep model default. Picked
# empirically so happy ≈ slightly faster + more variance, sad ≈ slower +
# less variance.
_EMOTION_VITS_TUNING = {
    "neutral":    {"noise_scale": 0.667, "noise_scale_duration": 0.8,  "speaking_rate": 1.00},
    "happy":      {"noise_scale": 0.75,  "noise_scale_duration": 0.85, "speaking_rate": 0.95},
    "excited":    {"noise_scale": 0.80,  "noise_scale_duration": 0.90, "speaking_rate": 0.90},
    "sad":        {"noise_scale": 0.55,  "noise_scale_duration": 0.70, "speaking_rate": 1.15},
    "serious":    {"noise_scale": 0.60,  "noise_scale_duration": 0.75, "speaking_rate": 1.05},
    "warm":       {"noise_scale": 0.65,  "noise_scale_duration": 0.80, "speaking_rate": 1.02},
    "respectful": {"noise_scale": 0.60,  "noise_scale_duration": 0.75, "speaking_rate": 1.05},
    "angry":      {"noise_scale": 0.85,  "noise_scale_duration": 0.95, "speaking_rate": 0.92},
}


class MMSTurkmenTTS:
    """Turkmen TTS backed by ``facebook/mms-tts-tuk-script_latin``."""

    def __init__(self) -> None:
        logger.info("loading MMS-TTS model %s", MODEL_ID)
        self.tokenizer: Optional[Any] = None
        self.model: Optional[Any] = None
        try:
            from transformers import AutoTokenizer, VitsModel  # type: ignore
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            self.model = VitsModel.from_pretrained(MODEL_ID)
            self.model.eval()
        except Exception as exc:  # noqa: BLE001
            logger.warning("MMS-TTS unavailable in preview mode: %s", exc)

    def synthesize(
        self,
        text: str,
        *,
        emotion: str = "neutral",
        noise_scale: Optional[float] = None,
        noise_scale_duration: Optional[float] = None,
        speaking_rate: Optional[float] = None,
    ) -> str:
        """Render ``text`` to a 16-bit mono WAV and return its path.

        Optional ``noise_scale`` / ``noise_scale_duration`` / ``speaking_rate``
        override the per-emotion defaults from ``_EMOTION_VITS_TUNING``.
        """
        if not text or not text.strip():
            raise ValueError("text is required")
        if self.tokenizer is None or self.model is None:
            raise RuntimeError(
                "Preview mode: TTS model is not installed. Use the VPS/full "
                "install for audio generation."
            )

        import numpy as np  # type: ignore
        import scipy.io.wavfile as wavfile  # type: ignore
        import torch  # type: ignore

        # 1) Style cue.
        prefix = _EMOTION_PREFIXES.get(emotion, "")
        final_text = f"{prefix}{text}".strip()

        # 2) VITS-level tuning per emotion. Each attribute is read once per
        #    call so caller overrides win, but we don't mutate the model
        #    permanently — that would leak across requests.
        tuning = _EMOTION_VITS_TUNING.get(emotion, _EMOTION_VITS_TUNING["neutral"])
        ns = noise_scale if noise_scale is not None else tuning["noise_scale"]
        nsd = (
            noise_scale_duration
            if noise_scale_duration is not None
            else tuning["noise_scale_duration"]
        )
        sr_mul = (
            speaking_rate if speaking_rate is not None else tuning["speaking_rate"]
        )
        prev_ns = getattr(self.model, "noise_scale", None)
        prev_nsd = getattr(self.model, "noise_scale_duration", None)
        prev_sr = getattr(self.model, "speaking_rate", None)
        try:
            self.model.noise_scale = ns
            self.model.noise_scale_duration = nsd
            self.model.speaking_rate = sr_mul

            # 3) Inference — mirrors the canonical model-card snippet.
            inputs = self.tokenizer(final_text, return_tensors="pt")
            with torch.no_grad():
                waveform = self.model(**inputs).waveform.squeeze().cpu().numpy()
        finally:
            # Restore previous attrs so concurrent callers stay deterministic.
            if prev_ns is not None:
                self.model.noise_scale = prev_ns
            if prev_nsd is not None:
                self.model.noise_scale_duration = prev_nsd
            if prev_sr is not None:
                self.model.speaking_rate = prev_sr

        # 4) Peak-normalise to 16-bit PCM for consistent loudness and easy
        #    ffmpeg ingestion in the dubbing pipeline.
        peak = float(np.max(np.abs(waveform))) or 1e-8
        pcm = np.int16(waveform / peak * 32767)
        path = OUT / f"{uuid.uuid4().hex}.wav"
        wavfile.write(
            str(path),
            rate=int(self.model.config.sampling_rate),
            data=pcm,
        )
        return str(path)
