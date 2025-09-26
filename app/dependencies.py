from fastapi import Depends, HTTPException, status
from .auth import get_current_user
from .schemas import UserRole, TokenData


def require_superuser(current_user: TokenData = Depends(get_current_user)):
    if current_user["role"] != UserRole.SUPERUSER:
        raise HTTPException(status_code=403, detail="Superuser access required")
    return current_user


def require_admin(current_user: TokenData = Depends(get_current_user)):
    if current_user["role"] not in [UserRole.SUPERUSER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def can_create_user(creator_role: UserRole, target_role: UserRole):
    return creator_role == UserRole.SUPERUSER and target_role == UserRole.ADMIN
