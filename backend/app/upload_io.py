"""
Bounded reads for uploads and JSON bodies — reduces DoS risk from huge bodies in memory.
"""
from __future__ import annotations

import io

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 20_000_000


async def read_upload_bytes(upload: UploadFile, max_bytes: int) -> bytes:
    """Read entire upload with a hard cap; rejects oversize before buffering gigabytes."""
    chunks: list[bytes] = []
    total = 0
    while True:
        part = await upload.read(64 * 1024)
        if not part:
            break
        total += len(part)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {max_bytes // (1024 * 1024)} MB)",
            )
        chunks.append(part)
    data = b"".join(chunks)
    if len(data) < 100:
        raise HTTPException(status_code=400, detail="Empty or invalid file")
    return data


def preprocess_image_to_jpeg(raw_bytes: bytes, max_dim: int = 1536, quality: int = 90) -> bytes:
    """
    Decode with Pillow, normalize EXIF orientation, downscale — matches Mehndi pipeline.
    Re-encode to JPEG so downstream model always gets a known format.
    """
    try:
        pil = Image.open(io.BytesIO(raw_bytes))
        pil = ImageOps.exif_transpose(pil)
        if pil.mode != "RGB":
            pil = pil.convert("RGB")
        w, h = pil.size
        if max(w, h) > max_dim:
            pil.thumbnail((max_dim, max_dim), Image.LANCZOS)
        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}") from e
