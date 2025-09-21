from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas


def get_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Category).offset(skip).limit(limit).all()


def get_category_by_id(db: Session, category_id: int):
    return db.query(models.Category).filter(models.Category.id == category_id).first()


def get_category_by_slug(db: Session, slug: str):
    return db.query(models.Category).filter(models.Category.slug == slug).first()


def create_category(db: Session, category: schemas.CategoryCreate):
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
    db_subcategory = db.query(models.Subcategory).filter(models.Subcategory.id == subcategory_id).first()
    if db_subcategory:
        db.delete(db_subcategory)
        db.commit()
    return db_subcategory


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
    return db.query(models.Product).offset(skip).limit(limit).all()


def get_product_by_id(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def get_product_by_slug(db: Session, slug: str):
    return db.query(models.Product).filter(models.Product.slug == slug).first()


def get_product_by_article(db: Session, article: str):
    return db.query(models.Product).filter(models.Product.article == article).first()


def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.dict(exclude={'tags', 'characteristics'}))

    if product.tags:
        for tag_name in product.tags:
            tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
            if not tag:
                tag = models.Tag(name=tag_name)
                db.add(tag)
            db_product.tags.append(tag)

    if product.characteristics:
        for char_data in product.characteristics:
            characteristic = models.Characteristic(**char_data.dict())
            db.add(characteristic)
            db_product.characteristics.append(characteristic)

    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate):
    db_product = db.query(models.Product).filter_by(id=product_id).first()
    if db_product:
        new_slug = product_update.generate_slug(
            current_text=db_product.text,
            new_text=product_update.text
        )

        update_data = product_update.dict(exclude_unset=True)
        if new_slug is not None:
            update_data['slug'] = new_slug

        for key, value in update_data.items():
            setattr(db_product, key, value)

        db.commit()
        db.refresh(db_product)
    return db_product


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
