from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import or_, Float
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List, cast
from .. import crud, schemas, database, models, dependencies
from ..s3_service import s3_service
import json

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=schemas.ProductResponse, operation_id="create_product")
async def create_product_with_upload(
        text: str = Form(...),
        price: float = Form(...),
        subcategory_id: int = Form(...),
        tag_ids: Optional[str] = Form(None),
        brand_id: Optional[str] = Form(None),
        article: Optional[str] = Form(None),
        slug: Optional[str] = Form(None),
        discount: float = Form(0),
        characteristics: str = Form("[]"),
        images: List[UploadFile] = File(..., description="От 1 до 15 изображений"),
        db: Session = Depends(database.get_db),
        _current_user: dict = Depends(dependencies.require_admin)
):
    try:

        if len(images) < 1:
            raise HTTPException(status_code=400, detail="Должно быть как минимум 1 изображение")
        if len(images) > 15:
            raise HTTPException(status_code=400, detail="Не более 15 изображений")

        article_int = None
        if article and article.strip():
            try:
                article_int = int(article)
            except ValueError:
                raise HTTPException(status_code=400, detail="article должен быть числом")

        subcategory = db.query(models.Subcategory).filter(models.Subcategory.id == subcategory_id).first()
        if not subcategory:
            raise HTTPException(status_code=404, detail=f"Subcategory with id {subcategory_id} not found")

        brand_id_int = None
        if brand_id and brand_id.strip():
            try:
                brand_id_int = int(brand_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="brand_id должен быть числом")

            brand = db.query(models.Brand).filter(models.Brand.id == brand_id_int).first()
            if not brand:
                raise HTTPException(status_code=404, detail=f"Brand with id {brand_id_int} not found")

        tag_ids_list = []
        if tag_ids and tag_ids.strip():
            try:
                tag_ids_list = json.loads(tag_ids)
                if not isinstance(tag_ids_list, list):
                    raise ValueError("tag_ids должен быть массивом")
                if not all(isinstance(tag_id, int) for tag_id in tag_ids_list):
                    raise ValueError("Все tag_ids должны быть числами")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Неверный формат tag_ids")

        if tag_ids_list:
            existing_tags = db.query(models.Tag).filter(models.Tag.id.in_(tag_ids_list)).all()
            existing_tag_ids = [tag.id for tag in existing_tags]
            non_existing_tags = set(tag_ids_list) - set(existing_tag_ids)
            if non_existing_tags:
                raise HTTPException(status_code=404, detail=f"Tags with ids {list(non_existing_tags)} not found")

        try:
            characteristics_data = json.loads(characteristics)
        except json.JSONDecodeError:
            characteristics_data = []

        image_urls = []
        for image in images:
            if image and image.filename and image.filename.strip():
                image_url = await s3_service.upload_file(image, "products")
                image_urls.append(image_url)

        product_data = {
            "text": text,
            "price": price,
            "subcategory_id": subcategory_id,
            "brand_id": brand_id_int,
            "article": article_int,
            "slug": slug,
            "discount": discount,
            "characteristics": characteristics_data,
            "images": image_urls
        }

        db_product = crud.create_product(db=db, product=schemas.ProductCreate(**product_data))

        if tag_ids_list:
            for tag_id in tag_ids_list:
                product_tag = models.ProductTag(product_id=db_product.id, tag_id=tag_id)
                db.add(product_tag)
            db.commit()

        db_product_with_relations = db.query(models.Product).options(
            joinedload(models.Product.tags),
            joinedload(models.Product.brand),
            joinedload(models.Product.subcategory),
            joinedload(models.Product.images)
        ).filter(models.Product.id == db_product.id).first()

        response_data = {
            **db_product_with_relations.__dict__,
            "images": [img.image_url for img in db_product_with_relations.images],
            "tags": db_product_with_relations.tags,
            "brand": db_product_with_relations.brand,
            "subcategory": db_product_with_relations.subcategory
        }

        return response_data

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating product: {str(e)}")


