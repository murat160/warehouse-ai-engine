# Custom Voice / «Мой голос»

The Custom Voice feature is **separate** from the built-in 23-voice catalog
(`docs/voice-profiles.md`). It lets the user upload or record their own
voice, configure how it should sound, save variants, bind it to a channel /
style / video use case and request a preview.

> **Audio safety**: voice samples are stored on the server's local disk
> only (`data/custom_voices/`, in `.gitignore`). They are **never**
> committed to git. The repository ships only code, docs and `.env.example`.

## Voice settings

Every Custom Voice carries six configuration axes plus a use-case:

| field        | values                                                                                          |
|--------------|-------------------------------------------------------------------------------------------------|
| `speed`      | `slow` / `normal` / `fast`                                                                       |
| `pitch`      | `low` / `normal` / `high`                                                                        |
| `emotion`    | `neutral` / `happy` / `sad` / `serious` / `confident` / `warm` / `energetic` / `dramatic` / `respectful` |
| `clarity`    | `normal` / `enhanced` / `studio`                                                                 |
| `intensity`  | `calm` / `medium` / `strong`                                                                     |
| `use_case`   | `text` / `blog` / `news` / `advertising` / `film` / `children` / `educational` / `dubbing`       |
| `language`   | `ru` / `tk` / `tr` / `en`                                                                        |

## Variants of one voice

A profile can mark another profile as its **parent** (`parent_id`) so the
same source voice can have multiple flavours:

```
"Мой голос" (parent)
  ├─ "Мой голос — обычный"
  ├─ "Мой голос — спокойный"
  ├─ "Мой голос — блогерский"
  ├─ "Мой голос — новостной"
  ├─ "Мой голос — драматичный"
  └─ "Мой голос — туркменская озвучка"
```

`CustomVoiceRepository.variants_of(parent_id)` returns every variant; the
UI exposes a «➕ Variant» button to seed the create form with the parent.

## Bindings

A Custom Voice can be optionally bound to:

* a **channel / AI agent** (`channel_id`) — the channel will prefer this voice
  for any rendering it does;
* a **translation style** (`bound_style`) — e.g. ”news” style picks the
  «Мой голос — новостной» variant;
* a **video use case** (`bound_video_use_case`) — `film`, `children`, etc.

Bindings are *hints*. Resolution priority when multiple voices match is:
exact `bound_style` > exact `bound_video_use_case` > exact `channel_id`
match > catalog default.

## Consent (mandatory)

`CustomVoiceProfile.consent_given` must be `True` before any row is
written. The repository raises `ConsentRequiredError` otherwise — both the
API (HTTP 400) and the UI (form blocks the submit) enforce this.

```python
voice = service.create(
    name="Мой голос",
    consent_given=True,                     # required
    language="ru",
    speed="normal", pitch="normal",
    emotion="neutral", clarity="normal",
    intensity="medium", use_case="text",
)
```

The default consent text persisted with each row is:

> «Я подтверждаю, что имею право использовать этот голос. /
>  I confirm that I have the right to use this voice.»

The consent timestamp is recorded automatically (`consent_at`).

## Audio sample handling

* Allowed formats: `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`, `.webm`.
* Hard cap: 25 MB per sample.
* Files are renamed with a fresh UUID and stored under
  `data/custom_voices/`. Only the path lives in SQLite.
* Deleting a Custom Voice deletes its sample file; replacing the sample
  also removes the previous one.
* The directory pattern is in `.gitignore`; audio extensions are
  ignore-listed at the repo root for an extra safety net.

## Preview

The «Прослушать пример» button (`POST /v1/custom-voices/{id}/preview`)
generates a short audio cue using the **closest catalog voice** that
matches the profile (same language; tone derived from the profile's
emotion; preference for matching speed/pitch). For Turkmen it routes
through Meta MMS-TTS (offline, no API key needed). For ru/tr/en the
preview requires a configured cloud TTS provider (`OPENAI_API_KEY`).

> Real voice cloning (using the uploaded sample as a speaker reference)
> is **not** part of this scaffold — a future provider (XTTS / Sesame /
> ElevenLabs / OpenVoice) plugs into `src/speech/text_to_speech.py` and
> `service.closest_catalog_voice(...)` becomes the fallback rather than
> the default. The UI already labels previews as approximations until
> cloning is wired in, so users are not misled.

## REST API

```
GET    /v1/custom-voices                           list / search / filter
POST   /v1/custom-voices                           create (consent required)
GET    /v1/custom-voices/{id}                      read
PATCH  /v1/custom-voices/{id}                      partial update
DELETE /v1/custom-voices/{id}                      delete (also removes sample file)

POST   /v1/custom-voices/{id}/sample               upload/replace audio sample
POST   /v1/custom-voices/{id}/preview              render preview audio
```

`GET /v1/custom-voices` accepts:

* `language=tk`
* `channel_id=<uuid>` (or `__global__` for unbound voices)
* `parent_id=<uuid>` (or `__none__` for top-level voices only)
* `q=<text>` — search by name

## UI flow

1. Tab **🎙️ Voices** → sub-tab **🎤 My Voices**.
2. **Create a custom voice** — fill name / language / settings, optionally
   upload or record a sample, optionally bind to a channel / style /
   video use case, **tick the consent checkbox**, press *Create voice*.
3. Each row has «🔊 Прослушать пример», «➕ Variant», «Edit», «🗑️ Delete».
4. The audio sample (if any) is rendered inline so the user can hear the
   reference clip they uploaded.

## Schema (SQLAlchemy)

```
custom_voices
├─ id                       uuid (pk)
├─ name                     string(120)
├─ description              text
├─ language                 string(8)            ru | tk | tr | en
├─ speed                    string(20)
├─ pitch                    string(20)
├─ emotion                  string(40)
├─ clarity                  string(20)
├─ intensity                string(20)
├─ use_case                 string(20)
├─ parent_id                FK custom_voices.id  (nullable, ON DELETE SET NULL)
├─ channel_id               FK channels.id       (nullable, ON DELETE SET NULL)
├─ bound_style              string(40)
├─ bound_video_use_case     string(40)
├─ sample_path              text                 (path on local disk)
├─ sample_duration          float
├─ consent_given            bool                 (must be true to insert)
├─ consent_text             text
├─ consent_at               datetime
├─ created_at, updated_at   datetime
```
