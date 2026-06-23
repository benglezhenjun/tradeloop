"""
Watchlist service layer.
"""

from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import AMOUNT_UNIT_TO_YI, MV_UNIT_TO_YI
from app.errors import build_error
from app.models import StockBasic
from app.models.watchlist import WatchlistGroup, WatchlistStock


def _normalize_codes(ts_codes: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    codes: list[str] = []
    for raw_code in ts_codes:
        code = raw_code.strip() if raw_code else ""
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return codes


def _fetch_existing_codes(
    db: Session,
    table_name: str,
    codes: list[str],
    group_id: int | None = None,
) -> set[str]:
    if not codes:
        return set()

    if table_name == "watchlist_stock" and group_id is not None:
        rows = (
            db.query(WatchlistStock.ts_code)
            .filter(WatchlistStock.group_id == group_id, WatchlistStock.ts_code.in_(codes))
            .all()
        )
        return {row[0] for row in rows}

    if table_name == "stock_basic":
        rows = db.query(StockBasic.ts_code).filter(StockBasic.ts_code.in_(codes)).all()
        return {row[0] for row in rows}

    raise ValueError(f"不支持的表名: {table_name}")


def _latest_quote_join_sql() -> str:
    return """
        LEFT JOIN daily_quote dq
            ON dq.ts_code = ws.ts_code
           AND dq.trade_date = (
               SELECT MAX(dq2.trade_date)
               FROM daily_quote dq2
               WHERE dq2.ts_code = ws.ts_code
           )
    """


def list_groups(db: Session) -> list[dict]:
    rows = db.execute(text("""
        SELECT g.id, g.name, g.description, g.sort_order, g.created_at,
               COUNT(s.id) AS stock_count
        FROM watchlist_group g
        LEFT JOIN watchlist_stock s ON g.id = s.group_id
        GROUP BY g.id
        ORDER BY g.sort_order, g.created_at
    """)).mappings().all()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "sort_order": row["sort_order"],
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "stock_count": row["stock_count"],
        }
        for row in rows
    ]


def create_group(db: Session, name: str, description: str = "") -> dict:
    group = WatchlistGroup(name=name, description=description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "sort_order": group.sort_order,
    }


def update_group(db: Session, group_id: int, **kwargs) -> dict | None:
    group = db.get(WatchlistGroup, group_id)
    if not group:
        return None

    for key in ("name", "description", "sort_order"):
        if key in kwargs and kwargs[key] is not None:
            setattr(group, key, kwargs[key])

    db.commit()
    db.refresh(group)
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "sort_order": group.sort_order,
    }


def delete_group(db: Session, group_id: int) -> bool:
    group = db.get(WatchlistGroup, group_id)
    if not group:
        return False
    db.delete(group)
    db.commit()
    return True


def _stock_query_with_quote(extra_where: str = "") -> str:
    where_clause = f"WHERE {extra_where}" if extra_where else ""
    return f"""
        SELECT ws.ts_code, ws.note, ws.added_at, ws.group_id,
               sb.name, sb.industry,
               dq.close, dq.pct_chg, dq.amount, dq.total_mv
        FROM watchlist_stock ws
        JOIN stock_basic sb ON ws.ts_code = sb.ts_code
        {_latest_quote_join_sql()}
        {where_clause}
        ORDER BY ws.added_at DESC, ws.id DESC
    """


def _format_stock_row(row) -> dict:
    return {
        "ts_code": row["ts_code"],
        "note": row["note"],
        "added_at": str(row["added_at"]) if row["added_at"] else None,
        "group_id": row["group_id"],
        "name": row["name"],
        "industry": row["industry"],
        "close": round(row["close"], 2) if row["close"] is not None else None,
        "pct_chg": round(row["pct_chg"], 2) if row["pct_chg"] is not None else None,
        "amount_yi": round(row["amount"] / AMOUNT_UNIT_TO_YI, 2) if row["amount"] is not None else None,
        "total_mv_yi": round(row["total_mv"] / MV_UNIT_TO_YI, 2) if row["total_mv"] is not None else None,
    }


