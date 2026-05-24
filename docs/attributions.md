# Attributions & licences — Murat AI

Murat AI is **licence-clean by default**: every default backend is
released under a permissive licence (Apache 2.0 / MIT / Unlicense) or is a
commercial cloud API whose output you own. Components that ship under
Creative Commons NonCommercial are **disabled by default** and only
become active when an operator explicitly opts in.

This document lists each upstream model, its licence, and the citation
you should include when publishing results produced with it.

---

## Default stack (all permissive)

| Component | Used for | Provider | Licence | Commercial use? |
|---|---|---|---|---|
| **MADLAD-400** (`google/madlad400-3b-mt`) | text translation across ru / tk / tr / en | Google Research | **Apache 2.0** | ✅ yes |
| **OpenAI Whisper** (`tiny` / `base` / `small` / `medium`) | speech recognition (audio + video) | OpenAI | **MIT** | ✅ yes |
| **OpenAI cloud APIs** (gpt-4o-mini / tts-1 / whisper-1) — optional | translation / TTS for ru / tr / en when `OPENAI_API_KEY` is set | OpenAI | OpenAI Terms of Service (output owned by you) | ✅ per their terms |
| **langdetect** | quick language ID for short text | Nakatani Shuyo | **Apache 2.0** | ✅ yes |
| **yt-dlp** | media download from YouTube / TikTok / etc. | yt-dlp team | **Unlicense** (public domain) | ✅ yes |
| **ffmpeg** (LGPL build in the slim Docker image) | audio/video transcoding | FFmpeg | **LGPL 2.1+** (safe to redistribute) | ✅ yes |

Every Python dependency in `requirements.txt` / `requirements-full.txt`
(FastAPI, Streamlit, SQLAlchemy, pydantic, transformers, torch, soundfile,
scipy, numpy, ffmpeg-python, pytest, …) is published under Apache 2.0,
MIT, BSD or an OSI-approved compatible licence. None are copyleft beyond
ffmpeg's LGPL.

---

## Opt-in components (CC-BY-NC, off by default)

These models give very high quality output for Turkmen but ship under
**Creative Commons Attribution-NonCommercial 4.0**. They are wired up in
code but require an explicit env-var flag to activate. Use them ONLY for
personal, research, demo or open-source projects — **never for paid SaaS
or ad-monetised products**.

| Component | Used for | Activation | Licence |
|---|---|---|---|
| `facebook/nllb-200-distilled-600M` | smaller / faster translation alternative | `MURAT_AI_TRANSLATION_MODEL=facebook/nllb-200-distilled-600M` | **CC-BY-NC 4.0** |
| `facebook/mms-tts-tuk-script_latin` | offline Turkmen text-to-speech | `MMS_TTS_TUK_ENABLED=true` | **CC-BY-NC 4.0** |

If you turn either on, you accept Meta's NonCommercial restriction for
your deployment. The README, `.env.production.example` and
`docs/licensing.md` all surface this clearly so no operator can flip the
flag accidentally.

---

## How to keep your deployment fully commercial-friendly

1. **Translation** — leave the default `MURAT_AI_TRANSLATION_MODEL=google/madlad400-3b-mt`.
   It is Apache 2.0 and covers all four languages we ship.
2. **Turkmen voice (TTS)** — pick ONE of:
   * a commercial cloud TTS where output belongs to you: OpenAI `tts-1`,
     Google Cloud TTS (`tk-TM` Standard / Wavenet voices), ElevenLabs,
     Azure Speech. Add the key in `.env.production`, plug the provider
     into `src/providers/`.
   * **`espeak-ng`** (low-quality robotic fallback, MIT-compatible). The
     audio it generates is yours.
   * a model you trained yourself on data you own.
3. **STT** — `openai-whisper` is MIT, safe for any use.

For ru / tr / en there are several commercial-friendly options:
DeepL API, Google Cloud Translation v3, Microsoft Azure Translator,
OpenAI gpt-4o-mini. All four can be wired through the
`TranslationProvider` interface (`src/providers/base.py`) and run side by
side with MADLAD-400.

---

## Citations (BibTeX)

If you publish demos, articles or research using Murat AI, please cite
the upstream papers.

### MADLAD-400

```bibtex
@misc{kudugunta2023madlad400,
    title  = {MADLAD-400: A Multilingual And Document-Level Large Audited Dataset},
    author = {Sneha Kudugunta and Isaac Caswell and Biao Zhang and Xavier Garcia
              and Christopher A. Choquette-Choo and Katherine Lee
              and Derrick Xin and Aditya Kusupati and Romi Stella
              and Ankur Bapna and Orhan Firat},
    year   = {2023},
    eprint = {2309.04662},
    archivePrefix = {arXiv},
    primaryClass  = {cs.CL}
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

### Meta MMS / MMS-TTS *(only if you opt in)*

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

### NLLB-200 *(only if you opt in)*

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

---

## Licence implications

### Default deployment

Out of the box Murat AI uses MADLAD-400 (Apache 2.0) + Whisper (MIT) +
permissive Python libs + LGPL ffmpeg. You can ship a paid SaaS, embed it
in a commercial product or use it inside a company without licence
friction. The first-party code in this repo is your own.

### LGPL note for ffmpeg

The `ffmpeg` binary baked into the Docker image (`python:3.11-slim` +
`apt install ffmpeg`) is the **LGPL build** — safe to redistribute inside
a proprietary product. Murat AI never enables GPL-only encoders like
`libx264` / `libx265` (we use only `pcm_s16le` + `aac` + `mp4` container).
If you ever add `-c:v libx264` in the dubbing pipeline, re-read the
[FFmpeg legal page](https://www.ffmpeg.org/legal.html) — that flips the
redistributable result to GPL.

### Repository licence file

The repo itself currently ships **without a top-level `LICENSE`** file.
By default this means: "all rights reserved" on the first-party code,
which is fine for a private project. Recommended action before any
public release: add an explicit `LICENSE` (MIT or Apache-2.0) covering
the first-party code.

---

## Where this is enforced in the codebase

| Concern | File |
|---|---|
| Default translation backend (MADLAD-400 Apache 2.0) | `src/cloud/config.py` |
| MADLAD vs NLLB tokenizer branching | `src/cloud/translator.py` |
| Lazy model loading + graceful preview fallback | `src/cloud/translator.py`, `src/cloud/asr.py`, `src/cloud/tts_mms.py` |
| MMS-TTS is opt-in (`MMS_TTS_TUK_ENABLED=false` by default) | `.env.production.example`, `src/cloud/tts_mms.py` |
| Provider routing (so a commercial backend can take over) | `src/providers/base.py`, `src/providers/openai_provider.py`, `src/providers/fallback_provider.py` |
| Voice catalog metadata + Custom Voice consent gate | `src/voices/catalog.py`, `src/voices/custom_voices.py`, `src/api/routes_custom_voices.py` |
