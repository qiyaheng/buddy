"""模型服务商 / 模型配置 / 连接测试路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.provider import (
    ModelConfigIn,
    ModelConfigOut,
    ModelConfigUpdate,
    ProviderCreate,
    ProviderOut,
    ProviderUpdate,
    TestConnectionRequest,
    TestConnectionResultOut,
)
from ..services import provider_service

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderOut])
def list_providers(db: Session = Depends(get_db)) -> list[ProviderOut]:
    return [provider_service.to_provider_out(p) for p in provider_service.list_providers(db)]


@router.post("", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
def create_provider(
    data: ProviderCreate, db: Session = Depends(get_db)
) -> ProviderOut:
    return provider_service.to_provider_out(provider_service.create_provider(db, data))


@router.patch("/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: str, data: ProviderUpdate, db: Session = Depends(get_db)
) -> ProviderOut:
    return provider_service.to_provider_out(
        provider_service.update_provider(db, provider_id, data)
    )


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: str, db: Session = Depends(get_db)) -> None:
    provider_service.delete_provider(db, provider_id)


@router.post("/{provider_id}/test", response_model=TestConnectionResultOut)
def test_provider(
    provider_id: str,
    data: TestConnectionRequest | None = None,
    db: Session = Depends(get_db),
) -> TestConnectionResultOut:
    return provider_service.run_connection_test(db, provider_id, data.model_id if data else None)


@router.post(
    "/{provider_id}/models",
    response_model=ModelConfigOut,
    status_code=status.HTTP_201_CREATED,
)
def add_model(
    provider_id: str, data: ModelConfigIn, db: Session = Depends(get_db)
) -> ModelConfigOut:
    return provider_service.add_model(db, provider_id, data)  # type: ignore[return-value]


@router.patch("/models/{model_id}", response_model=ModelConfigOut)
def update_model(
    model_id: str, data: ModelConfigUpdate, db: Session = Depends(get_db)
) -> ModelConfigOut:
    return provider_service.update_model(db, model_id, data)  # type: ignore[return-value]


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: str, db: Session = Depends(get_db)) -> None:
    provider_service.delete_model(db, model_id)
