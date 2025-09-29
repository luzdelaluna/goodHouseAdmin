from pydantic import BaseModel, field_validator, model_validator, Field, EmailStr, validator, ConfigDict
from typing import List, Optional
import re
from slugify import slugify
import enum
from datetime import datetime


class UserRole(str, enum.Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None


class UserCreateManual(UserBase):
    password: str
    role: UserRole = UserRole.ADMIN

    @validator('email', pre=True, always=True)
    def validate_email_or_username(cls, v, values):
        if not v and not values.get('username'):
            raise ValueError('Either email or username must be provided')
        return v


class UserCreateAuto(BaseModel):
    role: UserRole = UserRole.ADMIN


class UserLogin(BaseModel):
    login: str
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

    @validator('email')
    def validate_email_unique(cls, v):
        if v:
            return v
        return v


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    generated_password: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_role: UserRole
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_id: int
    role: UserRole

class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    size: int
    pages: int

class PaginationInfo(BaseModel):
    current_page: int
    total_pages: int
    limit: int
    total_items: Optional[int] = None


class CategoryPaginatedResponse(BaseModel):
    data: List['Category']
    pagination: Optional[PaginationInfo] = None


class SubcategoryPaginatedResponse(BaseModel):
    data: List['Subcategory']
    pagination: Optional[PaginationInfo] = None

class TagBase(BaseModel):
    name: str
    value: Optional[str] = None


class TagResponse(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TagPaginatedResponse(BaseModel):
    data: List[TagResponse]
    pagination: PaginationInfo

    model_config = ConfigDict(from_attributes=True)


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None
    color: Optional[str] = None


class CharacteristicItemBase(BaseModel):
    name: str
    value: str
    order_index: int = 0
    is_active: bool = True


class CharacteristicItemCreate(CharacteristicItemBase):
    pass


class CharacteristicItem(CharacteristicItemBase):
    id: int
    characteristic_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CharacteristicBase(BaseModel):
    name: str
    value: str
    slug: Optional[str] = None
    order_index: int = 0
    is_active: bool = True


class CharacteristicCreate(CharacteristicBase):
    items: List[CharacteristicItemCreate] = []


class CharacteristicUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None
    slug: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class Characteristic(CharacteristicBase):
    id: int
    items: List[CharacteristicItem] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CharacteristicPaginatedResponse(BaseModel):
    items: List['Characteristic']
    total: int
    page: int
    size: int
    pages: int


class FilterItemBase(BaseModel):
    value: str
    label: str
    color: Optional[str] = None
    order_index: int = 0
    is_active: bool = True


class FilterItemCreate(FilterItemBase):
    pass


class FilterItem(FilterItemBase):
    id: int
    filter_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FilterBase(BaseModel):
    label: str
    value: str
    slug: str
    order_index: int = 0
    is_active: bool = True


class FilterCreate(FilterBase):
    items: List[FilterItemCreate] = []


class FilterUpdate(BaseModel):
    label: Optional[str] = None
    value: Optional[str] = None
    slug: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class Filter(FilterBase):
    id: int
    items: List[FilterItem] = []
    created_at: datetime
    updated_at: datetime

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
    category_name: str

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def set_category_name(cls, values):
        if hasattr(values, 'category') and values.category:
            # Берем поле 'text' из связанной категории
            values.category_name = values.category.text
        else:
            values.category_name = ""
        return values


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
    tag_ids: Optional[List[int]] = []

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
    class ProductCreate(ProductBase):
        characteristics: List[CharacteristicCreate] = []

    def generate_slugs(self):

        from slugify import slugify
        import datetime
        import random

        if self.slug is None:
            self.slug = slugify(self.text, lowercase=True, word_boundary=True)

        if self.article is None:
            timestamp = int(datetime.datetime.now().timestamp()) % 100000
            random_part = random.randint(100, 999)
            self.article = timestamp * 1000 + random_part

            self.article %= 100000000

    def __init__(self, **data):
        super().__init__(**data)
        self.generate_slugs()


class Product(ProductBase):
    id: int
    in_stock: bool = True
    small_description: Optional[str] = None
    full_description: Optional[str] = None
    tags: List['TagResponse'] = []
    characteristics: List[CharacteristicBase] = []
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
    characteristics: List[dict] = []
    tags: List['TagResponse'] = []

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


class ProductsByTagResponse(BaseModel):
    tag: TagResponse
    products: List[ProductResponse]
    total: int


class ProductDetail(Product):
    warehouses: List[str] = []
    documents: List[dict] = []
    images: List[str] = []
    similar_products: List[Product] = []
    additional_products: List[dict] = []



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
