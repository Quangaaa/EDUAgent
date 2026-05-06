from fastapi import APIRouter, Depends, HTTPException
from api.auth import create_token, get_current_user, hash_password, verify_password
from api.db import get_db_connection, now_str
from api.response import build_success
from api.schemas import AuthPayload
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
def register(payload: AuthPayload):
    with get_db_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (payload.username,)).fetchone() # 注册检查
        if existing is not None:
            raise HTTPException(status_code=409, detail="Username already exists")
        
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (payload.username, hash_password(payload.password), now_str())
        )
        conn.commit()

        user = conn.execute("SELECT id, username, created_at FROM users WHERE username = ?", (payload.username,)).fetchone()

        return build_success(
            {
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "created_at": user["created_at"],
                }
            }
        )
    
@router.post("/login")
def login(payload: AuthPayload):
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (payload.username,),
        ).fetchone()

    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_token(user["id"])
    return build_success(
        {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
            },
        }
    )

@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return build_success(
        {
            "user": {
                "id": current_user["id"],
                "username": current_user["username"],
            }
        }
    )