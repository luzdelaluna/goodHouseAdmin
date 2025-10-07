from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from text_unidecode import unidecode
from . import models, schemas, auth
from datetime import datetime, timedelta
import random
import string
import re
import transliterate


def generate_username():
    return f"user_{random.randint(10000, 99999)}"


def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_login(db: Session, login: str):
    user = get_user_by_email(db, login)
    if not user:
        user = get_user_by_username(db, login)
    return user


def authenticate_user(db: Session, login: str, password: str):
    user = get_user_by_login(db, login)
    if not user or not auth.verify_password(password, user.hashed_password):
        return False
    return user


def create_user_manual(db: Session, user_data: schemas.UserCreateManual, created_by: int = None):
    if user_data.email and get_user_by_email(db, user_data.email):
        raise ValueError("Email already exists")
    if user_data.username and get_user_by_username(db, user_data.username):
        raise ValueError("Username already exists")

    hashed_password = auth.get_password_hash(user_data.password)
    db_user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        role=user_data.role,
        created_by=created_by
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_user_auto(db: Session, user_data: schemas.UserCreateAuto, created_by: int = None):
    while True:
        username = generate_username()
        if not get_user_by_username(db, username):
            break

    password = generate_password()
    hashed_password = auth.get_password_hash(password)

    db_user = models.User(
        username=username,
        hashed_password=hashed_password,
        role=user_data.role,
        created_by=created_by
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user, password


def update_user(db: Session, user_id: int, user_data: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return None

    update_data = user_data.dict(exclude_unset=True)

    if 'email' in update_data and update_data['email']:

        existing_user = get_user_by_email(db, update_data['email'])
        if existing_user and existing_user.id != user_id:
            raise ValueError("Email already exists")
        db_user.email = update_data['email']

    if 'username' in update_data and update_data['username']:

        existing_user = get_user_by_username(db, update_data['username'])
        if existing_user and existing_user.id != user_id:
            raise ValueError("Username already exists")
        db_user.username = update_data['username']

    if 'password' in update_data and update_data['password']:
        db_user.hashed_password = auth.get_password_hash(update_data['password'])

    if 'is_active' in update_data:
        db_user.is_active = update_data['is_active']

    db.commit()
    db.refresh(db_user)
    return db_user


def create_refresh_token_db(db: Session, user_id: int):
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user_id
    ).delete()

    token = auth.generate_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)

    db_refresh_token = models.RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    db.commit()
    db.refresh(db_refresh_token)
    return db_refresh_token


def get_valid_refresh_token(db: Session, token: str):
    return db.query(models.RefreshToken).filter(
        models.RefreshToken.token == token,
        models.RefreshToken.expires_at > datetime.utcnow(),
        models.RefreshToken.is_revoked == False
    ).first()


def revoke_refresh_token(db: Session, token: str):
    db_token = get_valid_refresh_token(db, token)
    if db_token:
        db_token.is_revoked = True
        db.commit()
    return db_token


def revoke_all_user_tokens(db: Session, user_id: int):
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user_id
    ).update({"is_revoked": True})
    db.commit()


def get_categories_count(db: Session) -> int:
    return db.query(models.Category).count()


def get_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Category).offset(skip).limit(limit).all()


def get_category_by_id(db: Session, category_id: int):
    return db.query(models.Category).filter(models.Category.id == category_id).first()


def get_category_by_slug(db: Session, slug: str):
    return db.query(models.Category).filter(models.Category.slug == slug).first()


def search_categories(db: Session, search_term: str, skip: int = 0, limit: int = 100):
    return db.query(models.Category).filter(
        models.Category.text.ilike(f"%{search_term}%")
    ).offset(skip).limit(limit).all()


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


def get_subcategories_count(db: Session) -> int:
    return db.query(models.Subcategory).count()


def get_subcategories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Subcategory).offset(skip).limit(limit).all()


