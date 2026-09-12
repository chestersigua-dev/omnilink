import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Server Config
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'omnilink.db'}")

# Security / JWT
JWT_SECRET = os.getenv("JWT_SECRET", "omnilink_super_secret_capstone_key_2026_x99")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # 24 hours

# IoT Discovery / Simulation Mode
# Defaults to True for immediate capstone presentation, can be toggled via env or runtime flag
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() in ("true", "1", "yes")

# Storage Directories
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
AVATARS_DIR = UPLOAD_DIR / "avatars"

# Ensure runtime directories exist
AVATARS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
