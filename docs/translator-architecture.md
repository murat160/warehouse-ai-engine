# Translator architecture

This document describes the AI translation / speech / video subsystem that
lives in `warehouse-ai-engine`. It is intentionally a **separate** repository
from `warehouse-ecosystem` and is not coupled to the customer, courier,
seller or admin applications.

## Goals

1. High-quality bidirectional translation between **ru, tk, tr, en**.
2. Priority direction: **ru ↔ tk**, with a clean literary register in both
   languages and idiomatic Turkmen with proper diacritics.
3. Speech recognition (audio + video → text) and speech synthesis
   (text → audio) for all four languages.
4. End-to-end video dubbing scaffolding so we can iterate quickly.
5. Provider-agnostic design: any backend that fulfils the abstract interface
   can be plugged in.

## Module layout

```
src/
  config.py                # pydantic Settings, env-only secrets
  translator/
    languages.py           # supported languages + pair validation
    glossary.py            # ru<->tk literary glossary (extensible)
    quality_check.py       # heuristic post-translation QA
    translator_service.py  # orchestrator (provider + glossary + QA)
  speech/
    speech_to_text.py      # STT facade
    text_to_speech.py      # TTS facade with per-language routing
  video/
    video_processor.py     # ffmpeg wrappers (extract / replace audio)
    subtitles.py           # SRT / WebVTT formatting
    dubbing_pipeline.py    # STT -> translate -> TTS -> mux
  providers/
    base.py                # TranslationProvider / STTProvider / TTSProvider
    openai_provider.py     # OpenAI: gpt-4o-mini, whisper-1, tts-1
    fallback_provider.py   # Meta MMS-TTS for tk; clear errors elsewhere
  api/
    schemas.py             # pydantic request/response models
    main.py                # FastAPI factory
docs/
  translator-architecture.md
tests/                     # unit + API tests with fake providers
```

## Translation flow

```
TranslateRequest
        │
        ▼
TranslatorService.translate()
        │
        ├── LanguagePair.of(src, tgt)            # validate + canonicalise
        │
        ├── primary.translate(literary=is_priority)
        │       ↳ falls back to FallbackProvider on ProviderError
        │
        ├── Glossary.apply()                     # ru<->tk literary fixes
        │
        ├── quality_check.check()                # script + length + diacritics
        │
        └── TranslationResult { text, provider, latency, quality, notes }
```

The `literary=True` hint is set automatically for the **ru ↔ tk** pair and
asks the provider to produce a clean, idiomatic register. The glossary is
applied **after** the provider and only for explicitly listed terms — it is
designed to fix style, not to inject translations into otherwise correct
output.

## Speech flow

* **STT** (`SpeechToText`): wraps an `STTProvider`. Default provider is
  OpenAI Whisper. Designed so we can swap in `whisper.cpp` /
  `faster-whisper` / MMS-ASR by adding a new provider class.
* **TTS** (`TextToSpeech`): wraps two providers (`primary`, `fallback`)
  and routes per language. For `tk` we prefer the **Meta MMS-TTS**
  (`facebook/mms-tts-tuk-script_latin`) provider when it is enabled,
  because cloud multilingual voices currently render Turkmen poorly.
  For `ru / tr / en` we use the primary provider.

## Video / dubbing flow

```
video_in.mp4
   │ extract_audio (ffmpeg)
   ▼
source.wav ──► STT.transcribe(with_segments=True) ──► [TranscriptSegment]
                                                          │
                                                          ▼
                                       per-segment Translator.translate()
                                                          │
                                                          ▼
                                         TTS.synthesize(full_text)
                                                          │
                                                          ▼
                                                      dubbed.wav
   │ replace_audio (ffmpeg)
   ▼
video_out.mp4   + source.srt + target.srt
```

The first iteration concatenates the translated transcript and dubs it as
one track. A future iteration should align each TTS clip to the original
segment timing (silence padding / time-stretch) for proper lip-sync.

## Providers

| Capability  | Primary         | Fallback                 |
|-------------|-----------------|--------------------------|
| Translation | OpenAI (gpt-4o) | Disabled by default      |
| STT         | OpenAI Whisper  | (whisper.cpp — todo)     |
| TTS ru/tr/en| OpenAI tts-1    | (none)                   |
| TTS tk      | OpenAI tts-1    | **Meta MMS-TTS (Vits)**  |

A provider declares availability via `is_available(...)`. The orchestrator
queries this before each call so the fallback is engaged automatically when
the primary lacks credentials or fails.

## Configuration

All settings come from environment variables (see `.env.example`). No
secrets are stored in code or in the repository:

* `OPENAI_API_KEY` — translation / STT / TTS for ru/tr/en.
* `MMS_TTS_TUK_ENABLED=true` — enable the offline Turkmen TTS fallback.
* `TRANSLATOR_USE_GLOSSARY` — toggle glossary post-processing.
* `TRANSLATOR_QUALITY_CHECK` — toggle heuristic QA.
* `TRANSLATOR_LATENCY_BUDGET` — soft per-request budget in seconds; a note
  is added to the response when exceeded (default 0.3).

## Roadmap

* Per-segment dubbing alignment with optional time-stretching.
* Domain glossaries for warehouse / e-commerce vocabulary loaded from JSON.
* Streaming endpoints (`/v1/translate/stream`, `/v1/tts/stream`).
* Optional `whisper.cpp` STT fallback to remove the OpenAI dependency for
  air-gapped deployments.
