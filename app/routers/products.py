from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from .. import crud, schemas, database, models
from ..s3_service import s3_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/with-upload", response_model=schemas.Product)
async def create_product_with_upload(
        text: str = Form(...),
        article: str = Form(...),
        price: float = Form(...),
        slug: Optional[str] = None,
        subcategory_id: int = Form(...),
        brand_id: int = Form(...),
        discount: float = Form(0),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(database.get_db)
):
    try:
        subcategory = db.query(models.Subcategory).filter(models.Subcategory.id == subcategory_id).first()
        if not subcategory:
            raise HTTPException(status_code=404, detail=f"Subcategory with id {subcategory_id} not found")

        brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
        if not brand:
            raise HTTPException(status_code=404, detail=f"Brand with id {brand_id} not found")

        image_url = None
        if image:
            image_url = await s3_service.upload_file(image, "products")

        product_data = {
            "image": image_url,
            "text": text,
            "article": article,
            "price": price,
            "slug": slug,
            "discount": discount,
            "subcategory_id": subcategory_id,
            "brand_id": brand_id
        }

        return crud.create_product(db=db, product=schemas.ProductCreate(**product_data))
    except HTTPException as e:
        raise e


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


@router.put("/{product_id}", response_model=schemas.Product)
async def update_product_with_upload(
        product_id: int,
        text: Optional[str] = Form(None),
        article: Optional[str] = Form(None),
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

        image_url = db_product.image
        if image:
            if db_product.image:
                await s3_service.delete_file(db_product.image)
            image_url = await s3_service.upload_file(image, "products")

        update_data = {}

        if text is not None:
            update_data["text"] = text
        if article is not None:
            update_data["article"] = article
        if price is not None:
            update_data["price"] = price
        if slug is not None:
            update_data["slug"] = slug
        if subcategory_id is not None:
            update_data["subcategory_id"] = subcategory_id
        if brand_id is not None:
            update_data["brand_id"] = brand_id
        if discount is not None:
            update_data["discount"] = discount
        if image_url != db_product.image:
            update_data["image"] = image_url

        if text is not None and text != db_product.text and slug is None:
            from slugify import slugify
            update_data["slug"] = slugify(text, lowercase=True, word_boundary=True)

        return crud.update_product(
            db=db,
            product_id=product_id,
            product_update=schemas.ProductUpdate(**update_data)
        )
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
