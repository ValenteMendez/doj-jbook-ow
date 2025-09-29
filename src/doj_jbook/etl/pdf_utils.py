from __future__ import annotations

import os
import io
from typing import List, Dict, Tuple

try:
    import fitz  # PyMuPDF
except Exception as e:  # pragma: no cover - import guard
    fitz = None  # type: ignore


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def list_embedded_files(pdf_path: str) -> List[Dict]:
    """
    Return metadata for embedded files in a PDF using PyMuPDF.
    Supports newer API (embfile_count / embfile_info) and older (attachments()).
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) not installed. Please install requirements.")

    doc = fitz.open(pdf_path)
    files: List[Dict] = []

    # Newer API
    if hasattr(doc, "embfile_count") and doc.embfile_count > 0:
        for i in range(doc.embfile_count):
            info = doc.embfile_info(i)  # type: ignore[attr-defined]
            # info keys include: filename, desc, ufilename, usize, cdate, mdate, etc.
            files.append({
                "index": i,
                "filename": info.get("filename"),
                "ufilename": info.get("ufilename"),
                "desc": info.get("desc"),
                "size": info.get("usize"),
            })
        return files

    # Older API fallback
    if hasattr(doc, "attachments"):
        atts = doc.attachments()
        for name, meta in atts.items():  # type: ignore[assignment]
            files.append({
                "filename": name,
                "size": meta.get("length"),
                "desc": meta.get("desc"),
            })
    return files


def extract_embedded_files(pdf_path: str, out_dir: str) -> List[str]:
    """
    Extract all embedded files from the given PDF into out_dir.
    Returns list of written file paths.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) not installed. Please install requirements.")

    _ensure_dir(out_dir)
    doc = fitz.open(pdf_path)
    written: List[str] = []

    # Newer API first
    if hasattr(doc, "embfile_count") and doc.embfile_count > 0:
        for i in range(doc.embfile_count):
            info = doc.embfile_info(i)  # type: ignore[attr-defined]
            data = doc.embfile_get(i)  # type: ignore[attr-defined]
            filename = info.get("filename") or f"attachment_{i}"
            safe_name = filename.replace(os.sep, "_")
            out_path = os.path.join(out_dir, safe_name)
            with open(out_path, "wb") as f:
                if isinstance(data, (bytes, bytearray)):
                    f.write(data)
                elif hasattr(data, "read"):
                    f.write(data.read())  # type: ignore
                else:
                    raise RuntimeError("Unexpected embedded data type")
            written.append(out_path)
        return written

    # Older API fallback
    if hasattr(doc, "attachments"):
        atts = doc.attachments()
        for name, meta in atts.items():
            safe_name = name.replace(os.sep, "_")
            out_path = os.path.join(out_dir, safe_name)
            with open(out_path, "wb") as f:
                f.write(meta["file"])
            written.append(out_path)

    return written

