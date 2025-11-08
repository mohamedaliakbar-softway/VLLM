import os
import jwt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from database import get_db
from models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

REPL_ID = os.environ.get("REPL_ID")
ISSUER_URL = os.environ.get("ISSUER_URL", "https://replit.com/oidc")

if not REPL_ID:
    logger.warning("REPL_ID environment variable not set. Authentication will not work in production.")
    REPL_ID = "development-repl-id"

oauth = OAuth()

oauth.register(
    name="replit",
    client_id=REPL_ID,
    client_secret=None,
    server_metadata_url=f"{ISSUER_URL}/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid profile email offline_access",
        "code_challenge_method": "S256",
    },
)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    user_data = request.session.get("user")
    if not user_data:
        return None
    
    user = db.query(User).filter(User.id == user_data["sub"]).first()
    return user


def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.replit.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.replit.authorize_access_token(request)
        
        user_claims = token.get("userinfo")
        if not user_claims:
            id_token_claims = await oauth.replit.parse_id_token(request, token)
            user_claims = id_token_claims
        
        user = db.query(User).filter(User.id == user_claims["sub"]).first()
        
        if not user:
            user = User(
                id=user_claims["sub"],
                email=user_claims.get("email"),
                first_name=user_claims.get("first_name"),
                last_name=user_claims.get("last_name"),
                profile_image_url=user_claims.get("profile_image_url"),
            )
            db.add(user)
        else:
            user.email = user_claims.get("email")
            user.first_name = user_claims.get("first_name")
            user.last_name = user_claims.get("last_name")
            user.profile_image_url = user_claims.get("profile_image_url")
        
        db.commit()
        db.refresh(user)
        
        request.session["user"] = user_claims
        
        next_url = request.session.pop("next_url", "/")
        return RedirectResponse(url=next_url)
        
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    
    end_session_endpoint = f"{ISSUER_URL}/session/end"
    post_logout_redirect_uri = str(request.base_url)
    
    logout_url = f"{end_session_endpoint}?client_id={REPL_ID}&post_logout_redirect_uri={post_logout_redirect_uri}"
    
    return RedirectResponse(url=logout_url)


@router.get("/me")
async def get_user_info(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return {"authenticated": False}
    
    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_image_url": user.profile_image_url,
        }
    }
