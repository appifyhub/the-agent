import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.crud.user import User as UserCRUD
from db.sql import BaseModel


@pytest.fixture(scope = "function")
def get_test_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    # noinspection PyPep8Naming
    TestLocalSession = sessionmaker(autocommit = False, autoflush = False, bind = engine)
    BaseModel.metadata.create_all(bind = engine)
    db = TestLocalSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope = "function")
def user_crud(test_session) -> UserCRUD:
    return UserCRUD(test_session)
