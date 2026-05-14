import os

import uvicorn

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
