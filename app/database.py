from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
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
