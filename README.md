# 🕵️ OSINT Image Bot

A Telegram bot for image-based open-source intelligence. Send a photo, get two investigative paths back: face search across public platforms, or metadata extraction and reverse image search.

Built as a practical OSINT toolkit — the same techniques used in verifying a dating profile, fact-checking a screenshot, or sourcing an image for a news article, packaged into a chat interface.

---

## What it does

The bot receives an image, extracts its embedded metadata immediately, then offers two methods:

**Method 2 — Face Search**
Runs the image through facial recognition engines that index public social profiles, news sites, and databases. Returns ranked matches with confidence scores and source URLs so you can verify manually.

**Method 3 — Metadata & OSINT**
Extracts EXIF (camera, timestamps, GPS), runs Google Lens reverse search, splits the image into quadrant crops for background inspection, and sharpens text for readability. For engines that need a public URL, generates one-tap links to Yandex, Bing, and TinEye.

---

## Technology

**Runtime:** Python 3.10+ · `python-telegram-bot` v21 for the async Telegram interface · `aiohttp` for outbound HTTP to search engine APIs

**Image processing:** `Pillow` for format detection, EXIF parsing, cropping, filtering, and enhancement · `exifread` as a fallback metadata reader · `piexif` for tag decoding

**Search integrations:**
- **FaceCheck.ID** — reverse-engineered API client with upload → poll → result flow
- **Search4Faces** — public JSON API for VK, Odnoklassniki, TikTok, Clubhouse
- **PimEyes** — paid BYOK integration, wired but gated behind an API key
- **Google Lens** — via `google-lens-python`, plus direct URL builders for Yandex, Bing, TinEye

**Architecture:** Handlers stay thin — they receive updates, dispatch to services, and format results. Services own the logic: `exif_service` for metadata, `face_search` for Method 2 engines, `reverse_search` for Lens, `context_service` for cropping and enhancement. Adding a new engine means one function, one branch, one button.

**State:** Per-user session data held in `context.user_data` between callbacks, so users upload once and explore multiple tools without re-sending the image.

**Deployment:** Dockerfile and docker-compose included. Runs as a long-polling bot — no webhook, no port binding, works anywhere Python runs.

---

## The two constraints that shaped it

**Telegram strips EXIF from photos.** When a user sends an image as a photo, Telegram recompresses and removes all metadata before the bot ever sees it. The bot handles both paths — photo and document — and tells the user explicitly when metadata is missing and how to resend it to preserve it.

**Face search engines rate-limit by IP.** FaceCheck.ID allows roughly 10–20 free searches per hour per address. The bot includes a per-user cooldown to protect the shared IP on multi-user deployments.

---

## Legal note

The bot only surfaces public information — public pages indexed by search engines, metadata embedded in the file itself. No privacy controls are bypassed. It is intended for verification, fact-checking, and OSINT research. Using it to locate someone without consent, stalk, or dox is illegal in most jurisdictions and outside the scope of what the tool is meant to do.
