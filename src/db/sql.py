from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from util.config import config

# type hinting is risky here because the function calls return class objects
engine = create_engine(config.db_url)
LocalSession = sessionmaker(autocommit = False, autoflush = False, bind = engine)
BaseModel = declarative_base()
BaseModel.metadata.create_all(bind = engine)


# database is enabled, let's enable fetch
def get_session() -> Session:
    db = LocalSession()
    try:
        yield db
    finally:
        db.close()
