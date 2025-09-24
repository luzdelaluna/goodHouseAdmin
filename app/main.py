from fastapi import FastAPI, Request
from . import database
from .routers import categories, subcategories, products, brands, filters, upload
import os
from dotenv import load_dotenv
import logging
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Product Catalog API", version="1.0.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    else:

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


@app.on_event("startup")
def startup_event():
    database.check_database()


app.include_router(categories.router)
app.include_router(subcategories.router)
app.include_router(products.router)
app.include_router(brands.router)
app.include_router(filters.router)
app.include_router(upload.router)


@app.get("/")
def read_root():
    return {
        "message": "Product Catalog API",
        "storage": "TimeWeb S3",
        "bucket": os.getenv('AWS_S3_BUCKET_NAME')
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
