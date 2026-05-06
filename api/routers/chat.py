from fastapi import APIRouter, HTTPException,Depends,UploadFile,File
from pathlib import Path
import uuid

from api.auth import get_current_user
from api.db import get_db_connection, now_str
from api.response import build_success
from api.schemas import SessionCreatePayload, AskPayload
from api.service import get_agent_service, get_chat_service, get_kb_service, get_plan_service
from utils.dialogue import dialogue_repo
from utils.file import extract_text_from_upload, get_chat_allowed_types, is_allowed_file_type

router = APIRouter(prefix="/chat", tags=["chat"])
CHAT_ALLOWED_TYPES = get_chat_allowed_types()

# 会话表用字典的形式取出来
@router.get("/sessions")
def list_sessions(current_user=Depends(get_current_user)):
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (current_user["id"],),
        ).fetchall()

    return build_success({"sessions": [dict(row) for row in rows]})

@router.post("/sessions")
def create_session(payload: SessionCreatePayload, current_user=Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    now = now_str()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, current_user["id"], payload.title, now, now),
        )
        conn.commit()

    return build_success(
        {
            "session": {
                "id": session_id,
                "title": payload.title,
                "created_at": now,
                "updated_at": now,
            }
        }
    )

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, current_user=Depends(get_current_user)):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, current_user["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()

    return build_success(
        {
            "history_deleted": True,
            "vector_store": {
                "skipped": True,
                "reason": "知识库为用户级，不随单会话删除",
            },
        }
    )

@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, current_user=Depends(get_current_user)):
    if not dialogue_repo.session_exists_for_user(str(current_user["id"]), session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    messages = dialogue_repo.list_session_messages(session_id)
    attachments = dialogue_repo.list_session_attachments(session_id)

    return build_success({"messages": messages, "attachments": attachments})

@router.post("/sessions/{session_id}/ask")
def ask(session_id: str, payload: AskPayload, current_user=Depends(get_current_user)):
    user_id = str(current_user["id"])
    if not dialogue_repo.session_exists_for_user(user_id, session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    inserted_user_id = dialogue_repo.append_message(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=payload.query,
    )
    if inserted_user_id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        if payload.mode == "agent":
            answer = get_agent_service().invoke(
                query=payload.query,
                context={"mode": "agent"},
                user_id=user_id,
                session_id=session_id,
            )
        elif payload.mode == "plan":
            answer = get_plan_service().invoke(
                query=payload.query,
                context={"mode": "plan"},
                user_id=user_id,
                session_id=session_id,
            )
        else:
            answer = get_chat_service().invoke(
                query=payload.query,
                context={"mode": "chat"},
                user_id=user_id,
                session_id=session_id,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG generation failed: {e}") from e

    inserted_assistant_id = dialogue_repo.append_message(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        content=str(answer),
    )
    if inserted_assistant_id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = dialogue_repo.list_session_messages(session_id)

    return build_success(
        {
            "session_id": session_id,
            "mode": payload.mode,
            "answer": str(answer),
            "messages": messages,
        }
    )

@router.post("/sessions/{session_id}/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    safe_name = Path(file.filename).name
    if not is_allowed_file_type(safe_name, CHAT_ALLOWED_TYPES):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {sorted(CHAT_ALLOWED_TYPES)}",
        )
    
    if not dialogue_repo.session_exists_for_user(str(current_user["id"]), session_id):
        raise HTTPException(status_code=404, detail="Session not found")
        
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    text_content = ""
    try:
        text_content = extract_text_from_upload(safe_name, content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded file: {exc}") from exc

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="No readable text found in uploaded file")

    content_preview = text_content[:2000]
    file_ref = f"memory://{current_user['id']}/{session_id}/{safe_name}"

    now = now_str()
    message_text = f"[用户上传文件] {safe_name} ({len(content)} bytes)"
    if content_preview:
        message_text += f"\n文件内容预览:\n{content_preview}"

    message_id = dialogue_repo.append_message(
        user_id=str(current_user["id"]),
        session_id=session_id,
        role="file",
        content=message_text,
        created_at=now,
    )
    if message_id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_attachments (session_id, message_id, filename, file_path, file_size, content_preview, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, message_id, safe_name, file_ref, len(content), content_preview, now),
        )
        conn.commit()

    kb_result = None
    try:
        kb_result = get_kb_service().add_uploaded_files(
            [{"filename": safe_name, "content": content}],
            user_id=str(current_user["id"]),
            session_id=session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to add file to knowledge base: {exc}") from exc

    return build_success(
        {
            "session_id": session_id,
            "filename": safe_name,
            "size": len(content),
            "stored_in": "db_and_vector_store",
            "kb_result": kb_result,
        },
        message="文件已完成会话记录并写入知识库。",
    )
