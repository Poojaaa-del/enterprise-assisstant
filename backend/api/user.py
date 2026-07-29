# backend/api/user.py
"""
User Management API
- /api/v1/user/me              : Get full authenticated user profile + live usage statistics
- /api/v1/user/profile         : Update display name, department, avatar color & receive refreshed JWT token
- /api/v1/user/change-password : Change account password with current password verification
"""

import os
import sqlite3
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from api.auth import get_current_user, create_access_token, verify_password, get_password_hash

from pathlib import Path

router = APIRouter(prefix="/api/v1/user", tags=["User Management"])

BASE_DIR      = Path(__file__).resolve().parent.parent
DATABASE_PATH = str(BASE_DIR / "triage.db")


class ProfileUpdateRequest(BaseModel):
    full_name: str
    department: str
    avatar_color: Optional[str] = "from-cyan-500 to-blue-600"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def format_user_dict(user: User) -> dict:
    """Helper to convert User model into clean dictionary response."""
    created_at_str = ""
    if user.created_at:
        created_at_str = (
            user.created_at.isoformat()
            if hasattr(user.created_at, "isoformat")
            else str(user.created_at)
        )

    role_str = str(user.role.value) if hasattr(user.role, "value") else str(user.role or "USER")

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name or user.username or user.email.split("@")[0],
        "department": user.department or "General",
        "avatar_color": user.avatar_color or "from-cyan-500 to-blue-600",
        "role": role_str,
        "created_at": created_at_str,
    }


@router.get("/me")
def get_user_profile(current_user: User = Depends(get_current_user)):
    """Returns full authenticated user profile metadata + live usage statistics."""
    print(f"[INFO] [UserProfile] Fetching profile for user_id={current_user.id}")

    usage = {"total_queries": 0, "total_uploads": 0, "total_audit_logs": 0}
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM query_audit_logs WHERE user_id = ?", (current_user.id,))
        row = cursor.fetchone()
        usage["total_queries"] = row["cnt"] if row else 0
        usage["total_audit_logs"] = usage["total_queries"]

        cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_files WHERE user_id = ?", (current_user.id,))
        row = cursor.fetchone()
        usage["total_uploads"] = row["cnt"] if row else 0
        conn.close()
    except Exception as stats_err:
        print(f"[WARNING] [UserProfile] Could not load usage stats: {stats_err}")

    user_info = format_user_dict(current_user)
    user_info["usage"] = usage
    return user_info


@router.put("/profile")
def update_user_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates full_name, department, and avatar_color for the logged-in user.
    Generates and returns an updated JWT token containing fresh claims.
    """
    print(f"[INFO] [UserProfile] Updating profile for user_id={current_user.id}")

    current_user.full_name = payload.full_name.strip()
    current_user.department = payload.department.strip()
    if payload.avatar_color:
        current_user.avatar_color = payload.avatar_color.strip()

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    user_dict = format_user_dict(current_user)

    # Issue updated JWT access token with new full_name, department, and avatar_color claims
    token_claims = {
        "sub": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "department": current_user.department,
        "avatar_color": current_user.avatar_color,
        "role": user_dict["role"],
    }
    new_token = create_access_token(data=token_claims)

    print(f"[OK] [UserProfile] Profile updated for user_id={current_user.id}, new JWT issued")
    return {
        "message": "Profile updated successfully",
        "access_token": new_token,
        "user": user_dict,
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verifies current password and updates to new password.
    Requires minimum 6 characters.
    """
    print(f"[INFO] [UserSecurity] Change password attempt for user_id={current_user.id}")

    if not verify_password(payload.current_password, current_user.hashed_password):
        print(f"[ERROR] [UserSecurity] Password verification failed for user_id={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long.",
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()

    print(f"[OK] [UserSecurity] Password successfully changed for user_id={current_user.id}")
    return {"message": "Password changed successfully"}