def _stock_exists(db: Session, ts_code: str) -> bool:
    return db.query(StockBasic.ts_code).filter(StockBasic.ts_code == ts_code).first() is not None


def get_group_stocks(db: Session, group_id: int) -> list[dict] | None:
    if not db.get(WatchlistGroup, group_id):
        return None

    sql = _stock_query_with_quote("ws.group_id = :group_id")
    rows = db.execute(text(sql), {"group_id": group_id}).mappings().all()
    return [_format_stock_row(row) for row in rows]


def get_all_stocks(db: Session) -> list[dict]:
    sql = f"""
        SELECT ws.ts_code, ws.note, ws.added_at, ws.group_id,
               sb.name, sb.industry,
               dq.close, dq.pct_chg, dq.amount, dq.total_mv
        FROM watchlist_stock ws
        JOIN stock_basic sb ON ws.ts_code = sb.ts_code
        {_latest_quote_join_sql()}
        WHERE ws.id = (
            SELECT MAX(ws2.id)
            FROM watchlist_stock ws2
            WHERE ws2.ts_code = ws.ts_code
        )
        ORDER BY ws.added_at DESC, ws.id DESC
    """
    rows = db.execute(text(sql)).mappings().all()
    return [_format_stock_row(row) for row in rows]


def add_stock(db: Session, group_id: int, ts_code: str, note: str = "") -> dict:
    normalized_codes = _normalize_codes([ts_code])
    normalized_code = normalized_codes[0] if normalized_codes else ""

    if not db.get(WatchlistGroup, group_id):
        return build_error(f"分组 {group_id} 不存在")
    if not normalized_code:
        return build_error("股票代码不能为空")
    if not _stock_exists(db, normalized_code):
        return build_error(f"股票 {normalized_code} 不存在")

    stock = WatchlistStock(group_id=group_id, ts_code=normalized_code, note=note)
    try:
        db.add(stock)
        db.commit()
        db.refresh(stock)
        return {"ts_code": stock.ts_code, "group_id": stock.group_id, "note": stock.note}
    except IntegrityError:
        db.rollback()
        return build_error(f"{normalized_code} 已在该分组中")


def remove_stock(db: Session, group_id: int, ts_code: str) -> bool:
    result = db.execute(
        text("DELETE FROM watchlist_stock WHERE group_id = :gid AND ts_code = :code"),
        {"gid": group_id, "code": ts_code},
    )
    db.commit()
    return result.rowcount > 0


def batch_add_stocks(db: Session, group_id: int, ts_codes: list[str]) -> dict:
    if not db.get(WatchlistGroup, group_id):
        return build_error(f"分组 {group_id} 不存在")

    normalized_codes = _normalize_codes(ts_codes)
    if not normalized_codes:
        return {
            "added": 0,
            "skipped": 0,
            "skipped_existing": 0,
            "skipped_invalid": 0,
            "invalid_codes": [],
        }

    valid_codes = _fetch_existing_codes(db, "stock_basic", normalized_codes)
    existing_codes = _fetch_existing_codes(db, "watchlist_stock", normalized_codes, group_id=group_id)

    invalid_codes = [code for code in normalized_codes if code not in valid_codes]
    new_codes = [code for code in normalized_codes if code in valid_codes and code not in existing_codes]

    for code in new_codes:
        db.add(WatchlistStock(group_id=group_id, ts_code=code))

    try:
        if new_codes:
            db.commit()
    except IntegrityError:
        db.rollback()
        return build_error("批量添加失败，请重试")

    skipped_existing = len(normalized_codes) - len(new_codes) - len(invalid_codes)
    skipped_invalid = len(invalid_codes)

    return {
        "added": len(new_codes),
        "skipped": skipped_existing + skipped_invalid,
        "skipped_existing": skipped_existing,
        "skipped_invalid": skipped_invalid,
        "invalid_codes": invalid_codes,
    }
