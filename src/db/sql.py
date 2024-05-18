from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from util.config import instance as config

engine: Engine = create_engine(config.db_url)

# type hinting is risky here because the function calls return class objects
LocalSession = sessionmaker(autoflush = False, bind = engine)
BaseModel = declarative_base()
