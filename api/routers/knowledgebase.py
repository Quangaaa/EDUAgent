from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pathlib import Path
from api.service import get_kb_service
from api.auth import get_current_user
from api.response import build_success
from utils.file import is_allowed_file_type, get_kb_allowed_types
from utils.file import extract_text_from_upload

router = APIRouter(prefix="/knowledgebase", tags=["knowledgebase"])

KB_ALLOWED_TYPES = get_kb_allowed_types()

@router.post("/kb/upload")
async def upload(session_id: str | None = None, file: UploadFile = File(...), current_user=Depends(get_current_user)):
    safe_name = Path(file.filename).name
    if not safe_name:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    if not is_allowed_file_type(safe_name, KB_ALLOWED_TYPES):
        raise HTTPException(status_code=400, detail="File type not allowed")
    
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

    try:
        resolved_session = session_id or "default"
        kb_result = get_kb_service().add_uploaded_files(
            [{"filename": safe_name, "content": content}],
            user_id=str(current_user["id"]),
            session_id=resolved_session,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add file to knowledge base: {e}") from e
    
    return build_success(
        {
            "filename": safe_name,
            "size": len(content),
            "operator": current_user["username"],
            "kb_result": kb_result or "文件已存在且未修改，无需更新知识库",
            "collection_name": get_kb_service()._collection_name_for_scope(str(current_user["id"]), resolved_session),
        }
    )
