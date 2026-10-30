"""Create, list and delete short URLs (all require login)."""
import os
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Url, User
from app.schemas import UrlCreate, UrlOut
from app.security import get_current_user

router = APIRouter(prefix="/urls", tags=["urls"])

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
RESERVED_CODES = {"docs", "redoc", "openapi", "health", "auth", "urls", "static"}


def generate_code(db: Session) -> str:
    """Return a random code that is not used yet."""
    for _ in range(10):
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        if not db.scalar(select(Url.id).where(Url.code == code)):
            return code
    raise HTTPException(status_code=500, detail="Could not generate a unique code")


def to_out(url: Url, request: Request) -> UrlOut:
    base = os.getenv("BASE_URL") or str(request.base_url)
    return UrlOut(
        code=url.code,
        short_url=f"{base.rstrip('/')}/{url.code}",
        target_url=url.target_url,
        clicks=url.clicks,
        created_at=url.created_at,
    )


@router.post("", response_model=UrlOut, status_code=status.HTTP_201_CREATED)
def create_url(
    payload: UrlCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    code = payload.custom_code
    if code:
        if code.lower() in RESERVED_CODES:
            raise HTTPException(status_code=409, detail="That code is reserved")
        if db.scalar(select(Url.id).where(Url.code == code)):
            raise HTTPException(status_code=409, detail="That code is already taken")
    else:
        code = generate_code(db)

    url = Url(code=code, target_url=str(payload.target_url), owner_id=user.id)
    db.add(url)
    try:
        db.commit()
    except IntegrityError:  # two requests grabbed the same code at once
        db.rollback()
        raise HTTPException(status_code=409, detail="That code is already taken")
    db.refresh(url)
    return to_out(url, request)


@router.get("", response_model=list[UrlOut])
def list_my_urls(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    urls = db.scalars(
        select(Url).where(Url.owner_id == user.id).order_by(Url.created_at.desc())
    ).all()
    return [to_out(u, request) for u in urls]


@router.get("/{code}", response_model=UrlOut)
def get_url_stats(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    url = db.scalar(select(Url).where(Url.code == code, Url.owner_id == user.id))
    if url is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return to_out(url, request)


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_url(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    url = db.scalar(select(Url).where(Url.code == code, Url.owner_id == user.id))
    if url is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    db.delete(url)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
