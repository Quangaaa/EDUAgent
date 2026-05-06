import hashlib
import importlib
import io
import os
import xml.etree.ElementTree as ET
import zipfile

from utils.config import chat_conf, chroma_conf
from utils.log import logger
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_core.documents import Document

PLAIN_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
    ".log",
    ".ini",
    ".cfg",
    ".conf",
    ".py",
    ".js",
    ".java",
    ".c",
    ".cpp",
    ".sql",
}

def normalize_allowed_types(types: list[str] | tuple[str, ...] | set[str] | None) -> set[str]:
    normalized = set()
    for ext in types or []:
        value = str(ext).strip().lower()
        if not value:
            continue
        if not value.startswith("."):
            value = f".{value}"
        normalized.add(value)
    return normalized


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def get_bytes_md5_hex(content_bytes: bytes) -> str:
    return hashlib.md5(content_bytes).hexdigest()


def get_kb_allowed_types() -> set[str]:
    configured = (chroma_conf or {}).get("allow_file_types", [])
    fallback = {".txt", ".pdf", ".docx"}
    result = normalize_allowed_types(configured)
    return result or fallback


def get_chat_allowed_types() -> set[str]:
    upload_conf = (chat_conf or {}).get("upload", {}) if isinstance(chat_conf, dict) else {}
    configured = upload_conf.get("allowed_file_types", [])
    result = normalize_allowed_types(configured)
    fallback = set(PLAIN_TEXT_EXTENSIONS) | {".pdf", ".docx"}
    return result or fallback


def is_allowed_file_type(filename: str, allowed_types: set[str]) -> bool:
    return get_file_extension(filename) in allowed_types

def get_file_md5_hex(file_path):
    if not os.path.exists(file_path):
        logger.error(f"{file_path} is not a valid file.")
        return
    
    if not os.path.isfile(file_path):
        logger.error(f"{file_path} is not a file.")
        return
    
    md5obj = hashlib.md5()

    chunk_size = 4096
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5obj.update(chunk)
        return md5obj.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating MD5 for {file_path}: {e}")
        return
    
def listdir_with_allowed_type(path: str, allowed_types: tuple[str]):
    """
    返回文件夹中允许的文件列表
    """
    files = []
    if not os.path.isdir(path):
        logger.error(f"{path} is not a valid directory.")
        return allowed_types
    
    for f in os.listdir(path):
        if f.endswith(allowed_types):
            files.append(os.path.join(path, f))

    return tuple(files)

def _decode_text_bytes(content_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return content_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def _extract_text_from_pdf_bytes(content_bytes: bytes) -> str:
    pdf_reader_cls = None
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = importlib.import_module(module_name)
            pdf_reader_cls = getattr(module, "PdfReader", None)
            if pdf_reader_cls is not None:
                break
        except Exception:
            continue

    if pdf_reader_cls is None:
        raise RuntimeError("未安装 pypdf/PyPDF2，无法解析 PDF")

    reader = pdf_reader_cls(io.BytesIO(content_bytes))
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts).strip()


def _extract_text_from_docx_bytes(content_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
        xml_content = zf.read("word/document.xml")
    root = ET.fromstring(xml_content)
    texts = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            texts.append(node.text)
    return "\n".join(texts).strip()


def is_supported_upload_file(filename: str) -> bool:
    # 兼容旧调用，按 chat 上传类型判断
    return is_allowed_file_type(filename, get_chat_allowed_types())


def extract_text_from_upload(filename: str, content_bytes: bytes) -> str:
    ext = get_file_extension(filename)
    if ext in PLAIN_TEXT_EXTENSIONS:
        return _decode_text_bytes(content_bytes)
    if ext == ".pdf":
        return _extract_text_from_pdf_bytes(content_bytes)
    if ext == ".docx":
        return _extract_text_from_docx_bytes(content_bytes)
    return ""