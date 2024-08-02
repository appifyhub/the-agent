import time

from sqlalchemy import create_engine, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from util.config import config


def create_db_engine(max_retries: int = 7, retry_interval_s: int = 5) -> Engine:
    retries = 0
    while retries < max_retries:
        try:
            # create and test connection
            created_engine = create_engine(config.db_url)
            with created_engine.connect():
                return created_engine
        except OperationalError:
            retries += 1
            print(f"Database connection attempt {retries} failed. Retrying in {retry_interval_s} seconds...")
            time.sleep(retry_interval_s)

    raise Exception("Failed to connect to the database after multiple attempts")


engine = create_db_engine()
LocalSession = sessionmaker(autocommit = False, autoflush = False, bind = engine)
BaseModel = declarative_base()
BaseModel.metadata.create_all(bind = engine)


def get_session() -> Session:
    db = LocalSession()
    try:
        yield db
    finally:
        db.close()
