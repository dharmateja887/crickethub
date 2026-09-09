# CricketHub

A Django-based cricket dashboard and chat application.

## Local Setup

```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## Configuration

Configuration is read from environment variables (see `.env` support in `CricketZone/settings.py`). Copy `.env.example` to `.env` to override settings.

- `DJANGO_SECRET_KEY` - Django secret key (set a strong value in production)
- `DJANGO_DEBUG` - debug mode (`True`/`False`)
- `DJANGO_ALLOWED_HOSTS` - comma-separated allowed hosts (default `*`)
- `DATABASE_URL` - database connection string. On Vercel this is set automatically when you add Postgres.
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - local MySQL fallback when `DATABASE_URL` is not set
- `GOOGLE_API_KEY` - Google Gemini API key

## Deploying on Vercel

Vercel supports Django zero-configuration (Python runtime). The repository includes `vercel.json`, `runtime.txt`, and `requirements.txt`.

1. Push this repository to GitHub.
2. Import the repo at https://vercel.com/new (create a Vercel account).
3. In the project, add a **Postgres (Neon)** database — Vercel sets `DATABASE_URL` automatically.
4. Set environment variables in Vercel: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=*`, `DJANGO_DEBUG=False`, `GOOGLE_API_KEY`.
5. Deploy. Static files are collected and served from the Vercel CDN automatically.