def get_subcategory_by_id(db: Session, subcategory_id: int):
    return db.query(models.Subcategory).filter(models.Subcategory.id == subcategory_id).first()


def get_subcategory_by_slug(db: Session, slug: str):
    return db.query(models.Subcategory).filter(models.Subcategory.slug == slug).first()


def get_products_count_by_subcategory(db: Session, subcategory_id: int) -> int:
    return db.query(models.Product).filter(models.Product.subcategory_id == subcategory_id).count()


def search_subcategories(db: Session, search_term: str, skip: int = 0, limit: int = 100):
    return db.query(models.Subcategory).options(
        joinedload(models.Subcategory.category)
    ).filter(
        models.Subcategory.text.ilike(f"%{search_term}%")
    ).offset(skip).limit(limit).all()


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


def get_characteristic_templates(db: Session, skip: int = 0, limit: int = 100) -> List[models.CharacteristicTemplate]:
    """Получить список шаблонов характеристик с пагинацией"""
    return db.query(models.CharacteristicTemplate).offset(skip).limit(limit).all()


def get_characteristic_templates_count(db: Session) -> int:
    """Получить общее количество шаблонов характеристик"""
    return db.query(models.CharacteristicTemplate).count()


def search_characteristic_templates(db: Session, search_term: str, skip: int = 0, limit: int = 100) -> List[
    models.CharacteristicTemplate]:
    """Поиск шаблонов характеристик по названию"""
    return db.query(models.CharacteristicTemplate).filter(
        models.CharacteristicTemplate.name.ilike(f"%{search_term}%")
    ).offset(skip).limit(limit).all()


def search_characteristic_templates_count(db: Session, search_term: str) -> int:
    """Получить количество найденных шаблонов характеристик"""
    return db.query(models.CharacteristicTemplate).filter(
        models.CharacteristicTemplate.name.ilike(f"%{search_term}%")
    ).count()


def get_characteristic_template_by_id(db: Session, template_id: int) -> Optional[models.CharacteristicTemplate]:
    """Получить шаблон характеристик по ID"""
    return db.query(models.CharacteristicTemplate).filter(
        models.CharacteristicTemplate.id == template_id
    ).first()


def get_characteristic_template_by_name(db: Session, name: str) -> Optional[models.CharacteristicTemplate]:
    """Получить шаблон характеристик по названию"""
    return db.query(models.CharacteristicTemplate).filter(
        models.CharacteristicTemplate.name == name
    ).first()


def create_characteristic_template(db: Session,
                                   template: schemas.CharacteristicTemplateCreate) -> models.CharacteristicTemplate:
    """Создать новый шаблон характеристик"""
    # Проверка уникальности имени
    existing_template = get_characteristic_template_by_name(db, template.name)
    if existing_template:
        raise ValueError(f"Шаблон с названием '{template.name}' уже существует")

    db_template = models.CharacteristicTemplate(
        name=template.name,
        description=template.description
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)

    # Добавление характеристик
    for char_data in template.characteristics:
        characteristic = models.CharacteristicItem(
            name=char_data.name,
            label=char_data.label,
            value=char_data.value,
            template_id=db_template.id
        )
        db.add(characteristic)

    db.commit()
    db.refresh(db_template)
    return db_template


def update_characteristic_template(db: Session, template_id: int,
                                   template_update: schemas.CharacteristicTemplateUpdate) -> Optional[
    models.CharacteristicTemplate]:
    """Обновить шаблон характеристик"""
    db_template = get_characteristic_template_by_id(db, template_id)
    if not db_template:
        return None

    # Проверка уникальности имени (если имя изменено)
    if template_update.name and template_update.name != db_template.name:
        existing_template = get_characteristic_template_by_name(db, template_update.name)
        if existing_template:
            raise ValueError(f"Шаблон с названием '{template_update.name}' уже существует")

    # Обновление полей
    update_data = template_update.model_dump(exclude_unset=True, exclude={'characteristics'})
    for field, value in update_data.items():
        setattr(db_template, field, value)

    # Обновление характеристик (если переданы)
    if hasattr(template_update, 'characteristics') and template_update.characteristics is not None:
        # Удаляем старые характеристики
        db.query(models.CharacteristicItem).filter(
            models.CharacteristicItem.template_id == template_id
        ).delete()

        # Добавляем новые характеристики
        for char_data in template_update.characteristics:
            characteristic = models.CharacteristicItem(
                name=char_data.name,
                label=char_data.label,
                value=char_data.value,
                template_id=db_template.id
            )
            db.add(characteristic)

    db.commit()
    db.refresh(db_template)
    return db_template


