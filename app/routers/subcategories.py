from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas, database, models
from ..s3_service import s3_service

router = APIRouter(prefix="/subcategories", tags=["subcategories"])


@router.post("/with-upload", response_model=schemas.Subcategory)
async def create_subcategory_with_upload(
        text: str = Form(...),
        slug: Optional[str] = None,
        category_id: int = Form(...),
        brand_id: Optional[int] = Form(None),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(database.get_db)
):
    try:
        category = db.query(models.Category).filter(models.Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail=f"Category with id {category_id} not found")

        if brand_id:
            brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
            if not brand:
                raise HTTPException(status_code=404, detail=f"Brand with id {brand_id} not found")

        image_url = None
        if image:
            image_url = await s3_service.upload_file(image, "images")

        subcategory_data = {
            "image": image_url,
            "text": text,
            "slug": slug,
            "category_id": category_id,
            "brand_id": brand_id
        }

        return crud.create_subcategory(db=db, subcategory=schemas.SubcategoryCreate(**subcategory_data))
    except HTTPException as e:
        raise e


@router.get("/", response_model=List[schemas.Subcategory])
def read_subcategories(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    try:
        return crud.get_subcategories(db, skip=skip, limit=limit)
    except HTTPException as e:
        raise e


@router.get("/{subcategory_id}", response_model=schemas.Subcategory)
def read_subcategory(subcategory_id: int, db: Session = Depends(database.get_db)):
    try:
        subcategory = crud.get_subcategory_by_id(db, subcategory_id=subcategory_id)
        if subcategory is None:
            raise HTTPException(status_code=404, detail="Subcategory not found")
        return subcategory
    except HTTPException as e:
        raise e


@router.get("/slug/{slug}", response_model=schemas.Subcategory)
def read_subcategory_by_slug(slug: str, db: Session = Depends(database.get_db)):
    try:
        subcategory = crud.get_subcategory_by_slug(db, slug=slug)
        if subcategory is None:
            raise HTTPException(status_code=404, detail="Subcategory not found")
        return subcategory
    except HTTPException as e:
        raise e


@router.put("/{subcategory_id}", response_model=schemas.Subcategory)
async def update_subcategory_with_upload(
        subcategory_id: int,
        text: Optional[str] = Form(None),
        slug: Optional[str] = Form(None),
        category_id: Optional[int] = Form(None),
        brand_id: Optional[int] = Form(None),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(database.get_db)
):
    try:
        db_subcategory = crud.get_subcategory_by_id(db, subcategory_id=subcategory_id)
        if db_subcategory is None:
            raise HTTPException(status_code=404, detail="Subcategory not found")

        image_url = db_subcategory.image
        if image:
            if db_subcategory.image:
                await s3_service.delete_file(db_subcategory.image)
            image_url = await s3_service.upload_file(image, "images")

        update_data = {}

        if text is not None:
            update_data["text"] = text
        if slug is not None:
            update_data["slug"] = slug
        if category_id is not None:
            update_data["category_id"] = category_id
        if brand_id is not None:
            update_data["brand_id"] = brand_id
        if image_url != db_subcategory.image:
            update_data["image"] = image_url

        if text is not None and text != db_subcategory.text and slug is None:
            from slugify import slugify
            update_data["slug"] = slugify(text, lowercase=True, word_boundary=True)

        return crud.update_subcategory(
            db=db,
            subcategory_id=subcategory_id,
            subcategory_update=schemas.SubcategoryUpdate(**update_data)
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{subcategory_id}")
def delete_subcategory(subcategory_id: int, db: Session = Depends(database.get_db)):
    try:
        subcategory = crud.get_subcategory_by_id(db, subcategory_id=subcategory_id)
        if subcategory is None:
            raise HTTPException(status_code=404, detail="Subcategory not found")

        if subcategory.image:
            s3_service.delete_file(subcategory.image)

        return crud.delete_subcategory(db=db, subcategory_id=subcategory_id)
    except HTTPException as e:
        raise e
