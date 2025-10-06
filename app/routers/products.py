from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import or_, Float
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List, cast
from pydantic_core import ValidationError
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
        characteristics: Optional[str] = Form(None),
        images: List[UploadFile] = File(..., description="От 1 до 15 изображений"),
        db: Session = Depends(database.get_db),
        _current_user: dict = Depends(dependencies.require_admin)
):
    try:
        # Проверка изображений
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

        # Проверка подкатегории
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

        # Парсинг характеристик
        characteristics_data = []
        if characteristics and characteristics.strip():
            try:
                characteristics_data = json.loads(characteristics)
                if not isinstance(characteristics_data, list):
                    raise ValueError("characteristics должен быть массивом")

                # Валидация структуры характеристик
                for char in characteristics_data:
                    if not all(key in char for key in ['name', 'label', 'value']):
                        raise ValueError("Каждая характеристика должна содержать name, label и value")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Неверный формат characteristics")

        # Загрузка изображений
        image_urls = []
        for image in images:
            if image and image.filename and image.filename.strip():
                image_url = await s3_service.upload_file(image, "products")
                image_urls.append(image_url)

        # Подготовка данных для продукта
        product_data = {
            "text": text,
            "price": price,
            "subcategory_id": subcategory_id,
            "brand_id": brand_id_int,
            "article": article_int,
            "slug": slug,
            "discount": discount,
        }

        # Используем новую схему без валидации изображений
        try:
            product_create = schemas.ProductCreateForm(**product_data)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Ошибка валидации данных: {str(e)}")

        # Создаем продукт в базе данных
        db_product = crud.create_product_with_characteristics(
            db=db,
            product=product_create,  # Теперь передаем ProductCreateForm
            characteristics=characteristics_data,
            image_urls=image_urls
        )

        # Добавление тегов
        if tag_ids_list:
            for tag_id in tag_ids_list:
                product_tag = models.ProductTag(product_id=db_product.id, tag_id=tag_id)
                db.add(product_tag)
            db.commit()

        # Получение продукта с отношениями
        db_product_with_relations = db.query(models.Product).options(
            joinedload(models.Product.tags),
            joinedload(models.Product.brand),
            joinedload(models.Product.subcategory),
            joinedload(models.Product.images),
            joinedload(models.Product.characteristics_assoc).joinedload(models.ProductCharacteristic.characteristic)
        ).filter(models.Product.id == db_product.id).first()

        response_data = {
            **db_product_with_relations.__dict__,
            "images": [img.image_url for img in db_product_with_relations.images],
            "tags": db_product_with_relations.tags,
            "brand": db_product_with_relations.brand,
            "subcategory": db_product_with_relations.subcategory,
            "characteristics": db_product_with_relations.characteristics
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


@router.get("/{slug}", response_model=schemas.ProductDetail, operation_id="get_product_by_slug")
def read_product(slug: str, db: Session = Depends(database.get_db)):
    try:
        product = crud.get_product_by_slug(db, slug=slug)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        # Преобразуем в схему
        product_detail = schemas.ProductDetail(
            id=product.id,
            text=product.text,
            article=product.article,
            price=product.price,
            discount=product.discount,
            slug=product.slug,
            in_stock=product.in_stock,
            small_description=product.small_description,
            full_description=product.full_description,
            subcategory_id=product.subcategory_id,
            brand_id=product.brand_id,
            images=[img.image_url for img in product.images],
            characteristics=[
                schemas.CharacteristicItemResponse(
                    id=char.id,
                    name=char.name,
                    label=char.label,
                    value=char.value
                ) for char in product.characteristics
            ],
            tags=[schemas.TagResponse.from_orm(tag) for tag in product.tags],
            warehouses=[wh.address for wh in product.warehouses],
            documents=[{"name": doc.name, "file_url": doc.file_url} for doc in product.documents],
            additional_products=[
                {"name": ap.name, "value": ap.value, "product_slug": ap.product_slug}
                for ap in product.additional_products
            ],
            similar_products=[],  # Нужно добавить логику для similar_products
            characteristic_templates=[
                schemas.CharacteristicTemplateResponse(
                    id=template.id,
                    name=template.name,
                    description=template.description,
                    is_active=template.is_active,
                    created_at=template.created_at,
                    items=[
                        schemas.CharacteristicItemResponse(
                            id=item.id,
                            name=item.name,
                            label=item.label,
                            value=item.value
                        ) for item in template.items
                    ]
                ) for template in product.characteristic_templates
            ]
        )

        return product_detail

    except HTTPException as e:
        raise e


@router.patch("/{product_id}", response_model=schemas.ProductResponse, operation_id="update_product")
async def update_product(
        product_id: int,
        text: Optional[str] = Form(None),
        article: Optional[str] = Form(None),
        price: Optional[float] = Form(None),
        slug: Optional[str] = Form(None),
        subcategory_id: Optional[int] = Form(None),
        brand_id: Optional[str] = Form(None),
        discount: Optional[float] = Form(None),
        characteristics: Optional[str] = Form(None),
        images: Optional[List[UploadFile]] = File(None),
        db: Session = Depends(database.get_db),
        _current_user: dict = Depends(dependencies.require_admin)
):
    try:
        db_product = crud.get_product_by_id(db, product_id=product_id)
        if db_product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        update_data = {}

        # Обработка новых изображений
        if images is not None:
            new_image_urls = []
            for image in images:
                if image and image.filename and image.filename.strip():
                    image_url = await s3_service.upload_file(image, "products")
                    new_image_urls.append(image_url)

            # Добавляем новые изображения к существующим
            for image_url in new_image_urls:
                product_image = models.ProductImage(
                    product_id=product_id,
                    image_url=image_url
                )
                db.add(product_image)

        # Обработка текстовых полей (как в создании)
        if text is not None:
            update_data["text"] = text

        if article is not None and article.strip():
            try:
                article_int = int(article)
                # Проверяем уникальность артикула (кроме текущего продукта)
                existing_article = db.query(models.Product).filter(
                    models.Product.article == article_int,
                    models.Product.id != product_id
                ).first()
                if existing_article:
                    raise HTTPException(status_code=400, detail=f"Артикул {article_int} уже используется")
                update_data["article"] = article_int
            except ValueError:
                raise HTTPException(status_code=400, detail="article должен быть числом")

        if price is not None:
            update_data["price"] = price

        if slug is not None:
            # Проверяем уникальность slug (кроме текущего продукта)
            existing_slug = db.query(models.Product).filter(
                models.Product.slug == slug,
                models.Product.id != product_id
            ).first()
            if existing_slug:
                raise HTTPException(status_code=400, detail=f"Slug '{slug}' уже используется")
            update_data["slug"] = slug

        if subcategory_id is not None:
            db_subcategory = crud.get_subcategory_by_id(db, subcategory_id=subcategory_id)
            if db_subcategory is None:
                raise HTTPException(status_code=404, detail="Subcategory not found")
            update_data["subcategory_id"] = subcategory_id

        if brand_id is not None and brand_id.strip():
            try:
                brand_id_int = int(brand_id)
                db_brand = crud.get_brand_by_id(db, brand_id=brand_id_int)
                if db_brand is None:
                    raise HTTPException(status_code=404, detail="Brand not found")
                update_data["brand_id"] = brand_id_int
            except ValueError:
                raise HTTPException(status_code=400, detail="brand_id должен быть числом")

        if discount is not None:
            update_data["discount"] = discount

        # Автогенерация slug если изменилось название
        if text is not None and text != db_product.text and slug is None:
            from slugify import slugify
            base_slug = slugify(text, lowercase=True)
            # Генерируем уникальный slug
            counter = 1
            new_slug = base_slug
            while db.query(models.Product).filter(
                    models.Product.slug == new_slug,
                    models.Product.id != product_id
            ).first():
                new_slug = f"{base_slug}-{counter}"
                counter += 1
            update_data["slug"] = new_slug

        # Обновляем основные данные продукта
        if update_data:
            updated_product = crud.update_product(
                db=db,
                product_id=product_id,
                product_update=schemas.ProductUpdate(**update_data)
            )

        # Обработка характеристик (как в создании)
        if characteristics and characteristics.strip():
            try:
                characteristics_data = json.loads(characteristics)
                if not isinstance(characteristics_data, list):
                    raise ValueError("characteristics должен быть массивом")

                # Валидация структуры характеристик
                for char in characteristics_data:
                    if not all(key in char for key in ['name', 'label', 'value']):
                        raise ValueError("Каждая характеристика должна содержать name, label и value")

                # Удаляем старые характеристики
                db.query(models.ProductCharacteristic).filter(
                    models.ProductCharacteristic.product_id == product_id
                ).delete()

                # Удаляем старые characteristic_items которые больше нигде не используются
                old_chars = db.query(models.CharacteristicItem).join(
                    models.ProductCharacteristic
                ).filter(
                    models.ProductCharacteristic.product_id == product_id
                ).all()

                for old_char in old_chars:
                    # Проверяем используется ли характеристика в других продуктах
                    other_usage = db.query(models.ProductCharacteristic).filter(
                        models.ProductCharacteristic.characteristic_id == old_char.id,
                        models.ProductCharacteristic.product_id != product_id
                    ).first()
                    if not other_usage:
                        db.delete(old_char)

                # Добавляем новые характеристики (как в создании)
                for char_data in characteristics_data:
                    characteristic = models.CharacteristicItem(
                        name=char_data['name'],
                        label=char_data['label'],
                        value=char_data['value']
                    )
                    db.add(characteristic)
                    db.flush()

                    # СОЗДАЕМ СВЯЗЬ БЕЗ custom_value (как в создании)
                    product_char = models.ProductCharacteristic(
                        product_id=product_id,
                        characteristic_id=characteristic.id
                        # Не передаем custom_value если его нет в модели
                    )
                    db.add(product_char)

            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Неверный формат characteristics")

        db.commit()

        # Получаем обновленный продукт с отношениями
        db_product_with_relations = db.query(models.Product).options(
            joinedload(models.Product.tags),
            joinedload(models.Product.brand),
            joinedload(models.Product.subcategory),
            joinedload(models.Product.images),
            joinedload(models.Product.characteristics_assoc).joinedload(models.ProductCharacteristic.characteristic)
        ).filter(models.Product.id == product_id).first()

        # Формируем ответ (как в создании)
        product_characteristics = []
        for char_assoc in db_product_with_relations.characteristics_assoc:
            if char_assoc.characteristic:
                product_characteristics.append({
                    "id": char_assoc.characteristic.id,
                    "name": char_assoc.characteristic.name,
                    "label": char_assoc.characteristic.label,
                    "value": char_assoc.characteristic.value,
                })

        response_data = {
            **db_product_with_relations.__dict__,
            "images": [img.image_url for img in db_product_with_relations.images],
            "tags": db_product_with_relations.tags,
            "brand": db_product_with_relations.brand,
            "subcategory": db_product_with_relations.subcategory,
            "characteristics": product_characteristics
        }

        return response_data

    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{product_id}", operation_id="delete_product")
def delete_product(
        product_id: int,
        db: Session = Depends(database.get_db),
        _current_user: dict = Depends(dependencies.require_admin)
):
    try:
        # Находим продукт со всеми связями
        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Удаляем файлы из S3
        for image in product.images:
            if image.image_url:
                try:
                    s3_service.delete_file(image.image_url)
                except Exception as e:
                    print(f"Error deleting image from S3: {e}")

        # Удаляем продукт (связанные записи удалятся каскадно)
        db.delete(product)
        db.commit()

        return {"message": "Product deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting product: {str(e)}")
