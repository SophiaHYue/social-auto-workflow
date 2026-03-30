# social-auto-workflow

全自動 AI 內容生成與多平台發佈工作流  
Fully automated AI content generation & multi-platform publishing workflow.

---

## Overview

This project uses GitHub Actions to run a daily Python workflow that:

1. **Generates AI content** – images (DALL·E / Stable Diffusion), short videos (Runway ML / MoviePy fallback), long videos (Pictory), and text captions / titles / hashtags (OpenAI).
2. **Publishes to multiple platforms** – Facebook, Instagram, TikTok, YouTube, and Pinterest.
3. **Collects analytics** – a weekly job gathers engagement metrics from every platform and saves CSV + JSON reports.

---

## Repository Layout

```
.
├── daily_update.py          # Orchestrates content generation + publishing
├── analytics_report.py      # Collects engagement data and saves reports
├── requirements.txt
├── .gitignore
│
├── config/
│   ├── api_keys.example.env # Template – copy to .env and fill in your keys
│   └── settings.py          # Configuration loader (reads .env / env vars)
│
├── scripts/
│   ├── generate_image.py    # DALL·E or Stable Diffusion image generation
│   ├── generate_video.py    # Runway ML (short) / Pictory (long) video generation
│   ├── generate_text.py     # OpenAI captions, titles, hashtags
│   ├── facebook.py          # Meta Graph API – Facebook publishing + insights
│   ├── instagram.py         # Meta Graph API – Instagram publishing + insights
│   ├── tiktok.py            # TikTok Business API – video publishing + analytics
│   ├── youtube.py           # YouTube Data API v3 – video upload + stats
│   ├── pinterest.py         # Pinterest API v5 – pin creation + analytics
│   └── analytics.py         # Unified analytics collector for all platforms
│
└── .github/
    └── workflows/
        ├── daily.yml        # Cron: daily content update (08:00 UTC)
        └── report.yml       # Cron: weekly analytics report (Mon 09:00 UTC)
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/SophiaHYue/social-auto-workflow.git
cd social-auto-workflow
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure API keys

```bash
cp config/api_keys.example.env .env
# Edit .env and fill in all required values
```

The `.env` file is git-ignored and will never be committed.

### 4. Add GitHub Secrets

For the GitHub Actions workflows to work, add every variable from
`config/api_keys.example.env` as a **repository secret**
(`Settings → Secrets and variables → Actions → New repository secret`).

---

## Running Locally

### Daily content update

```bash
# Full run (requires all API keys)
python daily_update.py

# Override today's topic
python daily_update.py --topic "sustainable energy breakthroughs"

# Dry-run: generate content only, skip publishing
python daily_update.py --dry-run
```

### Analytics report

```bash
python analytics_report.py

# Save reports to a custom directory
python analytics_report.py --output-dir my_reports
```

---

## GitHub Actions Schedules

| Workflow | File | Schedule |
|---|---|---|
| Daily content update | `.github/workflows/daily.yml` | Every day at **08:00 UTC** |
| Weekly analytics report | `.github/workflows/report.yml` | Every **Monday at 09:00 UTC** |

Both workflows can also be triggered manually via **Actions → Run workflow**.

---

## Content Generation APIs

| Type | Primary | Fallback |
|---|---|---|
| Image | DALL·E 3 (`OPENAI_API_KEY`) | Stable Diffusion (`STABILITY_API_KEY`) |
| Short video | Runway ML (`RUNWAY_API_KEY`) | MoviePy (local, needs `image_path`) |
| Long video | Pictory (`PICTORY_CLIENT_ID` + `PICTORY_CLIENT_SECRET`) | — |
| Text | OpenAI GPT-4o-mini (`OPENAI_API_KEY`) | — |

---

## License

MIT – see [LICENSE](LICENSE).
