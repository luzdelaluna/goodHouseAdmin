from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def create_initial_superuser(db: Session):
    from . import crud, schemas

    superuser_email = os.getenv('superuser_email')
    superuser_username = os.getenv('superuser_username')
    superuser_password = os.getenv('superuser_password')

    existing_superuser = crud.get_user_by_email(db, superuser_email) or crud.get_user_by_username(db,
                                                                                                  superuser_username)
    if not existing_superuser:
        superuser_data = schemas.UserCreateManual(
            email=superuser_email,
            username=superuser_username,
            password=superuser_password,
            role=schemas.UserRole.SUPERUSER
        )
        crud.create_user_manual(db, superuser_data)
        print("✅ Superuser created successfully")
        print(f"📧 Login: {superuser_username}")
        print(f"🔑 Password: {superuser_password}")
    else:
        print("✅ Superuser already exists")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✅ Подключение к БД успешно: {DATABASE_URL}")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
