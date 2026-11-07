import hashlib
import hmac
import secrets
import base64
import json
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import SESSION_SECRET
from app.database import get_db
from app.models import Usuario

bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, salt, hex_digest = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return hmac.compare_digest(dk.hex(), hex_digest)
    except Exception:
        return False

def create_access_token(user: Usuario) -> str:
    payload = {"user_id": user.id, "rol": user.rol, "correo": user.correo}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    b64 = base64.urlsafe_b64encode(raw).decode("utf-8")
    sig = hmac.new(SESSION_SECRET.encode("utf-8"), b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"

def decode_access_token(token: str) -> Optional[dict]:
    try:
        b64, sig = token.split(".", 1)
        expected = hmac.new(SESSION_SECRET.encode("utf-8"), b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return json.loads(base64.urlsafe_b64decode(b64.encode("utf-8")).decode("utf-8"))
    except Exception:
        return None

def get_current_user(
    request: Request,
     creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    user_id = None
    if creds and creds.credentials:
        data = decode_access_token(creds.credentials)
        if data:
            user_id = data.get("user_id")
    if not user_id and "session" in request.scope:
        user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Debe iniciar sesión.")
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida.")
    return user

def require_bibliotecario(user: Usuario = Depends(get_current_user)) -> Usuario:
    if user.rol != "Bibliotecario":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: se requiere rol Bibliotecario.",
        )
    return user
