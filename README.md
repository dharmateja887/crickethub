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

Configuration is read from environment variables (see the `.env` support in `CricketZone/settings.py`). Create a `.env` file if you need to override settings.

- `DJANGO_DEBUG` - debug mode (`True`/`False`)
- `DJANGO_ALLOWED_HOSTS` - comma-separated allowed hosts (default `*`)
- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - database settings
- `GOOGLE_API_KEY` - Google API key

## Deployment

See the deployment notes for PythonAnywhere / your chosen host in the repository documentation.
