"""Turkmen text-to-speech powered by Meta MMS-TTS (Vits).

The model id ``facebook/mms-tts-tuk-script_latin`` produces a single neutral
voice. Real prosody control is not exposed by the checkpoint, so the
``emotion`` parameter is implemented as a soft Turkmen-language style prefix
("Şatlykly äheňde:" / "Gamgyn äheňde:" / …) that is read aloud as part of
the utterance. It is a heuristic, not a true emotion-aware TTS.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile
import torch
from transformers import AutoTokenizer, VitsModel

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
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self.model = VitsModel.from_pretrained(MODEL_ID)
        self.model.eval()

    def synthesize(self, text: str, *, emotion: str = "neutral") -> str:
        if not text or not text.strip():
            raise ValueError("text is required")
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
