from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from .. import crud, schemas, database, models
from ..s3_service import s3_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=schemas.ProductResponse)
async def create_product_with_upload(
        text: str = Form(...),
        price: float = Form(...),
        subcategory_id: int = Form(...),
        brand_id: int = Form(...),
        article: Optional[int] = Form(None),
        slug: Optional[str] = Form(None),
        discount: float = Form(0),
        images: List[UploadFile] = File(..., description="От 1 до 15 изображений"),
        db: Session = Depends(database.get_db)
):
    try:

        if len(images) < 1:
            raise HTTPException(status_code=400, detail="Должна быть как минимум 1 картинка")
        if len(images) > 15:
            raise HTTPException(status_code=400, detail="Не более 15 картинок")

        subcategory = db.query(models.Subcategory).filter(models.Subcategory.id == subcategory_id).first()
        if not subcategory:
            raise HTTPException(status_code=404, detail=f"Subcategory with id {subcategory_id} not found")

        brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
        if not brand:
            raise HTTPException(status_code=404, detail=f"Brand with id {brand_id} not found")

        image_urls = []
        for image in images:
            if image and image.filename and image.filename.strip():
                image_url = await s3_service.upload_file(image, "products")
                image_urls.append(image_url)

        product_data = {
            "images": image_urls,
            "text": text,
            "price": price,
            "subcategory_id": subcategory_id,
            "brand_id": brand_id,
            "article": article,
            "slug": slug,
            "discount": discount
        }

        db_product = crud.create_product(db=db, product=schemas.ProductCreate(**product_data))
        return db_product

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating product: {str(e)}")


@router.get("/", response_model=schemas.PaginatedResponse)
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    try:
        products = crud.get_products(db, skip=skip, limit=limit)
        total = db.query(crud.models.Product).count()
        return {
            "items": products,
            "total": total,
            "page": skip // limit + 1,
            "size": limit,
            "pages": (total + limit - 1) // limit
        }
    except HTTPException as e:
        raise e


@router.get("/{slug}", response_model=schemas.ProductDetail)
def read_product(slug: str, db: Session = Depends(database.get_db)):
    try:
        product = crud.get_product_by_slug(db, slug=slug)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        product_detail = schemas.ProductDetail.from_orm(product)
        product_detail.warehouses = [wh.address for wh in product.warehouses]
        product_detail.documents = [{"name": doc.name, "file_url": doc.file_url} for doc in product.documents]
        product_detail.images = [img.image_url for img in product.images]
        product_detail.additional_products = [
            {"name": ap.name, "value": ap.value, "product_slug": ap.product_slug}
            for ap in product.additional_products
        ]

        return product_detail
    except HTTPException as e:
        raise e


@router.get("/slug/{slug}", response_model=schemas.ProductDetail)
def read_product_by_slug(slug: str, db: Session = Depends(database.get_db)):
    try:
        product = crud.get_product_by_slug(db, slug=slug)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        product_detail = schemas.ProductDetail.from_orm(product)
        product_detail.warehouses = [wh.address for wh in product.warehouses]
        product_detail.documents = [{"name": doc.name, "file_url": doc.file_url} for doc in product.documents]
        product_detail.images = [img.image_url for img in product.images]
        product_detail.additional_products = [
            {"name": ap.name, "value": ap.value, "product_slug": ap.product_slug}
            for ap in product.additional_products
        ]

        return product_detail
    except HTTPException as e:
        raise e


@router.patch("/{product_id}", response_model=schemas.Product)
async def update_product(
        product_id: int,
        text: Optional[str] = Form(None),
        article: Optional[int] = Form(None),
        price: Optional[float] = Form(None),
        slug: Optional[str] = Form(None),
        subcategory_id: Optional[int] = Form(None),
        brand_id: Optional[int] = Form(None),
        discount: Optional[float] = Form(None),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(database.get_db)
):
    try:
        db_product = crud.get_product_by_id(db, product_id=product_id)
        if db_product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        update_data = {}


        if image is not None and hasattr(image, 'filename') and image.filename and image.filename.strip():
            new_image_url = await s3_service.upload_file(image, "images")
            if db_product.image:
                await s3_service.delete_file(db_product.image)
            update_data["image"] = new_image_url


        if text is not None:
            update_data["text"] = text


        if article is not None:
            update_data["article"] = article

        if price is not None:
            update_data["price"] = price

        if slug is not None:
            update_data["slug"] = slug


        if subcategory_id is not None:
            db_subcategory = crud.get_subcategory_by_id(db, subcategory_id=subcategory_id)
            if db_subcategory is None:
                raise HTTPException(status_code=404, detail="Subcategory not found")
            update_data["subcategory_id"] = subcategory_id

        if brand_id is not None:
            db_brand = crud.get_brand_by_id(db, id=brand_id)
            if db_brand is None:
                raise HTTPException(status_code=404, detail="Brand not found")
            update_data["brand_id"] = brand_id

        if discount is not None:
            update_data["discount"] = discount


        if text is not None and text != db_product.text and slug is None:
            from slugify import slugify
            update_data["slug"] = slugify(text, lowercase=True, word_boundary=True)


        if update_data:
            return crud.update_product(
                db=db,
                product_id=product_id,
                product_update=schemas.ProductUpdate(**update_data)
            )
        else:
            return db_product

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    try:
        product = crud.get_product_by_id(db, product_id=product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        if product.image:
            s3_service.delete_file(product.image)

        return crud.delete_product(db=db, product_id=product_id)
    except HTTPException as e:
        raise e
