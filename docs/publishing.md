# Publishing — YouTube, TikTok, Instagram, Facebook, Telegram, X

The publishing module turns a finished translation/voiceover into a
**ready-to-paste package** for external platforms. It runs without any API
keys (you get a downloadable ZIP and platform-specific upload pages); when
you add OAuth credentials, the same data structure fuels direct upload.

> **Audio/video safety**: media files live ONLY on the local server under
> `data/publishing_inbox/` (in `.gitignore`). The repository stores only
> their path + JSON metadata. Audio extensions are also gitignored
> repo-wide as a safety net.

## Contents of a publishing package

| field             | meaning                                                              |
|-------------------|----------------------------------------------------------------------|
| `name`            | internal label                                                       |
| `kind`            | `video` or `audio`                                                   |
| `language`        | `ru` / `tk` / `tr` / `en`                                            |
| `channel_id`      | optional binding to a channel / AI agent                             |
| `title`           | the title that goes on YouTube / TikTok                              |
| `description`     | full description                                                     |
| `tags`            | list of comma-separated tags (used by YouTube)                       |
| `hashtags`        | list of #-prefixed tags (used by TikTok / Instagram / X)             |
| `target_platforms`| list of platforms to publish on                                      |
| `media_path`      | path to the local media file                                         |
| `status`          | `draft` / `exported` / `published`                                   |

## Supported platforms

| code        | label       | upload URL                                                | requires for direct API           |
|-------------|-------------|-----------------------------------------------------------|-----------------------------------|
| `youtube`   | YouTube     | https://studio.youtube.com/                               | Google Cloud OAuth (YouTube Data API v3) |
| `tiktok`    | TikTok      | https://www.tiktok.com/upload                             | TikTok Content Posting API + OAuth |
| `instagram` | Instagram   | https://www.instagram.com/                                | Instagram Graph API (Meta for Developers) |
| `facebook`  | Facebook    | https://www.facebook.com/                                 | Facebook Graph API + Page Token |
| `telegram`  | Telegram    | https://web.telegram.org/                                 | Telegram Bot API token (no OAuth) |
| `x`         | X (Twitter) | https://x.com/compose/post                                | X v2 API + OAuth 2.0 |

## What works out of the box (no credentials)

* Build a package: media + title + description + tags + hashtags + target platforms.
* Browse packages with filters: language, status, search.
* **Download a ZIP** that contains:
  * the media file (`media/<original-name>`)
  * `metadata.json` — full structured form
  * `ready_for_<platform>.txt` — per-platform copy-paste text
    with title / description / tags / hashtags / upload URL
  * `README.txt`
* **Open upload page** buttons that take you straight to YouTube Studio /
  TikTok / Instagram / Facebook / X / Telegram with the ZIP at hand.
* Mark a package as `exported` (auto on download) or `published`.

## Direct API upload (requires your credentials)

The scaffold is ready to grow into a one-click direct upload. Each
platform needs **your own** credentials — none of them ship with this repo:

### YouTube

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **YouTube Data API v3**.
3. Create OAuth 2.0 client (Desktop or Web).
4. Add the resulting JSON to a secret env var (`YOUTUBE_OAUTH_CLIENT_JSON`).
5. Implement `Uploader.upload(...)` in `src/publishing/uploaders/youtube.py`
   using `google-api-python-client` + `videos().insert`.

### TikTok

1. Apply on [TikTok for Developers](https://developers.tiktok.com/).
2. Request the **Content Posting API** scope (requires app review).
3. Implement OAuth 2.0 + `Direct Post` endpoint.

### Instagram / Facebook

1. Create an app on [Meta for Developers](https://developers.facebook.com/).
2. Connect a Facebook Page + Instagram Business account.
3. Use Graph API: `POST /<page-id>/videos` (Facebook) or
   container/publish endpoints (Instagram).

### Telegram

1. Create a bot via `@BotFather`, save the token.
2. Use `sendVideo` / `sendAudio` — no OAuth needed.

### X (Twitter)

1. Apply for **Free / Basic / Pro** on https://developer.x.com/.
2. Use OAuth 2.0 (PKCE) + `POST /2/tweets` with media.

When any of the above is implemented, plug the uploader into
`src/publishing/uploaders/<platform>.py` (one class per platform) and
extend `PublishingService` with a `publish(package_id, platform)` method
that calls the matching uploader. The repository / DTO layer already
carries everything those uploaders need.

## REST API

```
GET    /v1/publishing/platforms                    static catalog
GET    /v1/publishing                              list / search / filter
POST   /v1/publishing                              create draft
GET    /v1/publishing/{id}                         read
PATCH  /v1/publishing/{id}                         partial update
DELETE /v1/publishing/{id}                         delete (also removes media file)
POST   /v1/publishing/{id}/media                   upload/replace media file
GET    /v1/publishing/{id}/export                  download ZIP package
POST   /v1/publishing/{id}/publish                 mark as published
```

## UI flow

1. Tab **📤 Publish**.
2. **Create publishing package** — fill title / description / tags /
   hashtags / target platforms / language / channel; optionally upload
   the media file.
3. The package appears in the list with:
   * inline **video / audio preview** of the media,
   * **📦 Download ZIP** (one-click ZIP with metadata + per-platform text),
   * per-platform **Open upload page** buttons,
   * **Mark as published** / **Delete** controls.
4. Each platform also has a **reference card** at the bottom of the tab
   describing what's needed to wire direct upload.

## Schema (SQLAlchemy)

```
publishing_packages
├─ id                       uuid (pk)
├─ name                     string(160)
├─ kind                     string(16)            video | audio
├─ language                 string(8)             ru | tk | tr | en
├─ channel_id               FK channels.id        nullable, ON DELETE SET NULL
├─ title                    string(300)
├─ description              text
├─ tags_json                text                  JSON-encoded list
├─ hashtags_json            text                  JSON-encoded list
├─ target_platforms_json    text                  JSON-encoded list
├─ media_path               text                  local disk only
├─ media_filename           string(255)
├─ status                   string(20)            draft | exported | published
└─ created_at, updated_at   datetime
```