def delete_characteristic_template(db: Session, template_id: int) -> bool:
    """Удалить шаблон характеристик"""
    db_template = get_characteristic_template_by_id(db, template_id)
    if not db_template:
        return False

    db.delete(db_template)
    db.commit()
    return True


def get_products(db: Session, skip: int = 0, limit: int = 100):
    products = db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.tags)
    ).offset(skip).limit(limit).all()

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
            "characteristics": product.characteristics,
            "images": [img.image_url for img in images],
            "tags": [{"id": tag.id, "name": tag.name, "value": tag.value} for tag in product.tags]
        }
        products_data.append(product_data)

    return products_data


def get_product_by_id(db: Session, product_id: int):
    return db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.tags),
        joinedload(models.Product.warehouses),
        joinedload(models.Product.documents),
        joinedload(models.Product.additional_products)
    ).filter(models.Product.id == product_id).first()


def get_product_by_slug(db: Session, slug: str):
    """
    Получить продукт по slug со всеми отношениями
    """
    return db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.tags),
        joinedload(models.Product.brand),
        joinedload(models.Product.subcategory),
        joinedload(models.Product.warehouses),
        joinedload(models.Product.documents),
        joinedload(models.Product.additional_products),
        joinedload(models.Product.characteristics_assoc).joinedload(models.ProductCharacteristic.characteristic)
    ).filter(models.Product.slug == slug).first()


def get_product_by_article(db: Session, article: int):
    return db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.tags)
    ).filter(models.Product.article == article).first()


def create_product(db: Session, product: schemas.ProductCreate):
    # Генерация article если не передан
    def generate_numeric_article():
        return random.randint(100000, 999999)

    if product.article:
        # Проверка уникальности article
        if db.query(models.Product).filter(models.Product.article == product.article).first():
            while True:
                new_article = generate_numeric_article()
                if not db.query(models.Product).filter(models.Product.article == new_article).first():
                    product.article = new_article
                    break
    else:
        # Генерация нового article
        while True:
            new_article = generate_numeric_article()
            if not db.query(models.Product).filter(models.Product.article == new_article).first():
                product.article = new_article
                break

    # Генерация slug если не передан
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

    # Создание продукта
    product_data = product.model_dump(exclude={'images', 'tags', 'characteristics'})
    db_product = models.Product(**product_data)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # Добавление изображений
    if product.images:
        for image_url in product.images:
            product_image = models.ProductImage(
                image_url=image_url,
                product_id=db_product.id
            )
            db.add(product_image)

    # Добавление характеристик
    if hasattr(product, 'characteristics') and product.characteristics:
        for char_data in product.characteristics:
            # Создаем CharacteristicItem
            characteristic = models.CharacteristicItem(
                name=char_data.name,
                label=char_data.label,
                value=char_data.value
            )
            db.add(characteristic)
            db.flush()  # Получаем ID характеристики

            # Создаем связь с продуктом
            product_char = models.ProductCharacteristic(
                product_id=db_product.id,
                characteristic_id=characteristic.id
            )
            db.add(product_char)

    db.commit()
    db.refresh(db_product)
    return db_product


