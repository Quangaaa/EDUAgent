import hashlib
import os
import re

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from model.factory import get_embedding_model
from utils.config import chroma_conf
from utils.file import extract_text_from_upload, get_bytes_md5_hex, get_file_extension, get_kb_allowed_types
from utils.log import logger
from utils.path import get_abs_path

class VectorStoreService:
    def __init__(self):
        self.collection_name = chroma_conf["collection_name"]
        self.persist_directory = get_abs_path(chroma_conf["persist_directory"])
        self.allowed_types = get_kb_allowed_types()
        self.md5_store_path = get_abs_path(chroma_conf["md5_hex_store"])
        self.uploaded_dir = get_abs_path(chroma_conf.get("uploaded_dir", "uploaded_files"))

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def _normalize_scope(self, user_id: str | None, session_id: str | None) -> tuple[str, str]:
        user = (user_id or "anonymous").strip() or "anonymous"
        session = (session_id or "default").strip() or "default"
        return user, session

    def _safe_segment(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_.-]", "_", value)

    def _scope_key(self, user_id: str) -> str:
        return user_id

    def _collection_name_for_scope(self, user_id: str, session_id: str | None = None) -> str:
        # 知识库按用户隔离，不再按会话拆分
        raw = f"{self.collection_name}-{user_id}"
        normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)
        digest = hashlib.md5(self._scope_key(user_id).encode("utf-8")).hexdigest()[:8]
        short_name = normalized[:48].strip("_") or self.collection_name
        name = f"{short_name}_{digest}"
        if len(name) < 3:
            name = f"{self.collection_name}_{digest}"
        return name[:63]

    def _get_vector_store(self, user_id: str, session_id: str) -> Chroma:
        return Chroma(
            collection_name=self._collection_name_for_scope(user_id),
            persist_directory=self.persist_directory,
            embedding_function=get_embedding_model(),
        )

    def _save_uploaded_file(self, user_id: str, filename: str, content_bytes: bytes, md5_hex: str) -> str:
        user_dir = os.path.join(self.uploaded_dir, self._safe_segment(user_id))
        os.makedirs(user_dir, exist_ok=True)
        safe_name = self._safe_segment(filename)
        stored_name = f"{md5_hex[:8]}_{safe_name}"
        stored_path = os.path.join(user_dir, stored_name)
        with open(stored_path, "wb") as f:
            f.write(content_bytes)
        return stored_path

    def _ensure_md5_store(self) -> None:
        os.makedirs(os.path.dirname(self.md5_store_path) or ".", exist_ok=True)
        if not os.path.exists(self.md5_store_path):
            open(self.md5_store_path, "w", encoding="utf-8").close()

    def _check_md5_hex(self, scope: str, md5_for_check: str) -> bool:
        self._ensure_md5_store()
        with open(self.md5_store_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line == f"{scope}|{md5_for_check}":
                    return True
        return False

    def _save_md5_hex(self, scope: str, md5_for_check: str) -> None:
        self._ensure_md5_store()
        with open(self.md5_store_path, "a", encoding="utf-8") as f:
            f.write(f"{scope}|{md5_for_check}\n")

    def _remove_scope_md5(self, scope: str) -> int:
        self._ensure_md5_store()
        with open(self.md5_store_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        kept_lines = []
        removed_count = 0
        prefix = f"{scope}|"
        for line in lines:
            if line.startswith(prefix):
                removed_count += 1
                continue
            kept_lines.append(line)

        with open(self.md5_store_path, "w", encoding="utf-8") as f:
            f.writelines(kept_lines)

        return removed_count

    def _extract_text(self, filename: str, content_bytes: bytes) -> str:
        return extract_text_from_upload(filename, content_bytes)

    def get_retriever(self, user_id: str = "anonymous", session_id: str = "default"):
        user, session = self._normalize_scope(user_id, session_id)
        return self._get_vector_store(user, session).as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def add_uploaded_files(
        self,
        files: list[dict[str, bytes]],
        user_id: str = "anonymous",
        session_id: str = "default",
    ) -> dict:
        user, session = self._normalize_scope(user_id, session_id)
        scope = self._scope_key(user)
        vector_store = self._get_vector_store(user, session)

        indexed_files = []
        skipped_files = []
        failed_files = []

        for item in files:
            filename = os.path.basename(item.get("filename", ""))
            content_bytes = item.get("content", b"")
            ext = get_file_extension(filename)

            if not filename or ext not in self.allowed_types:
                skipped_files.append(
                    {
                        "filename": filename or "unknown",
                        "reason": f"不支持的文件类型，仅支持: {sorted(self.allowed_types)}",
                    }
                )
                continue

            if not content_bytes:
                skipped_files.append({"filename": filename, "reason": "空文件"})
                continue

            md5_hex = get_bytes_md5_hex(content_bytes)
            if self._check_md5_hex(scope, md5_hex):
                skipped_files.append({"filename": filename, "reason": "同会话内重复文件"})
                continue

            try:
                text = self._extract_text(filename, content_bytes)
                if not text.strip():
                    skipped_files.append({"filename": filename, "reason": "未解析到有效文本"})
                    continue

                docs = [
                    Document(
                        page_content=text,
                        metadata={
                            "source": filename,
                            "user_id": user,
                            "session_id": session,
                            "md5": md5_hex,
                        },
                    )
                ]
                split_documents = self.spliter.split_documents(docs)
                if not split_documents:
                    skipped_files.append({"filename": filename, "reason": "分片后无有效内容"})
                    continue

                vector_store.add_documents(split_documents)
                stored_path = self._save_uploaded_file(user, filename, content_bytes, md5_hex)
                self._save_md5_hex(scope, md5_hex)
                indexed_files.append({"filename": filename, "chunks": len(split_documents), "stored_path": stored_path})
            except Exception as e:
                logger.error(f"[上传入库] {filename} 加载失败: {str(e)}")
                failed_files.append({"filename": filename, "reason": str(e)})

        return {
            "user_id": user,
            "session_id": session,
            "indexed_count": len(indexed_files),
            "skipped_count": len(skipped_files),
            "failed_count": len(failed_files),
            "indexed_files": indexed_files,
            "skipped_files": skipped_files,
            "failed_files": failed_files,
        }

    def delete_scope(self, user_id: str = "anonymous", session_id: str = "default") -> dict:
        # 兼容旧调用：删除整用户知识库
        user, session = self._normalize_scope(user_id, session_id)
        scope = self._scope_key(user)
        vector_store = self._get_vector_store(user, session)

        collection_deleted = False
        collection_error = ""
        try:
            vector_store.delete_collection()
            collection_deleted = True
        except Exception as e:
            # collection 不存在时也允许继续清理 md5 记录
            collection_error = str(e)
            logger.warning(f"[会话清理] collection 删除异常: {collection_error}")

        md5_removed = self._remove_scope_md5(scope)

        user_dir = os.path.join(self.uploaded_dir, self._safe_segment(user))
        removed_files = 0
        if os.path.isdir(user_dir):
            for name in os.listdir(user_dir):
                file_path = os.path.join(user_dir, name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    removed_files += 1
            if not os.listdir(user_dir):
                os.rmdir(user_dir)

        return {
            "user_id": user,
            "session_id": session,
            "collection_deleted": collection_deleted,
            "collection_error": collection_error,
            "md5_removed": md5_removed,
            "removed_files": removed_files,
        }
