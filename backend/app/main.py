from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # Register tables before create_all.
from .database import Base, engine
from .routers import attachments, audit, auth, changes, dashboard, parts, revisions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="RevisionHub", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "Authorization"],
)
app.include_router(parts.router, prefix="/api")
app.include_router(revisions.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(changes.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(attachments.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}
