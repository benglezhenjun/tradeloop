"""用户配置服务 (V5)"""

from sqlalchemy.orm import Session

from app.models.plan import UserConfig

DEFAULT_USER_CONFIGS = {
    "total_capital": "0",
    "commission_rate": "0.00025",
    "stamp_tax_rate": "0.001",
    "transfer_fee_rate": "0.00002",
}


def ensure_default_configs(db: Session) -> None:
    """确保默认配置项存在。"""
    changed = False
    for key, value in DEFAULT_USER_CONFIGS.items():
        row = db.get(UserConfig, key)
        if row is None:
            db.add(UserConfig(key=key, value=value))
            changed = True
    if changed:
        db.commit()


def get_config(db: Session, key: str) -> str | None:
    """获取配置值，不存在返回 None"""
    row = db.get(UserConfig, key)
    if row is None and key in DEFAULT_USER_CONFIGS:
        row = UserConfig(key=key, value=DEFAULT_USER_CONFIGS[key])
        db.add(row)
        db.commit()
        db.refresh(row)
    return row.value if row else None


def set_config(db: Session, key: str, value: str) -> dict:
    """设置配置值（存在则更新，不存在则创建）"""
    row = db.get(UserConfig, key)
    if row:
        row.value = value
    else:
        row = UserConfig(key=key, value=value)
        db.add(row)
    db.commit()
    return {"key": key, "value": value}