@router.get("/filter/", operation_id="get_filtered_products")
def get_filtered_products(
        page: int = Query(1, ge=1, description="Номер страницы"),
        page_size: int = Query(20, ge=1, le=100, description="Количество элементов на странице"),
        db: Session = Depends(database.get_db),

        **filters: str
):
    try:

        filter_params = {k: v for k, v in filters.items()
                         if k not in ['skip', 'limit', 'page', 'page_size']}

        skip = (page - 1) * page_size

        products = crud.get_products_with_filters(
            db,
            filters=filter_params,
            skip=skip,
            limit=page_size
        )

        total_count = crud.get_products_count_with_filters(db, filter_params)

        total_pages = (total_count + page_size - 1) // page_size

        result_products = []
        for product in products:
            product_data = schemas.ProductResponse.from_orm(product)
            product_data.images = [img.image_url for img in product.images]
            result_products.append(product_data)

        return {
            "products": result_products,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering products: {str(e)}")


def get_products_count_with_filters(db: Session, filters: dict):
    query = db.query(models.Product)

    for filter_name, filter_value in filters.items():
        if '-' in filter_value and any(c.isdigit() for c in filter_value):
            try:
                min_val, max_val = map(float, filter_value.split('-'))

                subquery = db.query(models.CharacteristicItem.product_id).join(
                    models.CharacteristicItem.characteristic
                ).filter(
                    or_(
                        models.Characteristic.name == filter_name,
                        models.Characteristic.label == filter_name
                    ),
                    cast(models.CharacteristicItem.value, Float) >= min_val,
                    cast(models.CharacteristicItem.value, Float) <= max_val
                ).subquery()

                query = query.filter(models.Product.id.in_(subquery))

            except ValueError:
                continue

        elif ',' in filter_value:
            values = [v.strip() for v in filter_value.split(',')]

            subquery = db.query(models.CharacteristicItem.product_id).join(
                models.CharacteristicItem.characteristic
            ).filter(
                or_(
                    models.Characteristic.name == filter_name,
                    models.Characteristic.label == filter_name
                ),
                models.CharacteristicItem.value.in_(values)
            ).subquery()

            query = query.filter(models.Product.id.in_(subquery))

        else:
            subquery = db.query(models.CharacteristicItem.product_id).join(
                models.CharacteristicItem.characteristic
            ).filter(
                or_(
                    models.Characteristic.name == filter_name,
                    models.Characteristic.label == filter_name
                ),
                models.CharacteristicItem.value == filter_value
            ).subquery()

            query = query.filter(models.Product.id.in_(subquery))

    return query.distinct().count()


def get_products_with_filters(
        db: Session,
        filters: dict,
        skip: int = 0,
        limit: int = 100
):
    query = db.query(models.Product)

    for filter_name, filter_value in filters.items():

        if '-' in filter_value and any(c.isdigit() for c in filter_value):
            try:
                min_val, max_val = map(float, filter_value.split('-'))

                subquery = db.query(models.CharacteristicItem.product_id).join(
                    models.CharacteristicItem.characteristic
                ).filter(

                    or_(
                        models.Characteristic.name == filter_name,
                        models.Characteristic.label == filter_name
                    ),
                    cast(models.CharacteristicItem.value, Float) >= min_val,
                    cast(models.CharacteristicItem.value, Float) <= max_val
                ).subquery()

                query = query.filter(models.Product.id.in_(subquery))

            except ValueError:
                continue


        elif ',' in filter_value:
            values = [v.strip() for v in filter_value.split(',')]

            subquery = db.query(models.CharacteristicItem.product_id).join(
                models.CharacteristicItem.characteristic
            ).filter(

                or_(
                    models.Characteristic.name == filter_name,
                    models.Characteristic.label == filter_name
                ),
                models.CharacteristicItem.value.in_(values)
            ).subquery()

            query = query.filter(models.Product.id.in_(subquery))


        else:
            subquery = db.query(models.CharacteristicItem.product_id).join(
                models.CharacteristicItem.characteristic
            ).filter(

                or_(
                    models.Characteristic.name == filter_name,
                    models.Characteristic.label == filter_name
                ),
                models.CharacteristicItem.value == filter_value
            ).subquery()

            query = query.filter(models.Product.id.in_(subquery))

    return query.distinct().offset(skip).limit(limit).all()


@router.get("/filters/{subcategory_id}", operation_id="get_available_filters_for_subcategory")
def get_available_filters(subcategory_id: int, db: Session = Depends(database.get_db)):
    return crud.get_filters_for_subcategory(db, subcategory_id)


@router.get("/", response_model=schemas.PaginatedResponse, operation_id="get_products_paginated")
def read_products(
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(20, ge=1, le=100, description="Размер страницы"),
        db: Session = Depends(database.get_db)
):
    try:
        skip = (page - 1) * size
        products = crud.get_products(db, skip=skip, limit=size)
        total = db.query(models.Product).count()

        return {
            "items": products,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if size > 0 else 1
        }
    except HTTPException as e:
        raise e


@router.get("/{slug}", response_model=schemas.ProductDetail, operation_id="get_product_by_id")
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


@router.get("/slug/{slug}", response_model=schemas.ProductDetail, operation_id="get_product_by_slug")
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


@router.patch("/{product_id}", response_model=schemas.Product, operation_id="update_product")
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
        db: Session = Depends(database.get_db),
        _current_user: dict = Depends(dependencies.require_admin)
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


@router.delete("/{product_id}", operation_id="delete_product")
def delete_product(
        product_id: int,
        db: Session = Depends(database.get_db),
        _current_user: dict = Depends(dependencies.require_admin)
):
    try:
        product = crud.get_product_by_id(db, product_id=product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        if product.image:
            s3_service.delete_file(product.image)

        return crud.delete_product(db=db, product_id=product_id)
    except HTTPException as e:
        raise e
