from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional
from .. import crud, schemas, database
from ..s3_service import s3_service
from ..dependencies import require_admin

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=schemas.Category)
async def create_category_with_upload(
        text: str = Form(...),
        slug: Optional[str] = Form(None),
        icon: UploadFile = File(...),
        db: Session = Depends(database.get_db),
        _: dict = Depends(require_admin)
):
    icon_url = None
    if icon:
        icon_url = await s3_service.upload_file(icon, "icons")

    final_slug = slug
    if slug is None:
        from slugify import slugify
        final_slug = slugify(text, lowercase=True, word_boundary=True)

    category_data = {
        "text": text,
        "slug": final_slug,
        "icon": icon_url
    }

    return crud.create_category(db=db, category=schemas.CategoryCreate(**category_data))


@router.get("/", response_model=schemas.CategoryPaginatedResponse)
def read_categories(
        page: int = Query(1, ge=1, description="Номер страницы"),
        limit: int = Query(10, ge=1, le=100, description="Количество записей на странице (1-100)"),
        db: Session = Depends(database.get_db)
):
    try:

        skip = (page - 1) * limit

        categories = crud.get_categories(db, skip=skip, limit=limit)

        total_count = crud.get_categories_count(db)

        total_pages = (total_count + limit - 1) // limit

        return {
            "data": categories,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "limit": limit,
                "total_items": total_count
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении категорий: {str(e)}")


@router.get("/{category_id}", response_model=schemas.Category)
def read_category(category_id: int, db: Session = Depends(database.get_db)):
    try:
        category = crud.get_category_by_id(db, category_id=category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except HTTPException as e:
        raise e


@router.get("/slug/{slug}", response_model=schemas.Category)
def read_category_by_slug(slug: str, db: Session = Depends(database.get_db)):
    try:
        category = crud.get_category_by_slug(db, slug=slug)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except HTTPException as e:
        raise e


@router.patch("/{category_id}", response_model=schemas.Category)
async def update_category(
        category_id: int,
        icon: Optional[UploadFile] = File(None),
        text: Optional[str] = Form(None),
        slug: Optional[str] = Form(None),
        db: Session = Depends(database.get_db),
        _: dict = Depends(require_admin)
):
    try:
        db_category = crud.get_category_by_id(db, category_id=category_id)
        if db_category is None:
            raise HTTPException(status_code=404, detail="Category not found")

        update_data = {}
        old_icon_url = None
        new_icon_url = None

        if icon is not None:
            if icon.filename:

                new_icon_url = await s3_service.upload_file(icon, "icons")
                update_data["icon"] = new_icon_url

                old_icon_url = db_category.icon
            else:
                update_data["icon"] = None
                old_icon_url = db_category.icon

        if text is not None:
            update_data["text"] = text

        if slug is not None:
            update_data["slug"] = slug

        if text is not None and text != db_category.text and slug is None:
            from slugify import slugify
            update_data["slug"] = slugify(text, lowercase=True, word_boundary=True)

        if update_data:
            updated_category = crud.update_category(
                db=db,
                category_id=category_id,
                category_update=schemas.CategoryUpdate(**update_data)
            )

            if old_icon_url:
                try:
                    await s3_service.delete_file(old_icon_url)
                except Exception as delete_error:
                    print(f"Warning: Could not delete old icon {old_icon_url}: {delete_error}")

            return updated_category
        else:
            return db_category


    except HTTPException as e:

        if 'new_icon_url' in locals() and new_icon_url:
            try:
                await s3_service.delete_file(new_icon_url)
            except:
                pass

        raise e

    except Exception as e:
        if 'new_icon_url' in locals() and new_icon_url:
            try:
                await s3_service.delete_file(new_icon_url)
            except:
                pass

        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{category_id}")
def delete_category(
        category_id: int,
        db: Session = Depends(database.get_db),
        _: dict = Depends(require_admin)
):
    try:
        category = crud.get_category_by_id(db, category_id=category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")

        if category.icon:
            s3_service.delete_file(category.icon)

        return crud.delete_category(db=db, category_id=category_id)
    except HTTPException as e:
        raise e
