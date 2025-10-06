from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import UserRole
from app import crud, schemas
from app.auth import get_current_user
from ..dependencies import require_admin

router = APIRouter(prefix="/characteristics", tags=["characteristics"])


def check_admin_access(current_user: dict):
    if current_user["role"] not in [UserRole.SUPERUSER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения этой операции"
        )


@router.get("/", response_model=schemas.CharacteristicTemplatePaginatedResponse)
def read_characteristic_templates(
    search: Optional[str] = Query(None, description="Поисковый запрос"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=100, description="Количество записей на странице (1-100)"),
    db: Session = Depends(get_db)
):
    try:
        skip = (page - 1) * limit

        if search:
            # Поиск с пагинацией
            templates = crud.search_characteristic_templates(db, search_term=search, skip=skip, limit=limit)
            total_count = crud.search_characteristic_templates_count(db, search_term=search)
            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

            return {
                "data": templates,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "limit": limit,
                    "total_items": total_count,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        else:
            # Обычный список с пагинацией
            templates = crud.get_characteristic_templates(db, skip=skip, limit=limit)
            total_count = crud.get_characteristic_templates_count(db)
            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

            return {
                "data": templates,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "limit": limit,
                    "total_items": total_count,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении шаблонов характеристик: {str(e)}")

@router.get("/{template_id}", response_model=schemas.CharacteristicTemplateResponse)
def read_characteristic_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    template = crud.get_characteristic_template_by_id(db, template_id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон характеристик не найден")
    return template

@router.post("/", response_model=schemas.CharacteristicTemplateResponse)
def create_characteristic_template(
    template: schemas.CharacteristicTemplateCreate,
    db: Session = Depends(get_db),
    _current_user: dict = Depends(require_admin)
):
    try:
        return crud.create_characteristic_template(db=db, template=template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании шаблона: {str(e)}")

@router.put("/{template_id}", response_model=schemas.CharacteristicTemplateResponse)
def update_characteristic_template(
    template_id: int,
    template_update: schemas.CharacteristicTemplateUpdate,
    db: Session = Depends(get_db),
    _current_user: dict = Depends(require_admin)
):
    try:
        updated_template = crud.update_characteristic_template(db=db, template_id=template_id, template_update=template_update)
        if not updated_template:
            raise HTTPException(status_code=404, detail="Шаблон характеристик не найден")
        return updated_template
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении шаблона: {str(e)}")

@router.delete("/{template_id}")
def delete_characteristic_template(
    template_id: int,
    db: Session = Depends(get_db),
    _current_user: dict = Depends(require_admin)
):
    success = crud.delete_characteristic_template(db=db, template_id=template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Шаблон характеристик не найден")
    return {"message": "Шаблон характеристик успешно удален"}
