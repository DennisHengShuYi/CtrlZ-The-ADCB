"""
Clerk JWT authentication middleware for FastAPI.
Verifies the Bearer token from the Authorization header using Clerk's JWKS.
"""

from functools import lru_cache
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status

from app.config import CLERK_JWKS_URL


@lru_cache()
def _get_jwks() -> dict[str, Any]:
    """Fetch and cache the JWKS from Clerk."""
    response = httpx.get(CLERK_JWKS_URL)
    response.raise_for_status()
    return response.json()


def _get_public_key(token: str) -> jwt.algorithms.RSAAlgorithm:
    """Extract the correct public key from JWKS based on the token's kid."""
    jwks = _get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    for key_data in jwks.get("keys", []):
        if key_data["kid"] == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find matching signing key.",
    )


def _extract_bearer_token(request: Request) -> str:
    """Extract the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )
    return auth_header[7:]


def require_auth(request: Request) -> dict[str, Any]:
    """
    FastAPI dependency that verifies Clerk JWTs.
    Returns the decoded token payload (contains userId, etc.).
    """
    token = _extract_bearer_token(request)
    public_key = _get_public_key(token)

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk tokens don't always have aud
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )
