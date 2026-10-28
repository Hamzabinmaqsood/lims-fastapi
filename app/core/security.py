import bcrypt
from datetime import UTC, datetime, timedelta
import jwt
from app.core.config import settings

ALGORITHM = "HS256"

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())



def create_token(user_id: int, token_type: str, lifetime: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "user_id": user_id,
        "token_type": token_type,  # "access" or "refresh"
        "iat": now,                # issued at
        "exp": now + lifetime,     # expires at (PyJWT checks this automatically)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_token_pair(user_id: int) -> dict:
    return {
        "access": create_token(user_id, "access", timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)),
        "refresh": create_token(user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_DAYS)),
    }


def decode_token(token: str, expected_type: str) -> int:
    """Return the user_id inside a valid token, or raise ValueError."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:  # bad signature, expired, garbage...
        raise ValueError("Token is invalid or expired") from exc
    if payload.get("token_type") != expected_type:
        raise ValueError("Token has wrong type")
    return payload["user_id"]
