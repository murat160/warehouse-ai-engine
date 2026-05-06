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
6. **The engine learns over time** — a user-editable glossary and a
   translation memory persist corrections so the same input is translated
   correctly on subsequent calls.

## Module layout

```
src/
  config.py                # pydantic Settings, env-only secrets
  translator/
    languages.py           # supported languages + pair validation
    glossary.py            # static curated ru<->tk literary glossary
    user_glossary.py       # runtime user glossary (DB-backed)
    translation_memory.py  # whole-segment overrides
    styles.py              # 8 style/emotion profiles + prompt hints
    quality_check.py       # heuristic post-translation QA
    translator_service.py  # orchestrator: TM + provider + glossaries + QA
  speech/
    speech_to_text.py      # STT facade
    text_to_speech.py      # TTS facade with per-language routing
  video/
    video_processor.py     # ffmpeg wrappers (extract / replace audio)
    subtitles.py           # SRT / WebVTT formatting
    dubbing_pipeline.py    # STT -> translate -> TTS -> mux
  storage/
    db.py                  # SQLAlchemy engine + session factory
    models.py              # ORM: GlossaryEntry, TranslationMemoryEntry
    repositories.py        # CRUD + search for both tables
  cloud/                   # NLLB-200 / Whisper / MMS-TTS implementation
  ui/
    theme.py               # Streamlit CSS theme
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
TranslateRequest { text, src, tgt, style }
        │
        ▼
TranslatorService.translate()
        │
        ├── LanguagePair.of(src, tgt)            # validate + canonicalise
        │
        ├── TranslationMemoryService.lookup()    # exact-match shortcut
        │       ↳ on hit: skip the model entirely, apply user glossary,
        │                 run QA, return immediately.
        │
        ├── primary.translate(style=…)           # OpenAI / NLLB; system
        │       ↳ falls back to FallbackProvider on ProviderError
        │       prompt is composed from the chosen StyleProfile + Turkmen /
        │       Russian target-side guidance.
        │
        ├── Glossary.apply()                     # static curated ru<->tk
        ├── UserGlossaryService.apply()          # ← USER RULES, highest priority
        │
        ├── quality_check.check()                # script + length + diacritics
        │
        └── TranslationResult { text, provider, latency, quality,
                                style, tm_hit, user_glossary_hits, notes }
```

### Why this order

* **TM first** — a curated whole-segment override is always more correct
  than running the model again. It also costs ~0ms.
* **Static glossary** — built-in ru↔tk literary fixes that ship with the
  package. Conservative, only applied if a known term appears verbatim.
* **User glossary last** — has the **highest** priority by design. Anything
  the operator added overrides both the model output and the curated set.

### Style / emotion

`TranslationStyle` enumerates eight registers: `neutral, respectful, warm,
formal, friendly, expressive, literary, casual`. Each profile carries:

* a Russian/English label and short description (used by the UI),
* a `prompt_hint` injected into the OpenAI system prompt,
* an optional `nllb_prefix` for offline NLLB translation framing.

Turkmen targets always receive an additional guidance block
(`TURKMEN_TARGET_GUIDANCE`) that asks the model to write idiomatic Turkmen
with proper diacritics instead of mirroring Russian sentence structure.

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

## Persistent storage (glossary + TM)

```
src/storage/
  models.py            # GlossaryEntry, TranslationMemoryEntry (SQLAlchemy)
  repositories.py      # GlossaryRepository, TranslationMemoryRepository
                       # — pure CRUD + search, no SQLAlchemy leaks upstream
  db.py                # engine factory; defaults to SQLite, honours DATABASE_URL
```

The translator depends on **repositories**, not on SQLAlchemy. To migrate
to PostgreSQL we only need to set `DATABASE_URL=postgresql+psycopg://…`.

### Glossary table (`glossary_entries`)

| column         | type         | notes                                |
|----------------|--------------|--------------------------------------|
| id             | UUID-hex     | primary key                          |
| source_lang    | string(8)    | indexed                              |
| target_lang    | string(8)    | indexed                              |
| source_text    | string(512)  | the term to match                    |
| target_text    | string(512)  | the replacement                      |
| case_sensitive | bool         | default false                        |
| whole_word     | bool         | default true                         |
| note           | text         | optional human comment               |
| created_at, updated_at | timestamps |                                |

### Translation memory (`translation_memory`)

| column        | type          | notes                                 |
|---------------|---------------|---------------------------------------|
| id            | UUID-hex      | primary key                           |
| source_lang   | string(8)     | indexed                               |
| target_lang   | string(8)     | indexed                               |
| source_text   | text          | original input                        |
| target_text   | text          | curated translation                   |
| source_hash   | string(64)    | sha256 of normalised source for lookup|
| score         | float         | confidence (default 1.0)              |
| note          | text          | optional comment                      |
| `(src,tgt,hash)` is unique — `upsert` keeps a single row per pair+input. |

### REST API

| Method | Path                          | Purpose                          |
|--------|-------------------------------|----------------------------------|
| GET    | `/v1/glossary?source_lang=ru&target_lang=tk&q=…` | search/list      |
| POST   | `/v1/glossary`                | create rule                      |
| PATCH  | `/v1/glossary/{id}`           | edit                             |
| DELETE | `/v1/glossary/{id}`           | remove                           |
| GET    | `/v1/memory?source_lang=…&q=…` | search/list TM                  |
| POST   | `/v1/memory`                  | upsert TM entry                  |
| PATCH  | `/v1/memory/{id}`             | edit                             |
| DELETE | `/v1/memory/{id}`             | remove                           |
| GET    | `/v1/styles`                  | list available style profiles    |

## Configuration

All settings come from environment variables (see `.env.example`). No
secrets are stored in code or in the repository:

* `OPENAI_API_KEY` — translation / STT / TTS for ru/tr/en.
* `MMS_TTS_TUK_ENABLED=true` — enable the offline Turkmen TTS fallback.
* `TRANSLATOR_USE_GLOSSARY` — toggle the static curated glossary.
* `TRANSLATOR_QUALITY_CHECK` — toggle heuristic QA.
* `TRANSLATOR_LATENCY_BUDGET` — soft per-request budget in seconds; a note
  is added to the response when exceeded (default 0.3).
* `DATABASE_URL` — SQLAlchemy URL for the glossary/TM database. Default is
  `sqlite:///data/warehouse_ai.db`. Use `postgresql+psycopg://user:pwd@host/db`
  to switch to PostgreSQL without code changes.

## Roadmap

* Per-segment dubbing alignment with optional time-stretching.
* Domain glossaries for warehouse / e-commerce vocabulary loaded from JSON.
* Streaming endpoints (`/v1/translate/stream`, `/v1/tts/stream`).
* Optional `whisper.cpp` STT fallback to remove the OpenAI dependency for
  air-gapped deployments.
