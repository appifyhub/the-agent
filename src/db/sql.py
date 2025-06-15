import time
from contextlib import contextmanager
from typing import Generator

from requests import Session
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from db.model.base import BaseModel
from util.config import config
from util.safe_printer_mixin import sprint

engine: Engine
LocalSession: sessionmaker


def initialize_db(db_url: str = config.db_url, multi_connection_setup: bool = True) -> tuple[Engine, sessionmaker]:
    global engine, LocalSession
    engine = __create_db_engine(db_url, multi_connection_setup = multi_connection_setup)
    # noinspection PyPep8Naming
    LocalSession = sessionmaker(autocommit = False, autoflush = False, bind = engine)
    BaseModel.metadata.create_all(bind = engine)
    return engine, LocalSession


def __create_db_engine(
    db_url: str,
    max_retries: int = 7,
    retry_interval_s: int = 5,
    multi_connection_setup: bool = True,
) -> Engine:
    retries = 0
    while retries < max_retries:
        try:
            if multi_connection_setup:
                created_engine = create_engine(
                    url = db_url,          # where the DB is at
                    pool_pre_ping = True,  # check connections before using them
                    pool_recycle = 300,    # recycle connections after 5 minutes
                    pool_size = 3,         # start with a modest pool size
                    max_overflow = 10,     # allow more connections as requirements grow
                    pool_timeout = 10,     # wait for a few seconds for available connections
                )
            else:
                created_engine = create_engine(db_url)
            with created_engine.connect():
                sprint("Database connected")
                return created_engine
        except OperationalError:
            retries += 1
            message = f"Database connection attempt {retries} failed. Retrying in {retry_interval_s} seconds..."
            print(message)
            sprint(message)
            time.sleep(retry_interval_s)
    raise Exception("Failed to connect to the database after multiple attempts")


# noinspection PyPep8Naming,PyShadowingNames
def get_session() -> Generator[Session, None, None]:
    db = LocalSession()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_detached_session() -> Generator[Session, None, None]:
    session_generator = get_session()
    db = next(session_generator)
    try:
        yield db
    finally:
        session_generator.close()
