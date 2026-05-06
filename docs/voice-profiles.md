# Voice profiles

The engine ships a built-in catalog of **23 voice profiles** in
`src/voices/catalog.py`. Each profile is a self-contained dataclass that
describes a voice and tells the TTS layer which backend to render it with.

## Schema

```python
@dataclass(frozen=True)
class VoiceProfile:
    id: str                     # stable id ("male_neutral", "tk_cultural", …)
    label_ru: str
    label_en: str
    description: str

    gender: Gender              # male | female | child | teenager | neutral
    age_style: AgeStyle         # child | teen | young_adult | adult | senior
    tone: VoiceTone             # calm | warm | serious | energetic | friendly
                                # | official | dramatic | street | cultural

    languages: tuple[str, ...]  # codes from {ru, tk, tr, en}
    speed: SpeedPreset          # slow | normal | fast
    pitch: PitchPreset          # low  | normal | high
    default_emotion: str        # one of the Emotion codes
    use_cases: tuple[UseCase]   # subset of {text, video, audio, dubbing}

    provider: str               # "openai" | "mms" | "auto"
    backend_voice: str | None   # e.g. "alloy", "nova", "onyx", or HF model id
    notes: str | None
```

## The 23 built-in voices

| id                   | gender    | age          | tone        | languages         | provider | backend            |
|----------------------|-----------|--------------|-------------|-------------------|----------|--------------------|
| `male_neutral`       | male      | adult        | calm        | ru/tr/en          | openai   | onyx               |
| `female_neutral`     | female    | adult        | calm        | ru/tr/en          | openai   | nova               |
| `child_voice`        | child     | child        | warm        | ru/tr/en          | openai   | shimmer            |
| `teen_voice`         | teenager  | teen         | friendly    | ru/tr/en          | openai   | shimmer            |
| `male_young`         | male      | young_adult  | energetic   | ru/tr/en          | openai   | echo               |
| `female_young`       | female    | young_adult  | friendly    | ru/tr/en          | openai   | shimmer            |
| `male_adult`         | male      | adult        | serious     | ru/tr/en          | openai   | onyx               |
| `female_adult`       | female    | adult        | official    | ru/tr/en          | openai   | nova               |
| `male_senior`        | male      | senior       | dramatic    | ru/tr/en          | openai   | onyx               |
| `female_senior`      | female    | senior       | warm        | ru/tr/en          | openai   | nova               |
| `soft_voice`         | neutral   | adult        | warm        | ru/tr/en          | openai   | alloy              |
| `serious_voice`      | male      | adult        | serious     | ru/tr/en          | openai   | onyx               |
| `energetic_voice`    | neutral   | young_adult  | energetic   | ru/tr/en          | openai   | fable              |
| `calm_voice`         | neutral   | adult        | calm        | ru/tr/en          | openai   | alloy              |
| `news_voice`         | neutral   | adult        | official    | ru/tr/en          | openai   | onyx               |
| `blogger_voice`      | neutral   | young_adult  | friendly    | ru/tr/en          | openai   | shimmer            |
| `street_voice`       | neutral   | young_adult  | street      | ru/tr/en          | openai   | echo               |
| `education_voice`    | neutral   | adult        | calm        | ru/tr/en          | openai   | alloy              |
| `advertising_voice`  | neutral   | young_adult  | energetic   | ru/tr/en          | openai   | fable              |
| `dramatic_voice`     | male      | adult        | dramatic    | ru/tr/en          | openai   | onyx               |
| `child_storyteller`  | female    | adult        | warm        | ru/tr/en          | openai   | shimmer            |
| `tk_cultural`        | neutral   | adult        | cultural    | **tk**            | mms      | mms-tts-tuk        |
| `natural_video_voice`| neutral   | adult        | calm        | ru/tk/tr/en       | auto     | alloy + mms        |

## Routing rules

* **Turkmen** (`tk`) always renders through Meta MMS-TTS
  (`facebook/mms-tts-tuk-script_latin`) — cloud multilingual voices give
  poor Turkmen output. The single MMS voice is shaped via the
  translation-side prompt (`emotion`, `tone`) plus speed/pitch metadata
  applied by the TTS layer when ffmpeg post-processing is enabled.
* **Russian / Turkish / English** render through the configured cloud
  provider (default: OpenAI `tts-1`, with `backend_voice` selecting from
  `alloy / echo / fable / onyx / nova / shimmer`).
* `provider="auto"` profiles pick MMS for Turkmen and the cloud provider
  for everything else.

## Programmatic access

```python
from src.voices import (
    list_voices, voices_for_language, voices_for_use_case, get_voice, UseCase,
)

list_voices()                       # all 23
voices_for_language("tk")           # only Turkmen-capable
voices_for_use_case(UseCase.DUBBING)
get_voice("dramatic_voice")
```

## REST API

```
GET /v1/voices
GET /v1/voices?language=tk
GET /v1/voices?use_case=video
GET /v1/voices/{voice_id}
```

## Adding more voices

Custom voices live in `VOICE_CATALOG` (`src/voices/catalog.py`). To add a
new entry, append a `VoiceProfile(...)` literal — no migrations needed,
the UI and API pick it up automatically. To register a new TTS backend
(e.g. XTTS, Coqui, Sesame), add a `provider="..."` value and update the
TTS routing in `src/speech/text_to_speech.py`.
