from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import PORT_BASE
from .document_routes import router as document_router
from .file_routes import router as file_memory_router
from .memory_routes import router as memory_router

app = FastAPI(title="DATA 260 HW6 Clinical Trial Memory API", version="6.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.include_router(document_router)
app.include_router(memory_router)
app.include_router(file_memory_router)


@app.get("/health")
def health():
    return {"status": "ok", "database": "mongodb", "database_name": "s8561_doc", "model": "qwen3:8b"}


if __name__ == "__main__":
    uvicorn.run("code.memory_application.main:app", host="127.0.0.1", port=PORT_BASE, reload=False)
