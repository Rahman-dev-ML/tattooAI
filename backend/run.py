import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load .env from the same directory as this file into os.environ."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

import uvicorn  # noqa: E402

if __name__ == "__main__":
    reload_enabled = os.environ.get("UVICORN_RELOAD", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    workers = int(os.environ.get("UVICORN_WORKERS", "1"))
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=reload_enabled,
        workers=workers if not reload_enabled else 1,
    )
