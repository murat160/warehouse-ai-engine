"""Turkmen text-to-speech service.

The full self-hosted install uses Meta MMS-TTS. The Streamlit preview install
keeps heavy ML packages optional so the interface can open even without them.
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

_EMOTION_PREFIXES = {
    "neutral": "",
    "happy": "Şatlykly äheňde: ",
    "sad": "Gamgyn äheňde: ",
    "angry": "Gazaply äheňde: ",
}


class MMSTurkmenTTS:
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

    def synthesize(self, text: str, *, emotion: str = "neutral") -> str:
        if not text or not text.strip():
            raise ValueError("text is required")
        if self.tokenizer is None or self.model is None:
            raise RuntimeError(
                "Preview mode: TTS model is not installed. Use the VPS/full install for audio generation."
            )

        import numpy as np  # type: ignore
        import scipy.io.wavfile as wavfile  # type: ignore
        import torch  # type: ignore

        prefix = _EMOTION_PREFIXES.get(emotion, "")
        final_text = f"{prefix}{text}".strip()
        inputs = self.tokenizer(final_text, return_tensors="pt")
        with torch.no_grad():
            waveform = self.model(**inputs).waveform.squeeze().cpu().numpy()
        peak = float(np.max(np.abs(waveform))) or 1e-8
        pcm = np.int16(waveform / peak * 32767)
        path = OUT / f"{uuid.uuid4().hex}.wav"
        wavfile.write(str(path), rate=int(self.model.config.sampling_rate), data=pcm)
        return str(path)
