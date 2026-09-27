from fastapi import FastAPI

from app.api.routes.employees import router as employees_router
from app.api.routes.departments import router as departments_router
from app.api.routes.analytics import router as analytics_router
app = FastAPI(
    title="OrbitHR API",
    description="AI-Native HR Lifecycle & Predictive Retention Platform",
    version="0.1.0",
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