from pydantic import BaseModel, field_validator, model_validator, Field
from typing import List, Optional, Generic, TypeVar
import re
from slugify import slugify

class PaginationInfo(BaseModel):
    current_page: int
    total_pages: int
    limit: int
    total_items: Optional[int] = None


class CategoryPaginatedResponse(BaseModel):
    data: List['Category']
    pagination: PaginationInfo


class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    id: int

    class Config:
        from_attributes = True


class CharacteristicBase(BaseModel):
    name: str
    value: str
    template_id: Optional[int] = None


class CharacteristicCreate(CharacteristicBase):
    pass


class Characteristic(CharacteristicBase):
    id: int

    class Config:
        from_attributes = True


class FilterBase(BaseModel):
    image: Optional[str] = None
    text: str
    status: bool = True

    @field_validator('image')
    def validate_image_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Image must be a valid URL or None')
        return v


class FilterCreate(FilterBase):
    category_id: int


class Filter(FilterBase):
    id: int
    category_id: int

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    icon: Optional[str] = None
    text: str
    slug: str = None

    @field_validator('slug')
    def validate_slug_format(cls, v):
        if v is None or v == '':
            return None

        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug может содержать только латинские буквы, цифры и тире')
        if '--' in v or v.startswith('-') or v.endswith('-'):
            raise ValueError('Slug не может содержать двойные тире или тире в начале/конце')
        return v

    @model_validator(mode='after')
    def generate_slug_if_missing(self):
        if self.slug is None:
            self.slug = slugify(self.text, lowercase=True, word_boundary=True)
        return self


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int
    slug: str
    filters: List[Filter] = []

    class Config:
        from_attributes = True


class CategoryUpdate(BaseModel):
    icon: Optional[str] = None
    text: Optional[str] = None
    slug: Optional[str] = None

    @field_validator('slug')
    @classmethod
    def validate_slug_format(cls, v):
        if v is not None:
            if not all(c.isalnum() or c == '-' for c in v):
                raise ValueError('Slug может содержать только буквы, цифры и тире')
            if v.startswith('-') or v.endswith('-') or '--' in v:
                raise ValueError('Slug не может начинаться/заканчиваться тире или содержать двойные тире')
        return v

    def generate_slug(self, current_text: str, new_text: Optional[str] = None):

        if self.slug is not None:

            return self.slug

        elif new_text is not None and new_text != current_text:

            return slugify(new_text, lowercase=True, word_boundary=True)

        else:

            return None


class BrandBase(BaseModel):
    image: str
    name: str


class BrandCreate(BrandBase):
    pass


class Brand(BrandBase):
    id: int

    class Config:
        from_attributes = True


class SubcategoryBase(BaseModel):
    image: str
    text: str
    slug: Optional[str] = None,

    @field_validator('slug')
    def validate_slug_format(cls, v):
        if v is not None:
            if not re.match(r'^[a-z0-9-]+$', v):
                raise ValueError('Slug может содержать только латинские буквы, цифры и тире')
            if '--' in v or v.startswith('-') or v.endswith('-'):
                raise ValueError('Slug не может содержать двойные тире или тире в начале/конце')
        return v

    @model_validator(mode='after')
    def generate_slug_if_missing(self):
        if self.slug is None:
            self.slug = slugify(self.text, lowercase=True, word_boundary=True)
        return self


class SubcategoryCreate(SubcategoryBase):
    category_id: int
    brand_id: Optional[int] = None


class Subcategory(SubcategoryBase):
    id: int
    category_id: Optional[int] = None
    brand_id: Optional[int]

    class Config:
        from_attributes = True


class SubcategoryUpdate(BaseModel):
    image: Optional[str] = None
    text: Optional[str] = None
    slug: Optional[str] = None
    category_id: Optional[str] = None
    brand_id: Optional[str] = None

    @field_validator('slug')
    @classmethod
    def validate_slug_format(cls, v):
        if v is not None:
            if not all(c.isalnum() or c == '-' for c in v):
                raise ValueError('Slug может содержать только буквы, цифры и тире')
            if v.startswith('-') or v.endswith('-') or '--' in v:
                raise ValueError('Slug не может начинаться/заканчиваться тире или содержать двойные тире')
        return v

    def generate_slug(self, current_text: str, new_text: Optional[str] = None):
        if self.slug is not None:
            return self.slug
        elif new_text is not None and new_text != current_text:
            return slugify(new_text, lowercase=True, word_boundary=True)
        else:
            return None


