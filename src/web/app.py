import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.web.core.config import WebConfig
from src.web.db.session import init_app_db
from src.web.api.v1.auth import router as auth_router
from src.web.api.v1.analytics import router as analytics_router
from src.web.api.v1.explorer import router as explorer_router
from src.web.api.v1.pipelines import router as pipelines_router
from src.web.api.v1.users import router as users_router
from src.web.api.v1.looker import router as looker_router

# Initialize database on startup
init_app_db()

app = FastAPI(
    title=WebConfig.PROJECT_NAME,
    version=WebConfig.VERSION,
    description="DashGrow Multi-Tenant Enterprise Data-as-a-Service Platform (B2B SaaS)"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API Routers
app.include_router(auth_router, prefix=WebConfig.API_V1_STR)
app.include_router(analytics_router, prefix=WebConfig.API_V1_STR)
app.include_router(explorer_router, prefix=WebConfig.API_V1_STR)
app.include_router(pipelines_router, prefix=WebConfig.API_V1_STR)
app.include_router(users_router, prefix=WebConfig.API_V1_STR)
app.include_router(looker_router, prefix=WebConfig.API_V1_STR)

# Static files directory path
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static directory for CSS, JS, Assets
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_portal():
    """Serves the DashGrow Single-Page Application (SPA) dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "online",
        "platform": "DashGrow Technologies Multi-Tenant Data Platform",
        "api_docs": "/docs",
        "api_v1": WebConfig.API_V1_STR
    }

@app.get("/health")
def health_check():
    """Health check endpoint for container probes & load balancers."""
    return {"status": "healthy", "service": "dashgrow-web-portal", "version": WebConfig.VERSION}
