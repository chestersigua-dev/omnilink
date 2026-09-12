import os
import shutil
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.auth import get_current_user
from backend.config import AVATARS_DIR, BASE_DIR

router = APIRouter(prefix="/api/users", tags=["Users"])

ALLOWED_AVATAR_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None

@router.get("/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user.to_dict()

@router.put("/profile")
def update_user_profile(
    req: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if req.email and req.email != current_user.email:
        # Verify email is not taken by someone else
        existing = db.query(User).filter(User.email == req.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already used by another account"
            )
        current_user.email = req.email

    if req.full_name is not None:
        current_user.full_name = req.full_name
    if req.bio is not None:
        current_user.bio = req.bio

    db.commit()
    db.refresh(current_user)
    return {
        "message": "Profile updated successfully",
        "user": current_user.to_dict()
    }

@router.post("/avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # MIME-type validation
    content_type = (file.content_type or "").lower().strip()
    if content_type not in ALLOWED_AVATAR_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{content_type}'. Only PNG, JPG, and WebP are allowed."
        )

    extension = ALLOWED_AVATAR_MIME_TYPES[content_type]
    file_id = f"{current_user.id}_{uuid.uuid4().hex[:10]}{extension}"
    target_path = AVATARS_DIR / file_id

    # Clean up old uploaded avatar if not default
    if current_user.avatar_url and current_user.avatar_url.startswith("/uploads/avatars/"):
        old_filename = os.path.basename(current_user.avatar_url)
        old_file = AVATARS_DIR / old_filename
        if old_file.exists():
            try:
                old_file.unlink()
            except Exception:
                pass

    # Save to dedicated uploads directory
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    avatar_url = f"/uploads/avatars/{file_id}"
    current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)

    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url,
        "user": current_user.to_dict()
    }

@router.delete("/account")
def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes the current user account with cascading cleanup of
    associated devices, groups, and uploaded files.
    """
    # Delete uploaded avatar file if exists
    if current_user.avatar_url and current_user.avatar_url.startswith("/uploads/avatars/"):
        old_filename = os.path.basename(current_user.avatar_url)
        old_file = AVATARS_DIR / old_filename
        if old_file.exists():
            try:
                old_file.unlink()
            except Exception:
                pass

    # SQLAlchemy cascade will delete devices, groups, and device_group_members
    db.delete(current_user)
    db.commit()

    return {"message": "User account and all associated resources deleted successfully"}
