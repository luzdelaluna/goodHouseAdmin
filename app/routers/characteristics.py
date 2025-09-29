from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import UserRole
from app import crud, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/admin/characteristics", tags=["characteristics"])


def check_admin_access(current_user: dict):
    if current_user["role"] not in [UserRole.SUPERUSER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения этой операции"
        )


@router.post("/", response_model=schemas.Characteristic)
def create_characteristic(
        characteristic_data: schemas.CharacteristicCreate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
    check_admin_access(current_user)

    existing_characteristic = crud.get_characteristic_by_value(db, value=characteristic_data.value)
    if existing_characteristic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Характеристика с таким значением уже существует"
        )

    return crud.create_characteristic(db, characteristic_data)


@router.get("/", response_model=schemas.CharacteristicPaginatedResponse)
def read_characteristics(
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(10, ge=1, le=100, description="Размер страницы"),
        is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
        db: Session = Depends(get_db),
        # current_user: dict = Depends(get_current_user)
):
    # check_admin_access(current_user)

    items, total = crud.get_characteristics_paginated(
        db,
        page=page,
        size=size,
        is_active=is_active
    )

    pages = (total + size - 1) // size

    return schemas.CharacteristicPaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )



@router.get("/{characteristic_id}", response_model=schemas.Characteristic)
def read_characteristic(
        characteristic_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
    check_admin_access(current_user)
    db_characteristic = crud.get_characteristic(db, characteristic_id=characteristic_id)
    if db_characteristic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Характеристика не найдена"
        )
    return db_characteristic


@router.put("/{characteristic_id}", response_model=schemas.Characteristic)
def update_characteristic(
        characteristic_id: int,
        characteristic_data: schemas.CharacteristicUpdate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
    check_admin_access(current_user)
    db_characteristic = crud.update_characteristic(db, characteristic_id=characteristic_id,
                                                   characteristic_data=characteristic_data)
    if db_characteristic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Характеристика не найдена"
        )
    return db_characteristic


@router.delete("/{characteristic_id}")
def delete_characteristic(
        characteristic_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
    check_admin_access(current_user)
    db_characteristic = crud.delete_characteristic(db, characteristic_id=characteristic_id)
    if db_characteristic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Характеристика не найдена"
        )
    return {"message": "Характеристика успешно удалена"}
