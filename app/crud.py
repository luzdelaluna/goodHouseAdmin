from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from . import models, schemas


def get_categories_count(db: Session) -> int:
    return db.query(models.Category).count()


def get_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Category).offset(skip).limit(limit).all()


def get_category_by_id(db: Session, category_id: int):
    return db.query(models.Category).filter(models.Category.id == category_id).first()


def get_category_by_slug(db: Session, slug: str):
    return db.query(models.Category).filter(models.Category.slug == slug).first()


def create_category(db: Session, category: schemas.CategoryCreate):
    base_slug = category.slug
    counter = 1
    current_slug = base_slug

    while True:
        existing_category = db.query(models.Category).filter(models.Category.slug == current_slug).first()
        if not existing_category:
            category.slug = current_slug
            break

        current_slug = f"{base_slug}-{counter}"
        counter += 1

    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def update_category(db: Session, category_id: int, category_update: schemas.CategoryUpdate):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category:

        new_slug = category_update.generate_slug(
            current_text=db_category.text,
            new_text=category_update.text
        )

        update_data = category_update.dict(exclude_unset=True)

        if new_slug is not None:
            update_data['slug'] = new_slug

        for key, value in update_data.items():
            setattr(db_category, key, value)

        db.commit()
        db.refresh(db_category)
    return db_category


def delete_category(db: Session, category_id: int):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category:
        db.delete(db_category)
        db.commit()
    return db_category


def get_subcategories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Subcategory).offset(skip).limit(limit).all()


def get_subcategory_by_id(db: Session, subcategory_id: int):
    return db.query(models.Subcategory).filter(models.Subcategory.id == subcategory_id).first()


def get_subcategory_by_slug(db: Session, slug: str):
    return db.query(models.Subcategory).filter(models.Subcategory.slug == slug).first()


def get_products_count_by_subcategory(db: Session, subcategory_id: int) -> int:
    return db.query(models.Product).filter(models.Product.subcategory_id == subcategory_id).count()


def create_subcategory(db: Session, subcategory: schemas.SubcategoryCreate):
    db_subcategory = models.Subcategory(**subcategory.dict())
    db.add(db_subcategory)
    db.commit()
    db.refresh(db_subcategory)
    return db_subcategory


def update_subcategory(db: Session, subcategory_id: int, subcategory_update: schemas.SubcategoryUpdate):
    db_subcategory = db.query(models.Subcategory).filter(models.Subcategory.id == subcategory_id).first()
    if db_subcategory:
        new_slug = subcategory_update.generate_slug(
            current_text=db_subcategory.text,
            new_text=subcategory_update.text
        )

        update_data = subcategory_update.dict(exclude_unset=True)
        if new_slug is not None:
            update_data['slug'] = new_slug

        for key, value in update_data.items():
            setattr(db_subcategory, key, value)

        db.commit()
        db.refresh(db_subcategory)
    return db_subcategory


def delete_subcategory(db: Session, subcategory_id: int):
    products_count = db.query(models.Product).filter(models.Product.subcategory_id == subcategory_id).count()
    if products_count > 0:
        raise ValueError(f"Cannot delete subcategory with {products_count} products")

    subcategory = db.query(models.Subcategory).filter(models.Subcategory.id == subcategory_id).first()
    if subcategory:
        db.delete(subcategory)
        db.commit()
        return {"message": "Subcategory deleted successfully"}
    return None


def get_brands(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Brand).offset(skip).limit(limit).all()


def get_brand_by_id(db: Session, brand_id: int):
    return db.query(models.Brand).filter(models.Brand.id == brand_id).first()


def create_brand(db: Session, brand: schemas.BrandCreate):
    db_brand = models.Brand(**brand.dict())
    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)
    return db_brand


def update_brand(db: Session, brand_id: int, brand: schemas.BrandCreate):
    db_brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
    if db_brand:
        for key, value in brand.dict().items():
            setattr(db_brand, key, value)
        db.commit()
        db.refresh(db_brand)
    return db_brand


def delete_brand(db: Session, brand_id: int):
    db_brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
    if db_brand:
        db.delete(db_brand)
        db.commit()
    return db_brand


def get_products(db: Session, skip: int = 0, limit: int = 100):
    products = db.query(models.Product).offset(skip).limit(limit).all()

    products_data = []
    for product in products:
        images = db.query(models.ProductImage.image_url).filter(
            models.ProductImage.product_id == product.id
        ).all()

        product_data = {
            "id": product.id,
            "text": product.text,
            "article": product.article,
            "price": product.price,
            "discount": product.discount,
            "slug": product.slug,
            "in_stock": product.in_stock,
            "small_description": product.small_description,
            "full_description": product.full_description,
            "subcategory_id": product.subcategory_id,
            "brand_id": product.brand_id,
            "images": [img.image_url for img in images]
        }
        products_data.append(product_data)

    return products_data


def get_product_by_id(db: Session, product_id: int):
    return db.query(models.Product).options(
        joinedload(models.Product.images)
    ).filter(models.Product.id == product_id).first()


def get_product_by_slug(db: Session, slug: str):
    return db.query(models.Product).filter(models.Product.slug == slug).first()


def get_product_by_article(db: Session, article: int):
    return db.query(models.Product).filter(models.Product.article == article).first()


