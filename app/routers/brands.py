from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas, database
from ..s3_service import s3_service

router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("/", response_model=schemas.Brand)
async def create_brand_with_upload(
        name: str = Form(...),
        image: UploadFile = File(...),
        db: Session = Depends(database.get_db)
):
    try:
        image_url = await s3_service.upload_file(image, "brands")

        brand_data = {
            "name": name,
            "image": image_url
        }

        return crud.create_brand(db=db, brand=schemas.BrandCreate(**brand_data))
    except HTTPException as e:
        raise e


@router.get("/", response_model=List[schemas.Brand])
def read_brands(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    try:
        brands = crud.get_brands(db, skip=skip, limit=limit)
        return brands
    except HTTPException as e:
        raise e


@router.get("/{brand_id}/products", response_model=schemas.PaginatedResponse)
def read_brand_products(brand_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    try:
        brand = crud.get_brand_by_id(db, brand_id=brand_id)
        if brand is None:
            raise HTTPException(status_code=404, detail="Brand not found")

        products = crud.get_products_by_brand(db, brand_id=brand_id, skip=skip, limit=limit)
        total = crud.count_products_by_brand(db, brand_id=brand_id)

        return {
            "items": products,
            "total": total,
            "page": skip // limit + 1,
            "size": limit,
            "pages": (total + limit - 1) // limit
        }
    except HTTPException as e:
        raise e



@router.put("/{brand_id}", response_model=schemas.Brand)
async def update_brand_with_upload(
        brand_id: int,
        name: str = Form(...),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(database.get_db)
):
    try:
        db_brand = crud.get_brand_by_id(db, brand_id=brand_id)
        if db_brand is None:
            raise HTTPException(status_code=404, detail="Brand not found")

        image_url = db_brand.image
        if image:
            if db_brand.image:
                await s3_service.delete_file(db_brand.image)
            image_url = await s3_service.upload_file(image, "brands")

        brand_data = {
            "name": name,
            "image": image_url
        }

        return crud.update_brand(db=db, brand_id=brand_id, brand=schemas.BrandCreate(**brand_data))
    except HTTPException as e:
        raise e


@router.delete("/{brand_id}")
def delete_brand(brand_id: int, db: Session = Depends(database.get_db)):
    try:
        brand = crud.get_brand_by_id(db, brand_id=brand_id)
        if brand is None:
            raise HTTPException(status_code=404, detail="Brand not found")

        if brand.image:
            s3_service.delete_file(brand.image)

        return crud.delete_brand(db=db, brand_id=brand_id)
    except HTTPException as e:
        raise e
