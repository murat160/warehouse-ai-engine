# AI agents / channels

A **channel** is a reusable bundle of translation/TTS settings backed by
its own glossary and Translation Memory. A user can run 10 / 50 / 100
channels simultaneously — each with its own voice, register and
vocabulary. The active channel is chosen in the Streamlit sidebar; the
HTTP API accepts the channel id on every translation call.

## Schema

`channels` table (SQLAlchemy model in `src/storage/models.py`):

| column          | type    | meaning                                       |
|-----------------|---------|-----------------------------------------------|
| id              | uuid    | primary key                                   |
| name            | string  | unique human label                            |
| description     | text    | optional                                      |
| primary_lang    | string  | source language by default (`ru` / `tk` / …)  |
| target_lang     | string  | preferred target language (nullable)          |
| style           | string  | one of the 15 `TranslationStyle` codes        |
| tone            | string  | one of the 16 `DeliveryTone` codes (nullable) |
| emotion         | string  | one of the 7 `Emotion` codes                  |
| voice_id        | string  | id from the voice catalog (nullable)          |
| voice_use_case  | string  | `text` / `video` / `audio` / `dubbing`        |
| dubbing_notes   | text    | free-form notes for the dubbing pipeline      |
| created_at, updated_at | datetime |                                       |

Glossary and Translation Memory rows have an optional `channel_id`
foreign key — `NULL` rows are **global**, channel-scoped rows win when a
channel is active.

## Priority of corrections

1. **Channel-specific Translation Memory** — exact-segment short-circuit.
2. **Global Translation Memory** — exact-segment short-circuit.
3. The provider (OpenAI / NLLB-200) with the channel's style/tone/emotion.
4. The static curated ru↔tk glossary.
5. **Global user glossary**.
6. **Channel-specific user glossary** (always wins over the global one).

This means a correction saved to a channel always overrides both the
model output and any global rule.

## Recommended starter channels

| name              | style          | tone         | emotion      | voice                |
|-------------------|----------------|--------------|--------------|----------------------|
| Блог              | blogger        | friendly     | excited      | blogger_voice        |
| Новости           | news           | confident    | serious      | news_voice           |
| Туркменская культура | cultural    | respectful   | warm         | tk_cultural          |
| Улица             | street         | energetic    | excited      | street_voice         |
| Детский           | children       | warm         | warm         | child_storyteller    |
| Реклама           | advertising    | energetic    | happy        | advertising_voice    |
| Документы         | formal         | calm         | neutral      | male_adult           |
| Аудиокнига        | literary       | deep         | warm         | calm_voice           |
| Кинодубляж        | dramatic       | deep         | serious      | dramatic_voice       |
| Эксперт / обучение| expert         | confident    | neutral      | education_voice      |

## REST API

```
GET    /v1/channels                       list channels
POST   /v1/channels                       create
GET    /v1/channels/{id}                  read
PATCH  /v1/channels/{id}                  partial update
DELETE /v1/channels/{id}                  cascade-deletes channel-scoped
                                          glossary and TM rows
```

Every translation call accepts an optional `channel_id`:

```bash
curl -X POST http://localhost:8000/v1/translate \
  -H "Content-Type: application/json" \
  -d '{
        "text": "Спасибо за заказ",
        "source_lang": "ru",
        "target_lang": "tk",
        "channel_id": "<uuid>",
        "style": "blogger",
        "tone": "friendly",
        "emotion": "warm"
      }'
```

If both a channel and explicit `style`/`tone`/`emotion` are supplied, the
explicit values win — the channel only provides defaults.

## UI flow

1. **Sidebar → Channels** picker: choose the active channel (or "Global").
2. **Translate** tab inherits the channel's defaults; you can still
   override style / tone / emotion / voice per request.
3. **Replace translation** popover saves into the active channel's TM if a
   channel is selected, otherwise into the global TM.
4. **Add to dictionary** popover saves into the active channel's glossary
   if a channel is selected, otherwise into the global glossary.
5. **Channels** tab provides full CRUD + an "Activate" button per row.

## Future entities (planned, not yet shipped)

The schema is intentionally light so we can grow without migrations:

* `users` — when multi-tenant deployments are needed.
* `video_projects`, `dubbing_projects` — to persist a media pipeline run.
* `audio_outputs` — cached TTS renders keyed by `(text, voice_id, emotion)`.

These tables aren't part of the SQLAlchemy schema yet; they're documented
here so the contract is explicit when we add them.
