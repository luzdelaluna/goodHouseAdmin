from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, UserRole
from app import crud, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/admin/filters", tags=["filters"])


def check_admin_access(current_user: dict):
    if current_user["role"] not in [UserRole.SUPERUSER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения этой операции"
        )


@router.post("/", response_model=schemas.Filter)
def create_filter(
        filter_data: schemas.FilterCreate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
        check_admin_access(current_user)

        existing_filter = crud.get_filter_by_value(db, value=filter_data.value)
        if existing_filter:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Фильтр с таким значением уже существует"
            )

        return crud.create_filter(db, filter_data)


@router.get("/", response_model=List[schemas.Filter])
def read_filters(
        skip: int = 0,
        limit: int = 100,
        is_active: bool = None,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
        check_admin_access(current_user)
        filters = crud.get_filters(db, skip=skip, limit=limit, is_active=is_active)
        return filters


@router.get("/{filter_id}", response_model=schemas.Filter)
def read_filter(
        filter_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
        check_admin_access(current_user)
        db_filter = crud.get_filter(db, filter_id=filter_id)
        if db_filter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Фильтр не найден"
            )
        return db_filter


@router.put("/{filter_id}", response_model=schemas.Filter)
def update_filter(
        filter_id: int,
        filter_data: schemas.FilterUpdate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
        check_admin_access(current_user)
        db_filter = crud.update_filter(db, filter_id=filter_id, filter_data=filter_data)
        if db_filter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Фильтр не найден"
            )
        return db_filter


@router.delete("/{filter_id}")
def delete_filter(
        filter_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
        check_admin_access(current_user)
        db_filter = crud.delete_filter(db, filter_id=filter_id)
        if db_filter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Фильтр не найден"
            )
        return {"message": "Фильтр успешно удален"}
