from fastapi import FastAPI
from . import database
from .routers import categories, subcategories, products, brands, filters, upload
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Product Catalog API", version="1.0.0")


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