class ProductBase(BaseModel):
    images: List[str]
    text: str
    article: Optional[int] = Field(default=None, description="Автогенерация, если не указан")
    price: float
    discount: float = 0
    slug: Optional[str] = Field(default=None, description="Автогенерация, если не указан")
    subcategory_id: int
    brand_id: Optional[int] = None

    @field_validator('slug')
    @classmethod
    def validate_slug_format(cls, v):
        if v is not None:
            if not re.match(r'^[a-z0-9-]+$', v):
                raise ValueError('Slug может содержать только латинские буквы, цифры и тире')
            if '--' in v or v.startswith('-') or v.endswith('-'):
                raise ValueError('Slug не может содержать двойные тире или тире в начале/конце')
        return v

    @field_validator('article')
    @classmethod
    def validate_article_format(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Артикул должен быть положительным числом')
        return v

    @model_validator(mode='after')
    def validate_images_count(self):

        if len(self.images) < 1:
            raise ValueError('Должно быть как минимум 1 изображение')
        if len(self.images) > 15:
            raise ValueError('Не более 15 изображений')
        return self


class ProductCreate(ProductBase):
    def generate_slugs(self):

        from slugify import slugify
        import uuid
        import datetime

        if self.slug is None:
            self.slug = slugify(self.text, lowercase=True, word_boundary=True)

        if self.article is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d")
            unique_id = str(uuid.uuid4())[:8].upper()
            self.article = f"PRD-{timestamp}-{unique_id}"

    def __init__(self, **data):
        super().__init__(**data)
        self.generate_slugs()


class Product(ProductBase):
    id: int
    in_stock: bool = True
    small_description: Optional[str] = None
    full_description: Optional[str] = None
    tags: List[Tag] = []
    characteristics: List[Characteristic] = []
    images: List[dict] = []

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    text: str
    article: int
    price: float
    discount: float = 0
    slug: str
    in_stock: bool = True
    small_description: Optional[str] = None
    full_description: Optional[str] = None
    subcategory_id: int
    brand_id: Optional[int] = None
    images: List[str] = []

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    images: Optional[str] = None
    text: Optional[str] = None
    article: Optional[int] = None
    price: Optional[float] = None
    discount: Optional[float] = None
    slug: Optional[str] = None
    subcategory_id: Optional[int] = None
    brand_id: Optional[int] = None

    @field_validator('slug')
    @classmethod
    def validate_slug_format(cls, v):
        if v is not None:
            if not all(c.isalnum() or c == '-' for c in v):
                raise ValueError('Slug может содержать только буквы, цифры и тире')
            if v.startswith('-') or v.endswith('-') or '--' in v:
                raise ValueError('Slug не может начинаться/заканчиваться тире или содержать двойные тире')
        return v

    def generate_slug(self, current_text: str, new_text: Optional[str] = None):
        if self.slug is not None:
            return self.slug
        elif new_text is not None and new_text != current_text:
            return slugify(new_text, lowercase=True, word_boundary=True)
        else:
            return None

    @field_validator('article')
    @classmethod
    def validate_article_format(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Артикул должен быть положительным числом')
        return v


class ProductDetail(Product):
    warehouses: List[str] = []
    documents: List[dict] = []
    images: List[str] = []
    similar_products: List[Product] = []
    additional_products: List[dict] = []


class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    size: int
    pages: int


class ProductWarehouseBase(BaseModel):
    address: str


class DocumentBase(BaseModel):
    name: str
    file_url: str


class ProductImageBase(BaseModel):
    image_url: str


class AdditionalProductBase(BaseModel):
    name: str
    value: str
    product_slug: str
