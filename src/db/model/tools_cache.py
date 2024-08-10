from sqlalchemy import Column, String, Text, DateTime

from db.sql import BaseModel


class ToolsCacheDB(BaseModel):
    __tablename__ = "tools_cache"

    key = Column(String, primary_key = True)
    value = Column(Text, nullable = False)
    created_at = Column(DateTime, nullable = False)
    expires_at = Column(DateTime, nullable = True)
