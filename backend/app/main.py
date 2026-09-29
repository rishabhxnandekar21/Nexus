"""FastAPI app: CORS, router mounts, and the health check."""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import audit, auth, entities, graph, resolution

app = FastAPI(title="CrimeNet AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(entities.router)
app.include_router(graph.router)
app.include_router(resolution.router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Liveness plus a real round trip to Postgres."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"database unreachable: {exc}") from exc
    return {"status": "ok", "db": "connected"}
