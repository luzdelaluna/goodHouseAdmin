from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table, Text, ARRAY
from sqlalchemy.orm import relationship
from .database import Base

product_tags = Table(
    'product_tags',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

product_characteristics = Table(
    'product_characteristics',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id')),
    Column('characteristic_id', Integer, ForeignKey('characteristics.id'))
)

product_similar = Table(
    'product_similar',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id')),
    Column('similar_product_id', Integer, ForeignKey('products.id'))
)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String, nullable=True)
    text = Column(String, index=True)
    slug = Column(String, unique=True, index=True)

    subcategories = relationship("Subcategory", back_populates="category")
    filters = relationship("Filter", back_populates="category")


class Filter(Base):
    __tablename__ = "filters"

    id = Column(Integer, primary_key=True, index=True)
    image = Column(String, nullable=True)
    text = Column(String, index=True)
    status = Column(Boolean, default=True)
    category_id = Column(Integer, ForeignKey("categories.id"))

    category = relationship("Category", back_populates="filters")


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

    products = relationship("Product", secondary=product_tags, back_populates="tags")


class CharacteristicTemplate(Base):
    __tablename__ = "characteristic_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    characteristics = relationship("Characteristic", back_populates="template")


class Characteristic(Base):
    __tablename__ = "characteristics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    value = Column(String)
    template_id = Column(Integer, ForeignKey("characteristic_templates.id"), nullable=True)

    template = relationship("CharacteristicTemplate", back_populates="characteristics")
    products = relationship("Product", secondary=product_characteristics, back_populates="characteristics")


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    image = Column(String)
    name = Column(String, index=True)

    subcategories = relationship("Subcategory", back_populates="brand")
    products = relationship("Product", back_populates="brand")


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
    brand_id = Column(Integer, ForeignKey("brands.id"))

    subcategory = relationship("Subcategory", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    tags = relationship("Tag", secondary=product_tags, back_populates="products")
    characteristics = relationship("Characteristic", secondary=product_characteristics, back_populates="products")
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
    image_url = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="images")


class AdditionalProduct(Base):
    __tablename__ = "additional_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    value = Column(String)
    product_slug = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="additional_products")
