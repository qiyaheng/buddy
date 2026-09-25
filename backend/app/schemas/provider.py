"""模型服务商与模型配置的接口契约。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ModelConfigIn(BaseModel):
    model_id: str = Field(min_length=1, max_length=120, description="上游真实模型 ID")
    display_name: str = Field(min_length=1, max_length=120)
    capabilities: list[str] = Field(default_factory=list)
    is_default: bool = False


class ModelConfigUpdate(BaseModel):
    model_id: str | None = Field(default=None, min_length=1, max_length=120)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    capabilities: list[str] | None = None
    is_default: bool | None = None


class ModelConfigOut(ModelConfigIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    sort_order: int


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    base_url: HttpUrl
    api_key: str | None = Field(default=None, max_length=300)
    timeout_seconds: int = Field(default=60, ge=5, le=600)
    enabled: bool = True
    models: list[ModelConfigIn] = Field(default_factory=list)


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    base_url: HttpUrl | None = None
    # None 或空串 = 不修改；非空 = 更新密钥
    api_key: str | None = Field(default=None, max_length=300)
    timeout_seconds: int | None = Field(default=None, ge=5, le=600)
    enabled: bool | None = None


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    base_url: str
    timeout_seconds: int
    enabled: bool
    has_api_key: bool
    api_key_masked: str
    models: list[ModelConfigOut]
    created_at: datetime


class TestConnectionRequest(BaseModel):
    model_id: str | None = None


class TestConnectionResultOut(BaseModel):
    ok: bool
    code: str
    message: str = ""


class SetupStatusOut(BaseModel):
    has_models: bool
    default_provider_id: str | None = None
    default_model_id: str | None = None
    default_display_name: str | None = None
