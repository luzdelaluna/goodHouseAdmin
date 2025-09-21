from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
from ..s3_service import s3_service
from dotenv import load_dotenv


load_dotenv()

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/icon")
async def upload_icon(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    if file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB")

    file_url = await s3_service.upload_file(file, "icons")
    return JSONResponse(content={
        "url": file_url,
        "message": "Icon uploaded successfully to TimeWeb S3"
    })


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB")

    file_url = await s3_service.upload_file(file, "images")
    return JSONResponse(content={
        "url": file_url,
        "message": "Image uploaded successfully to TimeWeb S3"
    })


@router.post("/product-image")
async def upload_product_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB")

    file_url = await s3_service.upload_file(file, "products")
    return JSONResponse(content={
        "url": file_url,
        "message": "Product image uploaded successfully to TimeWeb S3"
    })


@router.delete("/file")
async def delete_file(file_url: str):
    success = await s3_service.delete_file(file_url)
    return JSONResponse(content={
        "deleted": success,
        "url": file_url,
        "message": "File deleted from TimeWeb S3" if success else "File not found or error deleting"
    })


@router.get("/test-connection")
async def test_s3_connection():
    try:
        files = await s3_service.list_files()
        return JSONResponse(content={
            "connected": True,
            "bucket": os.getenv('AWS_S3_BUCKET_NAME'),
            "endpoint": os.getenv('AWS_S3_ENDPOINT_URL'),
            "file_count": len(files),
            "message": "Successfully connected to TimeWeb S3"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")
