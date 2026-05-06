# Style modes — Murat AI

**Murat AI** (source repo: `warehouse-ai-engine`) exposes three independent
axes a caller can combine to control the **how** of a translation. They sit on top of the language
pair (the **what**) and the optional channel (the **for whom**).

```
input → [TranslationStyle] × [DeliveryTone] × [Emotion] → translation
```

The default is `style=natural`, `tone=None`, `emotion=neutral` — a living,
native-sounding translation with no extra colouring. Literary and other
strong registers are explicit choices, not the default.

## Translation styles (15)

| code            | label_ru                  | use case                                              |
|-----------------|---------------------------|-------------------------------------------------------|
| `natural`       | Обычный естественный      | Default — living everyday language for any text/video |
| `blogger`       | Блогерский                | YouTube / TikTok / Reels / Shorts voiceover           |
| `conversational`| Разговорный               | Plain spoken language                                 |
| `street`        | Уличный / повседневный    | Modern slang-aware, never rude by default             |
| `literary`      | Литературный              | Books, narration — explicit choice only               |
| `formal`        | Официальный               | Documents, announcements, business                    |
| `news`          | Новостной                 | News-anchor delivery: clear, calm, confident          |
| `cultural`      | Культурный                | Native-feeling phrasing; critical for Turkmen         |
| `expressive`    | Эмоциональный             | Storytelling, strong videos                           |
| `dramatic`      | Драматичный               | Film dubbing, dramatic narration                      |
| `children`      | Детский                   | Soft, simple, child-friendly                          |
| `teen`          | Подростковый              | Teen-voice modern phrasing                            |
| `humorous`      | Юмористический            | Light, jokes culturally adapted                       |
| `advertising`   | Рекламный                 | Punchy, value-forward marketing copy                  |
| `expert`        | Экспертный                | Confident teaching with clear terminology             |

Each style ships a one-paragraph **prompt hint** that is injected into the
OpenAI system prompt. The offline NLLB-200 backend has no native style
control — for it the user-glossary and Translation Memory are the
practical enforcement points (see `docs/translator-architecture.md`).

## Delivery tones (16)

| code           | label_ru        | code           | label_ru        |
|----------------|-----------------|----------------|-----------------|
| `calm`         | Спокойный       | `firm`         | Жёсткий         |
| `confident`    | Уверенный       | `cultural`     | Культурный      |
| `friendly`     | Дружеский       | `modern`       | Современный     |
| `warm`         | Тёплый          | `traditional`  | Традиционный    |
| `serious`      | Серьёзный       | `simple`       | Простой         |
| `cheerful`     | Весёлый         | `deep`         | Глубокий        |
| `energetic`    | Энергичный      | `emotional`    | Эмоциональный   |
| `respectful`   | Уважительный    | `soft`         | Мягкий          |

Tone is **orthogonal** to style — you can ask for `style=blogger` +
`tone=respectful` to get an enthusiastic-but-polite voice. When `tone=None`
nothing extra is appended to the prompt.

## Emotions (7)

| code         | label_ru     | meaning                                  |
|--------------|--------------|------------------------------------------|
| `neutral`    | Нейтральная  | Default — no emotional colouring         |
| `happy`      | Радостная    | Upbeat synonyms                          |
| `sad`        | Грустная     | Subdued phrasing                         |
| `serious`    | Серьёзная    | Weighty wording, no jokes                |
| `excited`    | Восторженная | Excitement and momentum                  |
| `respectful` | Уважительная | Polite forms (Russian Вы / Turkmen Siz)  |
| `warm`       | Тёплая       | Warm, kind                               |

Emotion drives both the translation prompt **and** the Turkmen MMS-TTS
voice-prefix used during synthesis.

## Per-language guidance (always on)

In addition to the user's choice, the system prompt always carries
target-language guidance:

* **Turkmen** — write idiomatic, native-sounding Turkmen with proper
  diacritics (ä, ý, ň, ö, ü, ç, ş). Do not transliterate from Russian or
  English. Do not copy Russian sentence structure when Turkmen idiom
  would differ.
* **Russian** — write fluent, natural literary Russian. Translate the
  meaning, not the form.
* **English / Turkish** — write fluent native phrasing; respect target
  word order and politeness conventions.

## Picking a combination

| Use case             | style           | tone           | emotion       |
|----------------------|-----------------|----------------|---------------|
| Blog video           | `blogger`       | `friendly`     | `excited`     |
| News bulletin        | `news`          | `confident`    | `serious`     |
| Street vlog          | `street`        | `energetic`    | `excited`     |
| Turkmen culture clip | `cultural`      | `respectful`   | `warm`        |
| Film dub             | `dramatic`      | `deep`         | `serious`     |
| Children's story     | `children`      | `warm`         | `warm`        |
| Marketing promo      | `advertising`   | `energetic`    | `happy`       |
| Educational tutorial | `expert`        | `confident`    | `neutral`     |
| Default everyday text| `natural`       | _none_         | `neutral`     |

These triples are also the recommended defaults you would assign to a
**channel** (see `docs/ai-agent-profiles.md`).
