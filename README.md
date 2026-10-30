# URL Shortener API

A REST API that creates short links, with user accounts, JWT authentication, click tracking, automated tests, Docker support and a CI pipeline.

Built with **Python, FastAPI, SQLAlchemy, SQLite/PostgreSQL, JWT, bcrypt, pytest and Docker**.

![CI](https://github.com/YOUR_USERNAME/url-shortener-api/actions/workflows/ci.yml/badge.svg)

**Live demo:** _add your deployed URL here_ (interactive API docs at `/docs`)

## Features

- User registration and login (passwords hashed with bcrypt, JWT access tokens)
- Create short links with a random code or your own custom code
- Public redirect endpoint with click counting
- Each user can list, inspect and delete only their own links
- Input validation (valid URLs, code format, password rules) and clear HTTP error codes
- 16 automated tests (pytest) using an isolated in-memory database
- Dockerfile and GitHub Actions workflow that runs the tests on every push
- Interactive Swagger documentation at `/docs`

## API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Create an account |
| POST | `/auth/login` | No | Get a JWT token (form fields `username`, `password`) |
| POST | `/urls` | Yes | Create a short URL (`target_url`, optional `custom_code`) |
| GET | `/urls` | Yes | List your short URLs |
| GET | `/urls/{code}` | Yes | Stats for one of your URLs |
| DELETE | `/urls/{code}` | Yes | Delete one of your URLs |
| GET | `/{code}` | No | Redirect to the original URL (counts a click) |
| GET | `/health` | No | Health check |

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv

# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (cmd):         .venv\Scripts\activate.bat
# macOS / Linux:         source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs, register a user, click **Authorize**, log in, and try `POST /urls`.

## Run the tests

```bash
pytest -v
```

## Run with Docker

```bash
docker build -t url-shortener-api .
docker run -p 8000:8000 -e SECRET_KEY=change-me-to-a-long-random-string url-shortener-api
```

## Configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | dev value | Signs JWT tokens. **Set a long random value in production.** |
| `DATABASE_URL` | `sqlite:///./shortener.db` | Use a PostgreSQL URL in production |
| `BASE_URL` | request host | Public base URL used in generated short links |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |

## Project structure

```
app/
  main.py        FastAPI app, redirect route, startup
  database.py    Engine and session setup
  models.py      User and Url tables
  schemas.py     Request/response validation
  security.py    Password hashing and JWT helpers
  routers/
    auth.py      /auth/register, /auth/login
    urls.py      /urls CRUD
tests/test_api.py
Dockerfile
.github/workflows/ci.yml
```

## Design notes

- Short codes are 6 random base62 characters (about 56 billion combinations), generated with `secrets`, and a unique database constraint protects against collisions.
- Click counts use an atomic SQL `UPDATE clicks = clicks + 1` so concurrent visits are not lost.
- Users can only see and delete their own links; other users get a 404.
- Tables are created at startup for simplicity. A production system would use Alembic migrations.

## Possible improvements

Rate limiting, link expiry dates, QR code generation, Alembic migrations, and a small frontend.
