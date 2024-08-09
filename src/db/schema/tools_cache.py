from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ToolsCacheBase(BaseModel):
    key: str
    value: str
    created_at: datetime = datetime.now()
    expires_at: datetime | None = None


class ToolsCacheSave(ToolsCacheBase):
    pass


class ToolsCache(ToolsCacheBase):
    model_config = ConfigDict(from_attributes = True)