def create_product(db: Session, product: schemas.ProductCreate):
    if product.article and db.query(models.Product).filter(models.Product.article == product.article).first():
        import uuid
        import datetime
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        unique_id = str(uuid.uuid4())[:6].upper()
        product.article = f"PRD-{timestamp}-{unique_id}"
    elif not product.article:

        import uuid
        import datetime
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        unique_id = str(uuid.uuid4())[:6].upper()
        product.article = f"PRD-{timestamp}-{unique_id}"

    if product.slug and db.query(models.Product).filter(models.Product.slug == product.slug).first():
        counter = 1
        while True:
            new_slug = f"{product.slug}-{counter}"
            if not db.query(models.Product).filter(models.Product.slug == new_slug).first():
                product.slug = new_slug
                break
            counter += 1
    elif not product.slug:

        from slugify import slugify
        product.slug = slugify(product.text, lowercase=True, word_boundary=True)

        if db.query(models.Product).filter(models.Product.slug == product.slug).first():
            counter = 1
            while True:
                new_slug = f"{product.slug}-{counter}"
                if not db.query(models.Product).filter(models.Product.slug == new_slug).first():
                    product.slug = new_slug
                    break
                counter += 1

    product_data = product.dict(exclude={'images', 'tags', 'characteristics'})
    db_product = models.Product(**product_data)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    if hasattr(product, 'images') and product.images:
        for image_url in product.images:
            db_image = models.ProductImage(
                image_url=image_url,
                product_id=db_product.id
            )
            db.add(db_image)
        db.commit()

    if hasattr(product, 'characteristics') and product.characteristics:
        for char_data in product.characteristics:
            db_char = models.ProductCharacteristic(
                product_id=db_product.id,
                characteristic_id=char_data.characteristic_id,
                value=char_data.value
            )
            db.add(db_char)
        db.commit()

    db.refresh(db_product)
    images = db.query(models.ProductImage).filter(
        models.ProductImage.product_id == db_product.id
    ).all()

    characteristics = db.query(models.ProductCharacteristic).filter(
        models.ProductCharacteristic.product_id == db_product.id
    ).all()

    response_data = {
        "id": db_product.id,
        "text": db_product.text,
        "article": db_product.article,
        "price": db_product.price,
        "discount": db_product.discount,
        "slug": db_product.slug,
        "in_stock": db_product.in_stock,
        "small_description": db_product.small_description,
        "full_description": db_product.full_description,
        "subcategory_id": db_product.subcategory_id,
        "brand_id": db_product.brand_id,
        "images": [img.image_url for img in images],
        "characteristics": [
            {
                "id": char.id,
                "characteristic_id": char.characteristic_id,
                "value": char.value
            }
            for char in characteristics
        ]
    }

    return schemas.ProductResponse(**response_data)


def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate):
    db_product = db.query(models.Product).filter_by(id=product_id).first()
    if not db_product:
        return None

    new_slug = product_update.generate_slug(
        current_text=db_product.text,
        new_text=product_update.text
    )

    update_data = product_update.dict(exclude_unset=True)

    update_data = {k: v for k, v in update_data.items() if v is not None}

    if new_slug is not None:
        update_data['slug'] = new_slug

    for key, value in update_data.items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)

    return {
        "id": db_product.id,
        "text": db_product.text,
        "article": db_product.article,
        "price": db_product.price,
        "discount": db_product.discount,
        "slug": db_product.slug,
        "in_stock": db_product.in_stock,
        "small_description": db_product.small_description,
        "full_description": db_product.full_description,
        "subcategory_id": db_product.subcategory_id,
        "brand_id": db_product.brand_id
    }


def delete_product(db: Session, product_id: int):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product:
        db.delete(db_product)
        db.commit()
    return db_product


def get_products_by_brand(db: Session, brand_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Product).filter(models.Product.brand_id == brand_id).offset(skip).limit(limit).all()


def count_products_by_brand(db: Session, brand_id: int):
    return db.query(func.count(models.Product.id)).filter(models.Product.brand_id == brand_id).scalar()


def get_filters(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Filter).offset(skip).limit(limit).all()


def get_filter_by_id(db: Session, filter_id: int):
    return db.query(models.Filter).filter(models.Filter.id == filter_id).first()


def create_filter(db: Session, filter: schemas.FilterCreate):
    db_filter = models.Filter(**filter.dict())
    db.add(db_filter)
    db.commit()
    db.refresh(db_filter)
    return db_filter


def update_filter(db: Session, filter_id: int, filter: schemas.FilterCreate):
    db_filter = db.query(models.Filter).filter(models.Filter.id == filter_id).first()
    if db_filter:
        for key, value in filter.dict().items():
            setattr(db_filter, key, value)
        db.commit()
        db.refresh(db_filter)
    return db_filter


def delete_filter(db: Session, filter_id: int):
    db_filter = db.query(models.Filter).filter(models.Filter.id == filter_id).first()
    if db_filter:
        db.delete(db_filter)
        db.commit()
    return db_filter


def get_tag_by_name(db: Session, name: str):
    return db.query(models.Tag).filter(models.Tag.name == name).first()


def create_tag(db: Session, tag: schemas.TagCreate):
    db_tag = models.Tag(**tag.dict())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


def create_characteristic(db: Session, characteristic: schemas.CharacteristicCreate):
    db_characteristic = models.Characteristic(**characteristic.dict())
    db.add(db_characteristic)
    db.commit()
    db.refresh(db_characteristic)
    return db_characteristic
