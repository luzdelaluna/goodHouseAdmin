from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud, database, dependencies

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/", response_model=schemas.TagResponse)
def create_tag(
        tag: schemas.TagCreate,
        db: Session = Depends(database.get_db),
        _: dict = Depends(dependencies.require_admin)
):
    try:
        return crud.create_tag(db, tag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=schemas.TagPaginatedResponse)
def read_tags(
        page: int = Query(1, ge=1, description="Номер страницы"),
        limit: int = Query(10, ge=1, le=100, description="Количество записей на странице (1-100)"),
        db: Session = Depends(database.get_db)
):
    try:
        skip = (page - 1) * limit

        tags = crud.get_all_tags(db, skip=skip, limit=limit)

        total_count = crud.get_tags_count(db)

        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

        return {
            "data": tags,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "limit": limit,
                "total_items": total_count
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении тегов: {str(e)}")


@router.get("/{tag_id}", response_model=schemas.TagResponse)
def read_tag(tag_id: int, db: Session = Depends(database.get_db)):
    tag = crud.get_tag_by_id(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.get("/value/{tag_value}", response_model=schemas.TagResponse)
def read_tag_by_value(tag_value: str, db: Session = Depends(database.get_db)):
    tag = crud.get_tag_by_value(db, tag_value)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.get("/{tag_value}/products", response_model=schemas.ProductsByTagResponse)
def get_products_by_tag_value(
        tag_value: str,
        limit: int = Query(20, le=50),  # Максимум 50 продуктов
        db: Session = Depends(database.get_db)
):
    tag, products, total = crud.get_products_by_tag_value(db, tag_value, limit)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    return {
        "tag": tag,
        "products": products,
        "total": total
    }


@router.get("/{tag_id}/products", response_model=schemas.ProductsByTagResponse)
def get_products_by_tag_id(
        tag_id: int,
        limit: int = Query(20, le=50),
        db: Session = Depends(database.get_db)
):
    tag, products, total = crud.get_products_by_tag_id(db, tag_id, limit)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    return {
        "tag": tag,
        "products": products,
        "total": total
    }


@router.put("/{tag_id}", response_model=schemas.TagResponse)
def update_tag(
        tag_id: int,
        tag: schemas.TagUpdate,
        db: Session = Depends(database.get_db),
        _: dict = Depends(dependencies.require_admin)
):
    updated_tag = crud.update_tag(db, tag_id, tag)
    if not updated_tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return updated_tag


@router.delete("/{tag_id}")
def delete_tag(
        tag_id: int,
        db: Session = Depends(database.get_db),
        _: dict = Depends(dependencies.require_admin)
):
    tag = crud.delete_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"message": "Tag deleted successfully"}
