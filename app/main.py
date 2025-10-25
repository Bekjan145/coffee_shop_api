from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import endpoints
from app.core.database import startup, shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup()
    yield
    # Shutdown
    await shutdown()


app = FastAPI(
    title="Coffee Shop API - User Management",
    description="JWT auth, verification, and roles system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.auth.router, prefix="/auth", tags=["auth"])
app.include_router(endpoints.users.router, tags=["users"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
