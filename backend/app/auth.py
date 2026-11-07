from fastapi import Header, HTTPException, status

from app import db


def require_username(
    x_username: str = Header(default=""),
    x_password: str = Header(default=""),
) -> str:
    if not db.verify_credentials(x_username, x_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    return x_username
