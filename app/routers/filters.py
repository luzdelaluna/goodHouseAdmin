from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas, database
from ..models import Filter
from ..s3_service import s3_service

router = APIRouter(prefix="/filters", tags=["filters"])


@router.post("/", response_model=schemas.Filter)
async def create_filter_with_upload(
        text: str = Form(...),
        status: bool = Form(True),
        category_id: int = Form(...),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(database.get_db)
):
    image_url = None

    if image:
        image_url = await s3_service.upload_file(image, "filters")

    filter_data = {
        "text": text,
        "status": status,
        "category_id": category_id,
        "image": image_url
    }

    return crud.create_filter(db=db, filter=schemas.FilterCreate(**filter_data))


# @router.post("/", response_model=schemas.Filter)
# def create_filter(filter: schemas.FilterCreate, db: Session = Depends(database.get_db)):
#     if filter.image and not filter.image.startswith(('http://', 'https://')):
#         raise HTTPException(
#             status_code=400,
#             detail="Image must be a URL. First upload file via POST /upload/image or use /with-upload endpoint"
#         )
#     return crud.create_filter(db=db, filter=filter)


@router.get("/", response_model=List[schemas.Filter])
def read_filters(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    filters = crud.get_filters(db, skip=skip, limit=limit)
    return filters


@router.get("/{filter_id}", response_model=schemas.Filter)
def read_filter(filter_id: int, db: Session = Depends(database.get_db)):
    filter = crud.get_filter_by_id(db, filter_id=filter_id)
    if filter is None:
        raise HTTPException(status_code=404, detail="Filter not found")
    return filter


@router.put("/{filter_id}", response_model=schemas.Filter)
def update_filter(filter_id: int, filter: schemas.FilterCreate, db: Session = Depends(database.get_db)):
    return crud.update_filter(db=db, filter_id=filter_id, filter=filter)


@router.delete("/{filter_id}")
def delete_filter(filter_id: int, db: Session = Depends(database.get_db)):
    return crud.delete_filter(db=db, filter_id=filter_id)


@router.get("/category/{category_id}", response_model=List[schemas.Filter])
def read_filters_by_category(category_id: int, db: Session = Depends(database.get_db)):
    filters = db.query(Filter).filter(Filter.category_id == category_id).all()
    return filters
