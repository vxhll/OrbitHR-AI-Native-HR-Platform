import sys
from pathlib import Path

from dotenv import load_dotenv

# Resolve project paths before importing application modules.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"

# Load environment variables from the backend configuration.
load_dotenv(BACKEND_ROOT / ".env")

# Ensure the root-level ml package takes precedence over backend/ml.
for path in (str(PROJECT_ROOT), str(BACKEND_ROOT)):
    while path in sys.path:
        sys.path.remove(path)

sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.employees import router as employees_router
from app.api.routes.departments import router as departments_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.rag import router as rag_router
from app.api.routes.recruitment import router as recruitment_router
from app.api.routes.onboarding import router as onboarding_router
from app.api.routes import support
from app.api.routes.leave import router as leave_router
from app.api.routes.offboarding import router as offboarding_router
from app.api.routes.exit_interviews import router as exit_interviews_router
from app.routers.auth.auth import router as auth_router

app = FastAPI(
    title="OrbitHR API",
    description="AI-Native HR Lifecycle & Predictive Retention Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "OrbitHR API",
        "version": "0.1.0",
    }


app.include_router(employees_router)
app.include_router(departments_router)
app.include_router(analytics_router)
app.include_router(rag_router)
app.include_router(recruitment_router)
app.include_router(onboarding_router)
app.include_router(support.router)
app.include_router(auth_router)
app.include_router(leave_router)
app.include_router(offboarding_router)
app.include_router(exit_interviews_router)
