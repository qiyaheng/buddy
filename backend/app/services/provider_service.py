"""模型服务商与模型配置的业务逻辑。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..agent.llm import test_connection
from ..errors import ConflictError, NotFoundError
from ..models import ModelConfig, Provider
from ..schemas.provider import (
    ModelConfigIn,
    ModelConfigUpdate,
    ProviderCreate,
    ProviderOut,
    ProviderUpdate,
    SetupStatusOut,
    TestConnectionResultOut,
)
from ..security import decrypt, encrypt, mask_secret


def to_provider_out(provider: Provider) -> ProviderOut:
    plaintext_key = decrypt(provider.encrypted_api_key)
    return ProviderOut(
        id=provider.id,
        name=provider.name,
        base_url=provider.base_url,
        timeout_seconds=provider.timeout_seconds,
        enabled=provider.enabled,
        has_api_key=bool(plaintext_key),
        api_key_masked=mask_secret(plaintext_key),
        models=[
            {
                "id": m.id,
                "provider_id": m.provider_id,
                "model_id": m.model_id,
                "display_name": m.display_name,
                "capabilities": m.capabilities,
                "is_default": m.is_default,
                "sort_order": m.sort_order,
            }
            for m in sorted(provider.models, key=lambda x: (x.sort_order, x.created_at))
        ],
        created_at=provider.created_at,
    )


def list_providers(db: Session) -> list[Provider]:
    return db.query(Provider).order_by(Provider.created_at).all()


def _get_or_404(db: Session, provider_id: str) -> Provider:
    provider = db.get(Provider, provider_id)
    if provider is None:
        raise NotFoundError("模型服务商不存在")
    return provider


def _set_single_default(db: Session, model: ModelConfig) -> None:
    """全局仅允许一个默认模型。"""
    if not model.is_default:
        return
    others = db.query(ModelConfig).filter(ModelConfig.id != model.id, ModelConfig.is_default.is_(True))
    for other in others:
        other.is_default = False


def create_provider(db: Session, data: ProviderCreate) -> Provider:
    provider = Provider(
        name=data.name,
        base_url=str(data.base_url),
        encrypted_api_key=encrypt(data.api_key) if data.api_key else None,
        timeout_seconds=data.timeout_seconds,
        enabled=data.enabled,
    )
    db.add(provider)
    db.flush()

    for index, item in enumerate(data.models):
        model = ModelConfig(
            provider_id=provider.id,
            model_id=item.model_id.strip(),
            display_name=item.display_name.strip(),
            capabilities=item.capabilities,
            is_default=item.is_default,
            sort_order=index * 10,
        )
        db.add(model)
        db.flush()
        _set_single_default(db, model)

    db.commit()
    db.refresh(provider)
    return provider


def update_provider(db: Session, provider_id: str, data: ProviderUpdate) -> Provider:
    provider = _get_or_404(db, provider_id)
    if data.name is not None:
        provider.name = data.name
    if data.base_url is not None:
        provider.base_url = str(data.base_url)
    if data.api_key:  # 空串/None 表示不修改
        provider.encrypted_api_key = encrypt(data.api_key)
    if data.timeout_seconds is not None:
        provider.timeout_seconds = data.timeout_seconds
    if data.enabled is not None:
        provider.enabled = data.enabled
    db.commit()
    db.refresh(provider)
    return provider


def delete_provider(db: Session, provider_id: str) -> None:
    provider = _get_or_404(db, provider_id)
    db.delete(provider)
    db.commit()


def add_model(db: Session, provider_id: str, data: ModelConfigIn) -> ModelConfig:
    _get_or_404(db, provider_id)
    exists = (
        db.query(ModelConfig)
        .filter_by(provider_id=provider_id, model_id=data.model_id.strip())
        .first()
    )
    if exists:
        raise ConflictError(f"模型 {data.model_id} 在该服务商下已存在")
    max_order = (
        db.query(ModelConfig)
        .filter_by(provider_id=provider_id)
        .count()
    )
    model = ModelConfig(
        provider_id=provider_id,
        model_id=data.model_id.strip(),
        display_name=data.display_name.strip(),
        capabilities=data.capabilities,
        is_default=data.is_default,
        sort_order=max_order * 10,
    )
    db.add(model)
    db.flush()
    _set_single_default(db, model)
    db.commit()
    db.refresh(model)
    return model


def update_model(db: Session, model_id: str, data: ModelConfigUpdate) -> ModelConfig:
    model = db.get(ModelConfig, model_id)
    if model is None:
        raise NotFoundError("模型不存在")
    if data.model_id is not None:
        model.model_id = data.model_id.strip()
    if data.display_name is not None:
        model.display_name = data.display_name.strip()
    if data.capabilities is not None:
        model.capabilities = data.capabilities
    if data.is_default is not None:
        model.is_default = data.is_default
    db.flush()
    _set_single_default(db, model)
    db.commit()
    db.refresh(model)
    return model


def delete_model(db: Session, model_id: str) -> None:
    model = db.get(ModelConfig, model_id)
    if model is None:
        raise NotFoundError("模型不存在")
    db.delete(model)
    db.commit()


def run_connection_test(
    db: Session, provider_id: str, model_id: str | None
) -> TestConnectionResultOut:
    result = test_connection(db, provider_id, model_id)
    return TestConnectionResultOut(ok=result.ok, code=result.code, message=result.message)


def get_setup_status(db: Session) -> SetupStatusOut:
    default_model = (
        db.query(ModelConfig)
        .join(Provider, ModelConfig.provider_id == Provider.id)
        .filter(Provider.enabled.is_(True), ModelConfig.is_default.is_(True))
        .first()
    )
    if default_model is None:
        default_model = (
            db.query(ModelConfig)
            .join(Provider, ModelConfig.provider_id == Provider.id)
            .filter(Provider.enabled.is_(True))
            .order_by(ModelConfig.sort_order, ModelConfig.created_at)
            .first()
        )
    if default_model is None:
        return SetupStatusOut(has_models=False)
    return SetupStatusOut(
        has_models=True,
        default_provider_id=default_model.provider_id,
        default_model_id=default_model.id,
        default_display_name=default_model.display_name,
    )
