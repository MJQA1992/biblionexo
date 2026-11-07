from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from app.schemas import LoginRequest
from app.security import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/v1", tags=["Autenticación"])

@router.post("/login")
def login(credentials: LoginRequest, request: Request, db: Session = Depends(get_db)):
    correo = credentials.correo.strip().lower()
    user = db.query(Usuario).filter(Usuario.correo == correo).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")
    token = create_access_token(user)
    if "session" in request.scope:
        request.session["user_id"] = user.id
        request.session["user_rol"] = user.rol
    return {
        "access_token": token,
        "token_type": "bearer",
        "id": user.id,
        "nombre": user.nombre,
        "correo": user.correo,
        "rol": user.rol,
    }

@router.post("/logout")
def logout(request: Request):
    if "session" in request.scope:
        request.session.clear()
    return {"mensaje": "Sesión cerrada correctamente."}

@router.get("/me")
def me(current_user: Usuario = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "correo": current_user.correo,
        "rol": current_user.rol,
    }
