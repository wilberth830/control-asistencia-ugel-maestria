"""CHIQUISTRUKIS API — TEC-D01/D04 entrypoint. Redis: infra/redis (aparte)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    attendance,
    auth,
    biometric_imports,
    dashboard,
    inconsistencies,
    justifications,
    reports,
    staff_members,
)
from app.repositories.oracle import warm_oracle_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    warm_oracle_pool()
    yield


app = FastAPI(title="CHIQUISTRUKIS API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
    ],
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(staff_members.router)
app.include_router(biometric_imports.router)
app.include_router(inconsistencies.router)
app.include_router(attendance.router)
app.include_router(justifications.router)
app.include_router(reports.router)
app.include_router(dashboard.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "chiquistrukis-api", "tec": "D01-D12 scaffold"}
