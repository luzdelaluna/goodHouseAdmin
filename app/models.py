from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table, Text, Enum as SQLEnum, DateTime, \
    UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

product_similar = Table(
    'product_similar',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id')),
    Column('similar_product_id', Integer, ForeignKey('products.id'))
)


class Filter(Base):
    __tablename__ = "filters"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(255), nullable=False)
    value = Column(String(100), unique=True, index=True, nullable=False)
    slug = Column(String(100), unique=True, index=True)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("FilterItem", back_populates="filter", cascade="all, delete-orphan")


class FilterItem(Base):
    __tablename__ = "filter_items"

    id = Column(Integer, primary_key=True, index=True)
    filter_id = Column(Integer, ForeignKey("filters.id"))
    value = Column(String(100), nullable=False)
    label = Column(String(255), nullable=False)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    filter = relationship("Filter", back_populates="items")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String, nullable=True)
    text = Column(String, index=True)
    slug = Column(String, unique=True, index=True)

    subcategories = relationship("Subcategory", back_populates="category")


class Subcategory(Base):
    __tablename__ = "subcategories"

    id = Column(Integer, primary_key=True, index=True)
    image = Column(String)
    text = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)

    category = relationship("Category", back_populates="subcategories")
    brand = relationship("Brand", back_populates="subcategories")
    products = relationship("Product", back_populates="subcategory")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    value = Column(String, unique=True, index=True)

    products = relationship("Product", secondary="product_tags", back_populates="tags")


class ProductTag(Base):
    __tablename__ = "product_tags"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    tag_id = Column(Integer, ForeignKey("tags.id"))

    __table_args__ = (UniqueConstraint('product_id', 'tag_id', name='_product_tag_uc'),)


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    image = Column(String)
    name = Column(String, index=True)

    subcategories = relationship("Subcategory", back_populates="brand")
    products = relationship("Product", back_populates="brand")


class CharacteristicTemplate(Base):
    __tablename__ = "characteristic_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    characteristics = relationship("CharacteristicItem", back_populates="template", cascade="all, delete-orphan")


class CharacteristicItem(Base):
    __tablename__ = "characteristic_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    label = Column(String, nullable=False)
    value = Column(String, nullable=False)

    template_id = Column(Integer, ForeignKey("characteristic_templates.id", ondelete="CASCADE"))
    template = relationship("CharacteristicTemplate", back_populates="characteristics")

    products = relationship("ProductCharacteristic", back_populates="characteristic")

class ProductCharacteristic(Base):
    __tablename__ = "product_characteristics"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    characteristic_id = Column(Integer, ForeignKey("characteristic_items.id", ondelete="CASCADE"))

    product = relationship("Product", back_populates="characteristics_assoc")
    characteristic = relationship("CharacteristicItem", back_populates="products")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    article = Column(Integer, unique=True, index=True)
    price = Column(Float)
    discount = Column(Float, default=0)
    slug = Column(String, unique=True, index=True)
    image = Column(String, nullable=True)
    in_stock = Column(Boolean, default=True)
    small_description = Column(Text, nullable=True)
    full_description = Column(Text, nullable=True)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"))
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)

    subcategory = relationship("Subcategory", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    tags = relationship("Tag", secondary="product_tags", back_populates="products")
    similar_products = relationship(
        "Product",
        secondary=product_similar,
        primaryjoin=id == product_similar.c.product_id,
        secondaryjoin=id == product_similar.c.similar_product_id,
        backref="similar_to"
    )
    warehouses = relationship("ProductWarehouse", back_populates="product")
    documents = relationship("Document", back_populates="product")
    images = relationship("ProductImage", back_populates="product")
    additional_products = relationship("AdditionalProduct", back_populates="product")
    characteristics_assoc = relationship("ProductCharacteristic", back_populates="product",
                                         cascade="all, delete-orphan")

    @property
    def image_urls(self):
        return [img.image_url for img in self.images] if self.images else []

    @property
    def characteristics(self):
        return [
            {
                "name": assoc.characteristic.name,
                "label": assoc.characteristic.label,
                "value": assoc.characteristic.value
            }
            for assoc in self.characteristics_assoc
        ]


class ProductWarehouse(Base):
    __tablename__ = "product_warehouses"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="warehouses")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    file_url = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="documents")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    image_url = Column(String)

    product = relationship("Product", back_populates="images")


class AdditionalProduct(Base):
    __tablename__ = "additional_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    value = Column(String)
    product_slug = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="additional_products")


class UserRole(str, enum.Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(SQLEnum(UserRole), default=UserRole.ADMIN)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_users = relationship("User", remote_side=[id], backref="creator")
    refresh_tokens = relationship("RefreshToken", back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime(timezone=True))
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="refresh_tokens")
