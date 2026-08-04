import enum

from pydantic import BaseModel, ConfigDict, field_validator


class SettingCategory(str, enum.Enum):
    API_KEY = "api_key"
    DATASHAPE = "datashape"
    GENERAL = "general"


class SettingValueType(str, enum.Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


class SettingDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    category: SettingCategory
    service_type: str = ""
    value_type: SettingValueType | None = None
    required: bool = True

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not value or not value.replace("_", "").isalnum() or not value[0].isalpha():
            raise ValueError("setting name must start with a letter and contain only letters, numbers, and underscores")
        return value
