from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas, database, models
from ..s3_service import s3_service, TimeWebS3Service
from ..dependencies import require_admin

router = APIRouter(prefix="/subcategories", tags=["subcategories"])


@router.post("/", response_model=schemas.Subcategory)
async def create_subcategory_with_upload(
        text: str = Form(...),
        slug: Optional[str] = Form(None),
        category_id: int = Form(...),
        brand_id: Optional[int] = Form(None),
        image: UploadFile = File(...),
        db: Session = Depends(database.get_db),
        _: dict = Depends(require_admin)
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


@router.get("/", response_model=schemas.SubcategoryPaginatedResponse)
def read_subcategories(
        page: int = Query(1, ge=1, description="Номер страницы"),
        limit: int = Query(10, ge=1, le=100, description="Количество записей на странице (1-100)"),
        db: Session = Depends(database.get_db)
):
    try:

        skip = (page - 1) * limit

        subcategories = crud.get_subcategories(db, skip=skip, limit=limit)

        total_count = crud.get_subcategories_count(db)

        total_pages = (total_count + limit - 1) // limit

        return {
            "data": subcategories,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "limit": limit,
                "total_items": total_count
            }
        }

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


@router.patch("/{subcategory_id}", response_model=schemas.Subcategory)
async def update_subcategory(
        subcategory_id: int,
        image: Optional[UploadFile] = File(None),
        text: Optional[str] = Form(None),
        slug: Optional[str] = Form(None),
        category_id: Optional[int] = Form(None),
        brand_id: Optional[int] = Form(None),
        db: Session = Depends(database.get_db),
        _: dict = Depends(require_admin)
):
    try:
        db_subcategory = crud.get_subcategory_by_id(db, subcategory_id=subcategory_id)
        if db_subcategory is None:
            raise HTTPException(status_code=404, detail="Subcategory not found")

        update_data = {}

        if image and image.filename:
            new_image_url = await s3_service.upload_file(image, "images")
            if db_subcategory.image:
                await s3_service.delete_file(db_subcategory.image)
            update_data["image"] = new_image_url

        if text is not None:
            update_data["text"] = text

        if slug is not None:
            update_data["slug"] = slug

        if category_id is not None:

            db_category = crud.get_category_by_id(db, category_id=category_id)
            if db_category is None:
                raise HTTPException(status_code=404, detail="Category not found")
            update_data["category_id"] = category_id

        if brand_id is not None:

            db_brand = crud.get_brand_by_id(db, brand_id=brand_id)
            if db_brand is None:
                raise HTTPException(status_code=404, detail="Brand not found")
            update_data["brand_id"] = brand_id

        if text is not None and text != db_subcategory.text and slug is None:
            from slugify import slugify

            update_data["slug"] = slugify(text, lowercase=True, word_boundary=True)

        if update_data:
            return crud.update_subcategory(
                db=db,
                subcategory_id=subcategory_id,
                subcategory_update=schemas.SubcategoryUpdate(**update_data)
            )
        else:

            return db_subcategory

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{subcategory_id}")
async def delete_subcategory(
        subcategory_id: int,
        db: Session = Depends(database.get_db),
        _: dict = Depends(require_admin),
        s3_service: TimeWebS3Service = Depends()
):
    try:
        subcategory = crud.get_subcategory_by_id(db, subcategory_id=subcategory_id)
        if subcategory is None:
            raise HTTPException(status_code=404, detail="Subcategory not found")

        products_count = crud.get_products_count_by_subcategory(db, subcategory_id=subcategory_id)
        if products_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete subcategory with {products_count} associated products"
            )

        if subcategory.image:
            await s3_service.delete_file(subcategory.image)

        return crud.delete_subcategory(db=db, subcategory_id=subcategory_id)

    except HTTPException as e:
        raise e
    except Exception as e:

        print(f"Error deleting subcategory {subcategory_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
