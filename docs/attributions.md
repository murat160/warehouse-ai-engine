# Attributions & licences — Murat AI

Murat AI is built on a stack of open-weight AI models. This file lists
each upstream model used by the engine, its licence, and the citation
you should include when publishing about results produced with it.

> ⚠️ Read the **Licence implications** section before any commercial use.

---

## Models in use

| Model | Used for | Provider | Licence | Commercial? |
|---|---|---|---|---|
| **NLLB-200 distilled-600M** | text translation across ru / tk / tr / en | Meta AI | **CC-BY-NC 4.0** | ❌ Non-commercial only |
| **Meta MMS-TTS (`facebook/mms-tts-tuk-script_latin`)** | Turkmen text-to-speech | Meta AI | **CC-BY-NC 4.0** | ❌ Non-commercial only |
| **OpenAI Whisper** (`tiny` / `base` / `small` / `medium`) | speech recognition (audio + video) | OpenAI | **MIT** | ✅ OK |
| **OpenAI cloud APIs** (gpt-4o-mini / tts-1 / whisper-1) — optional | translation / TTS for ru / tr / en when `OPENAI_API_KEY` is set | OpenAI | OpenAI Terms of Service | ✅ per their terms |
| **langdetect** | quick language ID for short text | Nakatani Shuyo | Apache 2.0 | ✅ OK |
| **yt-dlp** | media download from YouTube / TikTok / etc. | yt-dlp team | Unlicense | ✅ OK |

The full Python dependency list (FastAPI, Streamlit, SQLAlchemy, ffmpeg-python,
…) is in `requirements.txt` and `requirements-full.txt`. Each of those
packages carries its own licence — see PyPI.

---

## MMS-TTS — minimal usage snippet (matches `src/cloud/tts_mms.py`)

```python
from transformers import VitsModel, AutoTokenizer
import torch
import scipy.io.wavfile as wavfile

model = VitsModel.from_pretrained("facebook/mms-tts-tuk-script_latin")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-tuk-script_latin")

inputs = tokenizer("Salam, dünýä", return_tensors="pt")
with torch.no_grad():
    output = model(**inputs).waveform

scipy.io.wavfile.write(
    "out.wav",
    rate=model.config.sampling_rate,
    data=output.squeeze().cpu().numpy(),
)
```

In Murat AI this is wrapped by `MMSTurkmenTTS.synthesize(text, emotion=…)`
which adds an emotion-prefix, normalises the waveform and writes a
fresh-UUID WAV under `data/custom_voices/preview/` (or wherever the
caller points). See `src/cloud/tts_mms.py`.

## NLLB-200 — usage matches `src/cloud/translator.py`

`facebook/nllb-200-distilled-600M` is loaded once via
`AutoModelForSeq2SeqLM.from_pretrained` and cached in the `hf_cache`
docker volume. Translation routes for ru ↔ tk ↔ tr ↔ en are wired in
`src/cloud/config.py:SUPPORTED_ROUTES`.

---

## Citations (BibTeX)

If you publish demos, articles or research using Murat AI, please cite
the upstream papers.

### Meta MMS / MMS-TTS

```bibtex
@article{pratap2023mms,
    title  = {Scaling Speech Technology to 1,000+ Languages},
    author = {Vineel Pratap and Andros Tjandra and Bowen Shi and Paden Tomasello
              and Arun Babu and Sayani Kundu and Ali Elkahky and Zhaoheng Ni
              and Apoorv Vyas and Maryam Fazel-Zarandi and Alexei Baevski
              and Yossi Adi and Xiaohui Zhang and Wei-Ning Hsu and Alexis Conneau
              and Michael Auli},
    journal= {arXiv},
    year   = {2023}
}
```

### NLLB-200

```bibtex
@article{nllb2022,
    title  = {No Language Left Behind: Scaling Human-Centered Machine Translation},
    author = {{NLLB Team} and Costa-jussà, Marta R. and Cross, James and ÇelebI, Onur
              and Elbayad, Maha and Heafield, Kenneth and Heffernan, Kevin
              and Kalbassi, Elahe and Lam, Janice and Licht, Daniel and others},
    journal= {arXiv:2207.04672},
    year   = {2022}
}
```

### Whisper

```bibtex
@article{radford2022whisper,
    title  = {Robust Speech Recognition via Large-Scale Weak Supervision},
    author = {Alec Radford and Jong Wook Kim and Tao Xu and Greg Brockman
              and Christine McLeavey and Ilya Sutskever},
    journal= {arXiv:2212.04356},
    year   = {2022}
}
```

---

## Licence implications

### CC-BY-NC 4.0 (NLLB-200 + MMS-TTS)

The two Meta models we depend on for the core translation and the Turkmen
voice are released under **Creative Commons Attribution-NonCommercial 4.0**.
Plain English:

* ✅ Personal use, research, demos, open-source contributions, internal
  workflows, free educational content — all fine, just keep the citation.
* ❌ Selling translations / dub services, putting them behind a paid SaaS
  paywall, monetising ad-supported videos that consumed these models —
  technically **not allowed** by the licence.

If Murat AI moves towards commercial monetisation, the realistic options
are:

1. **Replace the model per language**:
   * ru / tr / en — already easy via OpenAI `gpt-4o` + `tts-1` (just set
     `OPENAI_API_KEY` and the engine routes through the OpenAI provider).
   * tk — there is **no equally-good commercial alternative right now**.
     Closest viable paths: a Coqui-XTTS fine-tune on Turkmen (CPML, also
     NC), a Whisper-based ASR-only pipeline with manual TTS pairing, or
     a custom-trained voice via ElevenLabs Voice Lab once they add tk.
2. **Negotiate a commercial licence** with Meta AI directly.
3. **Keep Turkmen voice non-commercial** and monetise only the
   text-translation / Russian-Turkish-English voiceover parts.

We treat this as an open architectural decision: the code paths are
provider-agnostic, so swapping the backend is a configuration change,
not a rewrite.

### MIT / Apache 2.0 / Unlicense

Everything else in the dependency tree is permissive — fine for both
research and commerce.

---

## Where this is enforced in the codebase

| Concern | File |
|---|---|
| Lazy model loading + graceful preview fallback | `src/cloud/tts_mms.py`, `src/cloud/translator.py`, `src/cloud/asr.py` |
| Provider routing (so a future commercial backend can take over) | `src/providers/base.py`, `src/providers/openai_provider.py`, `src/providers/fallback_provider.py` |
| Voice catalog metadata + Custom Voice consent gate | `src/voices/catalog.py`, `src/voices/custom_voices.py`, `src/api/routes_custom_voices.py` |
