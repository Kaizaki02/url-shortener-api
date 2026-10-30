"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.routers import auth, urls


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (fine for a small project; use Alembic for real migrations).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="URL Shortener API",
    description="Create short links with user accounts, JWT login and click tracking.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(urls.router)


@app.get("/health", tags=["meta"])
def health():
    """Used to check that the deployed service is up."""
    return {"status": "ok"}


@app.get("/", tags=["meta"])
def root():
    return {"name": "URL Shortener API", "docs": "/docs", "health": "/health"}


# Keep this route LAST: it matches any single path segment.
@app.get("/{code}", tags=["redirect"], include_in_schema=True)
def redirect_to_target(code: str, db: Session = Depends(get_db)):
    """Public endpoint: send the visitor to the original URL and count the click."""
    url = db.scalar(select(models.Url).where(models.Url.code == code))
    if url is None:
        raise HTTPException(status_code=404, detail="Short URL not found")

    db.execute(update(models.Url).where(models.Url.id == url.id).values(clicks=models.Url.clicks + 1))
    db.commit()
    return RedirectResponse(url=url.target_url, status_code=307)
