import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.config import STATIC_DIR, UPLOAD_DIR, AVATARS_DIR, HOST, PORT, SIMULATION_MODE, is_simulation_mode
from backend.database import init_db
from backend.routes.auth_routes import router as auth_router
from backend.routes.user_routes import router as user_router
from backend.routes.iot_routes import router as iot_router
from backend.routes.group_routes import router as group_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    # Ensure storage paths exist
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize SQLite database schema
    init_db()
    print(f"[*] OmniLink Monolith booted successfully on http://{HOST}:{PORT}")
    print(f"[*] Simulation Mode: {'ENABLED (Virtual Devices Active)' if SIMULATION_MODE else 'DISABLED (Physical LAN Scan)'}")
    yield

app = FastAPI(
    title="OmniLink Universal IoT Platform",
    description="Monolithic IoT orchestration engine supporting Xiaomi, TP-Link Tapo, Samsung, LG, and TCL.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(iot_router)
app.include_router(group_router)

# Mount uploads static directory for user profile avatars
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Mount static directory for CSS, JS, and images
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def read_index():
    """Serve the Single Page Application."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "OmniLink Backend Running. Frontend static files pending."}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "OmniLink Monolith",
        "simulation_mode": is_simulation_mode(),
        "supported_brands": ["xiaomi", "tapo", "samsung", "lg", "tcl"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
