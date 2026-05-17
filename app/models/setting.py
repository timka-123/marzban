from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SettingUpdate(BaseModel):
    value: Any


class SettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: Any
    updated_at: datetime
