from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas, database
from ..s3_service import s3_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=schemas.Category)
async def create_category_with_upload(
        category_id: int,
        text: str = Form(...),
        icon: Optional[UploadFile] = File(None),
        slug: Optional[str] = None,
        db: Session = Depends(database.get_db)
):
    try:
        db_category = crud.get_category_by_id(db, category_id=category_id)
        if db_category is None:
            raise HTTPException(status_code=404, detail="Category not found")

        icon_url = db_category.icon
        if icon:
            if db_category.icon:
                await s3_service.delete_file(db_category.icon)
            icon_url = await s3_service.upload_file(icon, "icons")

        update_data = {}

        if text is not None:
            update_data["text"] = text
        if slug is not None:
            update_data["slug"] = slug
        if icon_url != db_category.icon:
            update_data["icon"] = icon_url

        if text is not None and text != db_category.text and slug is None:
            from slugify import slugify
            update_data["slug"] = slugify(text, lowercase=True, word_boundary=True)

        return crud.update_category(
            db=db,
            category_id=category_id,
            category_update=schemas.CategoryUpdate(**update_data)
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[schemas.Category])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    return crud.get_categories(db, skip=skip, limit=limit)


@router.get("/{category_id}", response_model=schemas.Category)
def read_category(category_id: int, db: Session = Depends(database.get_db)):
    try:
        category = crud.get_category_by_id(db, category_id=category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except HTTPException as e:
        raise e


@router.get("/slug/{slug}", response_model=schemas.Category)
def read_category_by_slug(slug: str, db: Session = Depends(database.get_db)):
    try:
        category = crud.get_category_by_slug(db, slug=slug)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except HTTPException as e:
        raise e


@router.put("/{category_id}", response_model=schemas.Category)
async def update_category_with_upload(
        category_id: int,
        text: Optional[str] = Form(None),
        slug: Optional[str] = Form(None),
        icon: Optional[UploadFile] = File(None),
        db: Session = Depends(database.get_db)
):
    try:
        db_category = crud.get_category_by_id(db, category_id=category_id)
        if db_category is None:
            raise HTTPException(status_code=404, detail="Category not found")

        icon_url = db_category.icon
        if icon:

            if db_category.icon:
                await s3_service.delete_file(db_category.icon)
            icon_url = await s3_service.upload_file(icon, "icons")

            final_text = text if text is not None else db_category.text
            final_slug = slug if slug is not None else db_category.slug

            if text is not None and text != db_category.text and slug is None:
                from slugify import slugify
                final_slug = slugify(text, lowercase=True, word_boundary=True)

        category_data = {
            "icon": icon_url,
            "text": text,
            "slug": slug
        }

        return crud.update_category(
            db=db,
            category_id=category_id,
            category_update=schemas.CategoryUpdate(**category_data)
        )
    except HTTPException as e:
        raise e


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(database.get_db)):
    try:
        category = crud.get_category_by_id(db, category_id=category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")

        if category.icon:
            s3_service.delete_file(category.icon)

        return crud.delete_category(db=db, category_id=category_id)
    except HTTPException as e:
        raise e