def create_product_with_characteristics(
        db: Session,
        product: schemas.ProductCreateForm,  # Измените тип здесь
        characteristics: List[dict],
        image_urls: List[str]
):
    """Создать продукт с характеристиками и изображениями"""
    # Создаем продукт
    db_product = models.Product(
        text=product.text,
        price=product.price,
        subcategory_id=product.subcategory_id,
        brand_id=product.brand_id,
        article=product.article,
        slug=product.slug,
        discount=product.discount,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # Добавляем изображения
    for image_url in image_urls:
        product_image = models.ProductImage(
            product_id=db_product.id,
            image_url=image_url
        )
        db.add(product_image)

    # Добавляем характеристики
    for char_data in characteristics:
        characteristic = models.CharacteristicItem(
            name=char_data['name'],
            label=char_data['label'],
            value=char_data['value']
        )
        db.add(characteristic)
        db.flush()

        product_char = models.ProductCharacteristic(
            product_id=db_product.id,
            characteristic_id=characteristic.id
        )
        db.add(product_char)

    db.commit()
    db.refresh(db_product)
    return db_product

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


def get_brands(db: Session, skip: int = 0, limit: int = 100) -> List[models.Brand]:
    return db.query(models.Brand).offset(skip).limit(limit).all()


def count_brands(db: Session) -> int:
    return db.query(models.Brand).count()


def get_brand_by_id(db: Session, brand_id: int) -> models.Brand:
    return db.query(models.Brand).filter(models.Brand.id == brand_id).first()


def count_products_by_brand(db: Session, brand_id: int):
    return db.query(func.count(models.Product.id)).filter(models.Product.brand_id == brand_id).scalar()


def generate_tag_value(name: str) -> str:
    try:
        transliterated = transliterate.translit(name, reversed=True)
    except:
        transliterated = name

    value = re.sub(r'[^a-zA-Z0-9]+', '_', transliterated).lower().strip('_')

    value = re.sub(r'_{2,}', '_', value)

    return value


def create_tag(db: Session, tag: schemas.TagCreate):
    if not tag.value:
        tag.value = generate_tag_value(tag.name)

    if db.query(models.Tag).filter(models.Tag.name == tag.name).first():
        raise ValueError("Tag with this name already exists")

    if db.query(models.Tag).filter(models.Tag.value == tag.value).first():

        counter = 1
        base_value = tag.value
        while db.query(models.Tag).filter(models.Tag.value == tag.value).first():
            tag.value = f"{base_value}_{counter}"
            counter += 1

    db_tag = models.Tag(**tag.dict())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


def get_tag_by_id(db: Session, tag_id: int):
    return db.query(models.Tag).filter(models.Tag.id == tag_id).first()


def get_tag_by_value(db: Session, value: str):
    return db.query(models.Tag).filter(models.Tag.value == value).first()


def get_all_tags(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Tag).offset(skip).limit(limit).all()


def get_products_by_tag_value(db: Session, tag_value: str, limit: int = 20):
    tag = db.query(models.Tag).filter(models.Tag.value == tag_value).first()
    if not tag:
        return None, 0

    products = (db.query(models.Product)
                .join(models.ProductTag)
                .filter(models.ProductTag.tag_id == tag.id)
                .order_by(models.Product.created_at.desc())
                .limit(limit)
                .all())

    total = (db.query(models.Product)
             .join(models.ProductTag)
             .filter(models.ProductTag.tag_id == tag.id)
             .count())

    return tag, products, total


def get_products_by_tag_id(db: Session, tag_id: int, limit: int = 20):
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        return None, 0, 0

    products = (db.query(models.Product)
                .join(models.ProductTag)
                .filter(models.ProductTag.tag_id == tag_id)
                .order_by(models.Product.created_at.desc())
                .limit(limit)
                .all())

    total = (db.query(models.Product)
             .join(models.ProductTag)
             .filter(models.ProductTag.tag_id == tag_id)
             .count())

    return tag, products, total


def update_tag(db: Session, tag_id: int, tag_data: schemas.TagUpdate):
    db_tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not db_tag:
        return None

    update_data = tag_data.dict(exclude_unset=True)

    if 'name' in update_data and not update_data.get('value'):
        update_data['value'] = generate_tag_value(update_data['name'])

    for field, value in update_data.items():
        setattr(db_tag, field, value)

    db.commit()
    db.refresh(db_tag)
    return db_tag


def delete_tag(db: Session, tag_id: int):
    db_tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if db_tag:
        db.query(models.ProductTag).filter(models.ProductTag.tag_id == tag_id).delete()
        db.delete(db_tag)
        db.commit()
    return db_tag


def add_tags_to_product(db: Session, product_id: int, tag_ids: List[int]):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return None

    tags = db.query(models.Tag).filter(models.Tag.id.in_(tag_ids)).all()

    for tag in tags:

        existing_link = db.query(models.ProductTag).filter(
            models.ProductTag.product_id == product_id,
            models.ProductTag.tag_id == tag.id
        ).first()

        if not existing_link:
            product_tag = models.ProductTag(product_id=product_id, tag_id=tag.id)
            db.add(product_tag)

    db.commit()
    db.refresh(product)
    return product


def remove_tags_from_product(db: Session, product_id: int, tag_ids: List[int]):
    db.query(models.ProductTag).filter(
        models.ProductTag.product_id == product_id,
        models.ProductTag.tag_id.in_(tag_ids)
    ).delete()

    db.commit()

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    db.refresh(product)
    return product


def set_product_tags(db: Session, product_id: int, tag_ids: List[int]):
    db.query(models.ProductTag).filter(
        models.ProductTag.product_id == product_id
    ).delete()

    product = add_tags_to_product(db, product_id, tag_ids)
    return product


def get_tags_count(db: Session) -> int:
    return db.query(models.Tag).count()


def generate_slug(text: str) -> str:
    text = unidecode(text)

    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-_')
    return slug


def generate_slug_from_name(name: str) -> str:
    try:

        transliterated = transliterate.translit(name, reversed=True)
    except:
        transliterated = name

    slug = re.sub(r'[^a-zA-Z0-9]+', '-', transliterated).lower().strip('-')

    slug = re.sub(r'-{2,}', '-', slug)

    return slug


def get_filter(db: Session, filter_id: int):
    return db.query(models.Filter).filter(models.Filter.id == filter_id).first()


def get_filter_by_value(db: Session, value: str):
    return db.query(models.Filter).filter(models.Filter.value == value).first()


def get_filters(db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None):
    query = db.query(models.Filter)
    if is_active is not None:
        query = query.filter(models.Filter.is_active == is_active)
    return query.offset(skip).limit(limit).all()


def create_filter(db: Session, filter_data: schemas.FilterCreate):
    db_filter = models.Filter(
        label=filter_data.label,
        value=filter_data.value,
        slug=filter_data.slug,
        order_index=filter_data.order_index,
        is_active=filter_data.is_active
    )
    db.add(db_filter)
    db.commit()
    db.refresh(db_filter)

    for item_data in filter_data.items:
        db_item = models.FilterItem(
            filter_id=db_filter.id,
            value=item_data.value,
            label=item_data.label,
            color=item_data.color,
            order_index=item_data.order_index,
            is_active=item_data.is_active
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_filter)
    return db_filter


def update_filter(db: Session, filter_id: int, filter_data: schemas.FilterUpdate):
    db_filter = db.query(models.Filter).filter(models.Filter.id == filter_id).first()
    if db_filter:
        update_data = filter_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_filter, field, value)
        db.commit()
        db.refresh(db_filter)
    return db_filter


def delete_filter(db: Session, filter_id: int):
    db_filter = db.query(models.Filter).filter(models.Filter.id == filter_id).first()
    if db_filter:
        db.delete(db_filter)
        db.commit()
    return db_filter


def create_filter_item(db: Session, item_data: schemas.FilterItemCreate, filter_id: int):
    db_item = models.FilterItem(**item_data.dict(), filter_id=filter_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
