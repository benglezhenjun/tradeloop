"""市场情绪快照计算服务。"""

from __future__ import annotations

import json
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import DailyQuote, LimitEventDaily, MarketSentimentDaily, ThemeHeatDaily


HIGH_BOARD_THRESHOLD = 3


def _zero_premium() -> dict:
    return {
        "yday_limit_premium_avg": 0.0,
        "yday_limit_premium_median": 0.0,
        "yday_limit_red_rate": 0.0,
        "yday_limit_sample_count": 0,
        "sample_codes": [],
    }


def _zero_high_board(threshold: int) -> dict:
    return {
        "high_board_threshold": threshold,
        "high_board_total": 0,
        "high_board_advanced": 0,
        "high_board_promotion_rate": 0.0,
        "candidate_codes": [],
        "advanced_codes": [],
    }


def _get_previous_trade_date(db: Session, trade_date: str) -> str | None:
    return (
        db.query(func.max(DailyQuote.trade_date))
        .filter(DailyQuote.trade_date < trade_date)
        .scalar()
    )


def calculate_max_limit_height(limit_up_rows: list[LimitEventDaily]) -> dict:
    if not limit_up_rows:
        return {
            "max_limit_height": 0,
            "max_limit_height_count": 0,
            "max_limit_height_codes": [],
        }

    max_limit_height = max(int(row.limit_times or 0) for row in limit_up_rows)
    max_limit_height_codes = sorted(
        row.ts_code for row in limit_up_rows if int(row.limit_times or 0) == max_limit_height
    )
    return {
        "max_limit_height": max_limit_height,
        "max_limit_height_count": len(max_limit_height_codes),
        "max_limit_height_codes": max_limit_height_codes,
    }


def calculate_broken_rate(limit_up_count: int, limit_broken_count: int) -> float:
    total = limit_up_count + limit_broken_count
    if total <= 0:
        return 0.0
    return limit_broken_count / total


def calculate_yday_limit_premium(db: Session, trade_date: str) -> dict:
    previous_trade_date = _get_previous_trade_date(db, trade_date)
    if not previous_trade_date:
        return _zero_premium()

    previous_limit_rows = (
        db.query(LimitEventDaily.ts_code)
        .filter(LimitEventDaily.trade_date == previous_trade_date)
        .filter(LimitEventDaily.limit_type == "U")
        .order_by(LimitEventDaily.ts_code.asc())
        .all()
    )
    if not previous_limit_rows:
        return _zero_premium()

    candidate_codes = [row[0] for row in previous_limit_rows]
    quote_rows = (
        db.query(DailyQuote.ts_code, DailyQuote.pct_chg)
        .filter(DailyQuote.trade_date == trade_date)
        .filter(DailyQuote.ts_code.in_(candidate_codes))
        .filter(DailyQuote.pct_chg.isnot(None))
        .all()
    )
    if not quote_rows:
        return _zero_premium()

    quote_map = {ts_code: float(pct_chg) for ts_code, pct_chg in quote_rows}
    sample_codes = [code for code in candidate_codes if code in quote_map]
    samples = [quote_map[code] for code in sample_codes]
    if not samples:
        return _zero_premium()

    sample_count = len(samples)
    red_count = sum(1 for value in samples if value > 0)
    return {
        "yday_limit_premium_avg": sum(samples) / sample_count,
        "yday_limit_premium_median": float(median(samples)),
        "yday_limit_red_rate": red_count / sample_count,
        "yday_limit_sample_count": sample_count,
        "sample_codes": sample_codes,
    }


def calculate_high_board_promotion_rate(
    db: Session,
    trade_date: str,
    threshold: int = HIGH_BOARD_THRESHOLD,
) -> dict:
    previous_trade_date = _get_previous_trade_date(db, trade_date)
    if not previous_trade_date:
        return _zero_high_board(threshold)

    previous_rows = (
        db.query(LimitEventDaily.ts_code, LimitEventDaily.limit_times)
        .filter(LimitEventDaily.trade_date == previous_trade_date)
        .filter(LimitEventDaily.limit_type == "U")
        .filter(LimitEventDaily.limit_times >= threshold)
        .order_by(LimitEventDaily.ts_code.asc())
        .all()
    )
    if not previous_rows:
        return _zero_high_board(threshold)

    current_rows = (
        db.query(LimitEventDaily.ts_code, LimitEventDaily.limit_times)
        .filter(LimitEventDaily.trade_date == trade_date)
        .filter(LimitEventDaily.limit_type == "U")
        .all()
    )
    current_map = {ts_code: int(limit_times or 0) for ts_code, limit_times in current_rows}

    candidate_codes = [ts_code for ts_code, _ in previous_rows]
    advanced_codes = [
        ts_code
        for ts_code, limit_times in previous_rows
        if current_map.get(ts_code) == int(limit_times or 0) + 1
    ]
    high_board_total = len(candidate_codes)
    high_board_advanced = len(advanced_codes)
    return {
        "high_board_threshold": threshold,
        "high_board_total": high_board_total,
        "high_board_advanced": high_board_advanced,
        "high_board_promotion_rate": (
            high_board_advanced / high_board_total if high_board_total else 0.0
        ),
        "candidate_codes": candidate_codes,
        "advanced_codes": advanced_codes,
    }


def calculate_main_theme_streak(db: Session, trade_date: str) -> dict:
    theme_rows = (
        db.query(ThemeHeatDaily)
        .filter(ThemeHeatDaily.trade_date == trade_date)
        .all()
    )
    if not theme_rows:
        return {
            "main_theme_code": None,
            "main_theme_name": None,
            "main_theme_score": None,
            "main_theme_streak_days": 0,
        }

    theme_rows.sort(
        key=lambda row: (
            row.rank is None,
            row.rank if row.rank is not None else 10**9,
            -(float(row.score) if row.score is not None else 0.0),
            row.theme_code or "",
        )
    )
    leader = theme_rows[0]

    previous_trade_date = _get_previous_trade_date(db, trade_date)
    previous_snapshot = db.get(MarketSentimentDaily, previous_trade_date) if previous_trade_date else None
    streak_days = 1
    if (
        previous_snapshot
        and previous_snapshot.main_theme_code
        and previous_snapshot.main_theme_code == leader.theme_code
    ):
        streak_days = int(previous_snapshot.main_theme_streak_days or 0) + 1

    return {
        "main_theme_code": leader.theme_code,
        "main_theme_name": leader.theme_name,
        "main_theme_score": float(leader.score) if leader.score is not None else None,
        "main_theme_streak_days": streak_days,
    }


def build_market_sentiment_snapshot(
    db: Session,
    trade_date: str,
    threshold: int = HIGH_BOARD_THRESHOLD,
) -> dict:
    limit_up_rows = (
        db.query(LimitEventDaily)
        .filter(LimitEventDaily.trade_date == trade_date)
        .filter(LimitEventDaily.limit_type == "U")
        .order_by(LimitEventDaily.limit_times.desc(), LimitEventDaily.ts_code.asc())
        .all()
    )
    limit_broken_rows = (
        db.query(LimitEventDaily)
        .filter(LimitEventDaily.trade_date == trade_date)
        .filter(LimitEventDaily.limit_type == "Z")
        .order_by(LimitEventDaily.limit_times.desc(), LimitEventDaily.ts_code.asc())
        .all()
    )

    max_limit = calculate_max_limit_height(limit_up_rows)
    yday_premium = calculate_yday_limit_premium(db, trade_date)
    high_board = calculate_high_board_promotion_rate(db, trade_date, threshold=threshold)
    main_theme = calculate_main_theme_streak(db, trade_date)

    notes = {
        "max_limit_height_codes": max_limit["max_limit_height_codes"],
        "yday_limit_sample_codes": yday_premium["sample_codes"],
        "high_board_candidate_codes": high_board["candidate_codes"],
        "high_board_advanced_codes": high_board["advanced_codes"],
    }

    return {
        "trade_date": trade_date,
        "max_limit_height": max_limit["max_limit_height"],
        "max_limit_height_count": max_limit["max_limit_height_count"],
        "max_limit_height_codes_json": json.dumps(
            max_limit["max_limit_height_codes"], ensure_ascii=False
        ),
        "limit_up_count": len(limit_up_rows),
        "limit_broken_count": len(limit_broken_rows),
        "broken_rate": calculate_broken_rate(len(limit_up_rows), len(limit_broken_rows)),
        "yday_limit_premium_avg": yday_premium["yday_limit_premium_avg"],
        "yday_limit_premium_median": yday_premium["yday_limit_premium_median"],
        "yday_limit_red_rate": yday_premium["yday_limit_red_rate"],
        "yday_limit_sample_count": yday_premium["yday_limit_sample_count"],
        "high_board_threshold": high_board["high_board_threshold"],
        "high_board_total": high_board["high_board_total"],
        "high_board_advanced": high_board["high_board_advanced"],
        "high_board_promotion_rate": high_board["high_board_promotion_rate"],
        "main_theme_code": main_theme["main_theme_code"],
        "main_theme_name": main_theme["main_theme_name"],
        "main_theme_score": main_theme["main_theme_score"],
        "main_theme_streak_days": main_theme["main_theme_streak_days"],
        "notes_json": json.dumps(notes, ensure_ascii=False),
    }


def save_market_sentiment_snapshot(
    db: Session,
    trade_date: str,
    threshold: int = HIGH_BOARD_THRESHOLD,
) -> dict:
    payload = build_market_sentiment_snapshot(db, trade_date, threshold=threshold)
    row = db.get(MarketSentimentDaily, trade_date)

    if row is None:
        row = MarketSentimentDaily(**payload)
        db.add(row)
    else:
        for key, value in payload.items():
            setattr(row, key, value)

    db.commit()
    return payload


def sync_market_sentiment_daily(
    db: Session,
    trade_dates: list[str],
    threshold: int = HIGH_BOARD_THRESHOLD,
) -> dict:
    if not trade_dates:
        return {"synced_dates": 0, "successful_dates": 0, "failed_dates": [], "total_rows": 0}

    ordered_dates = sorted(set(trade_dates))
    total_rows = 0
    successful_dates = 0
    failed_dates: list[dict[str, str]] = []

    for trade_date in ordered_dates:
        try:
            save_market_sentiment_snapshot(db, trade_date, threshold=threshold)
            successful_dates += 1
            total_rows += 1
        except Exception as exc:
            db.rollback()
            failed_dates.append({"trade_date": trade_date, "error": str(exc)})

    return {
        "synced_dates": len(ordered_dates),
        "successful_dates": successful_dates,
        "failed_dates": failed_dates,
        "total_rows": total_rows,
    }


def backfill_market_sentiment(
    db: Session,
    start_date: str = "20150101",
    threshold: int = HIGH_BOARD_THRESHOLD,
) -> dict:
    latest = db.query(func.max(MarketSentimentDaily.trade_date)).scalar()
    trade_date_set: set[str] = set()
    for model in (DailyQuote, LimitEventDaily, ThemeHeatDaily):
        query = db.query(model.trade_date).filter(model.trade_date >= start_date)
        if latest:
            query = query.filter(model.trade_date > latest)
        trade_date_set.update(row[0] for row in query.distinct().all())
    trade_dates = sorted(trade_date_set)
    db.commit()

    total_rows = 0
    successful_dates = 0
    failed_dates: list[dict[str, str]] = []
    for trade_date in trade_dates:
        result = sync_market_sentiment_daily(db, [trade_date], threshold=threshold)
        total_rows += result["total_rows"]
        successful_dates += result["successful_dates"]
        failed_dates.extend(result["failed_dates"])

    return {
        "synced_dates": len(trade_dates),
        "successful_dates": successful_dates,
        "failed_dates": failed_dates,
        "total_rows": total_rows,
    }


def _empty_sentiment_summary() -> dict:
    return {
        "trade_date": None,
        "max_limit_height": 0,
        "max_limit_height_count": 0,
        "max_limit_height_codes": [],
        "limit_up_count": 0,
        "limit_broken_count": 0,
        "broken_rate": 0.0,
        "yday_limit_premium_avg": 0.0,
        "yday_limit_premium_median": 0.0,
        "yday_limit_red_rate": 0.0,
        "yday_limit_sample_count": 0,
        "high_board_threshold": HIGH_BOARD_THRESHOLD,
        "high_board_total": 0,
        "high_board_advanced": 0,
        "high_board_promotion_rate": 0.0,
        "main_theme_code": None,
        "main_theme_name": None,
        "main_theme_score": None,
        "main_theme_streak_days": 0,
    }


def _deserialize_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _deserialize_json_dict(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _serialize_sentiment_row(row: MarketSentimentDaily) -> dict:
    return {
        "trade_date": row.trade_date,
        "max_limit_height": int(row.max_limit_height or 0),
        "max_limit_height_count": int(row.max_limit_height_count or 0),
        "max_limit_height_codes": _deserialize_json_list(row.max_limit_height_codes_json),
        "limit_up_count": int(row.limit_up_count or 0),
        "limit_broken_count": int(row.limit_broken_count or 0),
        "broken_rate": float(row.broken_rate or 0.0),
        "yday_limit_premium_avg": float(row.yday_limit_premium_avg or 0.0),
        "yday_limit_premium_median": float(row.yday_limit_premium_median or 0.0),
        "yday_limit_red_rate": float(row.yday_limit_red_rate or 0.0),
        "yday_limit_sample_count": int(row.yday_limit_sample_count or 0),
        "high_board_threshold": int(row.high_board_threshold or HIGH_BOARD_THRESHOLD),
        "high_board_total": int(row.high_board_total or 0),
        "high_board_advanced": int(row.high_board_advanced or 0),
        "high_board_promotion_rate": float(row.high_board_promotion_rate or 0.0),
        "main_theme_code": row.main_theme_code,
        "main_theme_name": row.main_theme_name,
        "main_theme_score": float(row.main_theme_score) if row.main_theme_score is not None else None,
        "main_theme_streak_days": int(row.main_theme_streak_days or 0),
    }


def get_sentiment_summary(db: Session) -> dict:
    row = (
        db.query(MarketSentimentDaily)
        .order_by(MarketSentimentDaily.trade_date.desc())
        .first()
    )
    if row is None:
        return _empty_sentiment_summary()
    return _serialize_sentiment_row(row)


def get_sentiment_history(db: Session, days: int = 120) -> list[dict]:
    rows = (
        db.query(MarketSentimentDaily)
        .order_by(MarketSentimentDaily.trade_date.desc())
        .limit(days)
        .all()
    )
    rows.reverse()
    return [_serialize_sentiment_row(row) for row in rows]


def get_sentiment_themes(db: Session, days: int = 120) -> list[dict]:
    rows = (
        db.query(MarketSentimentDaily)
        .order_by(MarketSentimentDaily.trade_date.desc())
        .limit(days)
        .all()
    )
    rows.reverse()
    return [
        {
            "trade_date": row.trade_date,
            "main_theme_code": row.main_theme_code,
            "main_theme_name": row.main_theme_name,
            "main_theme_score": float(row.main_theme_score) if row.main_theme_score is not None else None,
            "main_theme_streak_days": int(row.main_theme_streak_days or 0),
        }
        for row in rows
    ]


def _get_limit_event_samples(db: Session, trade_date: str, limit_type: str) -> list[dict]:
    rows = (
        db.query(LimitEventDaily)
        .filter(LimitEventDaily.trade_date == trade_date)
        .filter(LimitEventDaily.limit_type == limit_type)
        .order_by(LimitEventDaily.limit_times.desc(), LimitEventDaily.ts_code.asc())
        .limit(10)
        .all()
    )
    return [
        {
            "ts_code": row.ts_code,
            "name": row.name,
            "limit_times": int(row.limit_times or 0),
            "up_stat": row.up_stat,
        }
        for row in rows
    ]


def _get_yday_limit_samples(db: Session, trade_date: str, sample_codes: list[str]) -> list[dict]:
    if not sample_codes:
        return []

    previous_trade_date = _get_previous_trade_date(db, trade_date)
    if not previous_trade_date:
        return []

    previous_rows = (
        db.query(LimitEventDaily)
        .filter(LimitEventDaily.trade_date == previous_trade_date)
        .filter(LimitEventDaily.limit_type == "U")
        .filter(LimitEventDaily.ts_code.in_(sample_codes))
        .all()
    )
    current_rows = (
        db.query(DailyQuote.ts_code, DailyQuote.pct_chg)
        .filter(DailyQuote.trade_date == trade_date)
        .filter(DailyQuote.ts_code.in_(sample_codes))
        .all()
    )
    previous_map = {row.ts_code: row for row in previous_rows}
    current_map = {ts_code: pct_chg for ts_code, pct_chg in current_rows}

    samples = []
    for code in sample_codes:
        previous_row = previous_map.get(code)
        if previous_row is None:
            continue
        samples.append(
            {
                "ts_code": code,
                "name": previous_row.name,
                "prev_limit_times": int(previous_row.limit_times or 0),
                "today_pct_chg": float(current_map[code]) if code in current_map else None,
            }
        )
    return samples


def _get_high_board_samples(
    db: Session,
    trade_date: str,
    candidate_codes: list[str],
    advanced_codes: list[str],
) -> list[dict]:
    if not candidate_codes:
        return []

    previous_trade_date = _get_previous_trade_date(db, trade_date)
    if not previous_trade_date:
        return []

    previous_rows = (
        db.query(LimitEventDaily)
        .filter(LimitEventDaily.trade_date == previous_trade_date)
        .filter(LimitEventDaily.limit_type == "U")
        .filter(LimitEventDaily.ts_code.in_(candidate_codes))
        .all()
    )
    current_rows = (
        db.query(LimitEventDaily)
        .filter(LimitEventDaily.trade_date == trade_date)
        .filter(LimitEventDaily.limit_type == "U")
        .filter(LimitEventDaily.ts_code.in_(candidate_codes))
        .all()
    )
    previous_map = {row.ts_code: row for row in previous_rows}
    current_map = {row.ts_code: row for row in current_rows}
    advanced_code_set = set(advanced_codes)

    samples = []
    for code in candidate_codes:
        previous_row = previous_map.get(code)
        if previous_row is None:
            continue
        current_row = current_map.get(code)
        samples.append(
            {
                "ts_code": code,
                "name": current_row.name if current_row else previous_row.name,
                "prev_limit_times": int(previous_row.limit_times or 0),
                "current_limit_times": int(current_row.limit_times or 0) if current_row else None,
                "is_advanced": code in advanced_code_set,
            }
        )
    return samples


def _get_theme_leaders(db: Session, trade_date: str) -> list[dict]:
    rows = (
        db.query(ThemeHeatDaily)
        .filter(ThemeHeatDaily.trade_date == trade_date)
        .order_by(ThemeHeatDaily.rank.asc(), ThemeHeatDaily.score.desc(), ThemeHeatDaily.theme_code.asc())
        .limit(10)
        .all()
    )
    return [
        {
            "theme_code": row.theme_code,
            "theme_name": row.theme_name,
            "rank": row.rank,
            "score": float(row.score) if row.score is not None else None,
            "up_stat": row.up_stat,
        }
        for row in rows
    ]


def get_sentiment_detail(db: Session, trade_date: str) -> dict:
    row = db.get(MarketSentimentDaily, trade_date)
    if row is None:
        return {
            "trade_date": trade_date,
            "summary": None,
            "limit_up_samples": [],
            "limit_broken_samples": [],
            "yday_limit_samples": [],
            "high_board_samples": [],
            "theme_leaders": [],
        }

    notes = _deserialize_json_dict(row.notes_json)
    return {
        "trade_date": trade_date,
        "summary": _serialize_sentiment_row(row),
        "limit_up_samples": _get_limit_event_samples(db, trade_date, "U"),
        "limit_broken_samples": _get_limit_event_samples(db, trade_date, "Z"),
        "yday_limit_samples": _get_yday_limit_samples(
            db, trade_date, notes.get("yday_limit_sample_codes", [])
        ),
        "high_board_samples": _get_high_board_samples(
            db,
            trade_date,
            notes.get("high_board_candidate_codes", []),
            notes.get("high_board_advanced_codes", []),
        ),
        "theme_leaders": _get_theme_leaders(db, trade_date),
    }


def _load_json_array(raw: str | None) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _load_json_object(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _empty_summary() -> dict:
    return {
        "trade_date": None,
        "max_limit_height": 0,
        "max_limit_height_count": 0,
        "max_limit_height_codes": [],
        "limit_up_count": 0,
        "limit_broken_count": 0,
        "broken_rate": 0.0,
        "yday_limit_premium_avg": 0.0,
        "yday_limit_premium_median": 0.0,
        "yday_limit_red_rate": 0.0,
        "yday_limit_sample_count": 0,
        "high_board_threshold": HIGH_BOARD_THRESHOLD,
        "high_board_total": 0,
        "high_board_advanced": 0,
        "high_board_promotion_rate": 0.0,
        "main_theme_code": None,
        "main_theme_name": None,
        "main_theme_score": None,
        "main_theme_streak_days": 0,
        "notes": {},
    }


def _serialize_snapshot(row: MarketSentimentDaily | None) -> dict | None:
    if row is None:
        return None

    return {
        "trade_date": row.trade_date,
        "max_limit_height": int(row.max_limit_height or 0),
        "max_limit_height_count": int(row.max_limit_height_count or 0),
        "max_limit_height_codes": _load_json_array(row.max_limit_height_codes_json),
        "limit_up_count": int(row.limit_up_count or 0),
        "limit_broken_count": int(row.limit_broken_count or 0),
        "broken_rate": float(row.broken_rate or 0.0),
        "yday_limit_premium_avg": float(row.yday_limit_premium_avg or 0.0),
        "yday_limit_premium_median": float(row.yday_limit_premium_median or 0.0),
        "yday_limit_red_rate": float(row.yday_limit_red_rate or 0.0),
        "yday_limit_sample_count": int(row.yday_limit_sample_count or 0),
        "high_board_threshold": int(row.high_board_threshold or HIGH_BOARD_THRESHOLD),
        "high_board_total": int(row.high_board_total or 0),
        "high_board_advanced": int(row.high_board_advanced or 0),
        "high_board_promotion_rate": float(row.high_board_promotion_rate or 0.0),
        "main_theme_code": row.main_theme_code,
        "main_theme_name": row.main_theme_name,
        "main_theme_score": float(row.main_theme_score) if row.main_theme_score is not None else None,
        "main_theme_streak_days": int(row.main_theme_streak_days or 0),
        "notes": _load_json_object(row.notes_json),
    }


def get_market_sentiment_summary(db: Session) -> dict:
    row = (
        db.query(MarketSentimentDaily)
        .order_by(MarketSentimentDaily.trade_date.desc())
        .first()
    )
    return _serialize_snapshot(row) or _empty_summary()


def get_market_sentiment_history(db: Session, days: int = 120) -> list[dict]:
    rows = (
        db.query(MarketSentimentDaily)
        .order_by(MarketSentimentDaily.trade_date.desc())
        .limit(days)
        .all()
    )
    return [_serialize_snapshot(row) for row in reversed(rows)]


def get_market_sentiment_themes(db: Session, days: int = 120) -> list[dict]:
    rows = (
        db.query(MarketSentimentDaily)
        .filter(MarketSentimentDaily.main_theme_code.isnot(None))
        .order_by(MarketSentimentDaily.trade_date.desc())
        .limit(days)
        .all()
    )
    return [
        {
            "trade_date": row.trade_date,
            "main_theme_code": row.main_theme_code,
            "main_theme_name": row.main_theme_name,
            "main_theme_score": float(row.main_theme_score) if row.main_theme_score is not None else None,
            "main_theme_streak_days": int(row.main_theme_streak_days or 0),
        }
        for row in reversed(rows)
    ]


def get_market_sentiment_detail(db: Session, trade_date: str) -> dict:
    row = db.get(MarketSentimentDaily, trade_date)
    if row is None:
        return {
            "trade_date": trade_date,
            "summary": None,
            "limit_up_samples": [],
            "limit_broken_samples": [],
            "yday_limit_samples": [],
            "high_board_samples": [],
            "theme_leaders": [],
        }

    summary = _serialize_snapshot(row)
    notes = summary["notes"]
    previous_trade_date = _get_previous_trade_date(db, trade_date)

    limit_up_samples = [
        {
            "ts_code": item.ts_code,
            "name": item.name,
            "limit_times": int(item.limit_times or 0),
        }
        for item in (
            db.query(LimitEventDaily)
            .filter(LimitEventDaily.trade_date == trade_date)
            .filter(LimitEventDaily.limit_type == "U")
            .order_by(LimitEventDaily.limit_times.desc(), LimitEventDaily.ts_code.asc())
            .limit(20)
            .all()
        )
    ]

    limit_broken_samples = [
        {
            "ts_code": item.ts_code,
            "name": item.name,
            "limit_times": int(item.limit_times or 0),
        }
        for item in (
            db.query(LimitEventDaily)
            .filter(LimitEventDaily.trade_date == trade_date)
            .filter(LimitEventDaily.limit_type == "Z")
            .order_by(LimitEventDaily.limit_times.desc(), LimitEventDaily.ts_code.asc())
            .limit(20)
            .all()
        )
    ]

    yday_sample_codes = notes.get("yday_limit_sample_codes", [])
    yday_name_map: dict[str, str | None] = {}
    if previous_trade_date and yday_sample_codes:
        yday_name_map = {
            item.ts_code: item.name
            for item in (
                db.query(LimitEventDaily)
                .filter(LimitEventDaily.trade_date == previous_trade_date)
                .filter(LimitEventDaily.limit_type == "U")
                .filter(LimitEventDaily.ts_code.in_(yday_sample_codes))
                .all()
            )
        }
    yday_quote_map = {
        ts_code: float(pct_chg)
        for ts_code, pct_chg in (
            db.query(DailyQuote.ts_code, DailyQuote.pct_chg)
            .filter(DailyQuote.trade_date == trade_date)
            .filter(DailyQuote.ts_code.in_(yday_sample_codes))
            .filter(DailyQuote.pct_chg.isnot(None))
            .all()
        )
    }
    yday_limit_samples = [
        {
            "ts_code": code,
            "name": yday_name_map.get(code),
            "today_pct_chg": yday_quote_map[code],
        }
        for code in yday_sample_codes
        if code in yday_quote_map
    ]

    candidate_codes = notes.get("high_board_candidate_codes", [])
    advanced_codes = set(notes.get("high_board_advanced_codes", []))
    previous_limit_map: dict[str, tuple[int, str | None]] = {}
    if previous_trade_date and candidate_codes:
        previous_limit_map = {
            item.ts_code: (int(item.limit_times or 0), item.name)
            for item in (
                db.query(LimitEventDaily)
                .filter(LimitEventDaily.trade_date == previous_trade_date)
                .filter(LimitEventDaily.limit_type == "U")
                .filter(LimitEventDaily.ts_code.in_(candidate_codes))
                .all()
            )
        }
    current_limit_map = {
        item.ts_code: int(item.limit_times or 0)
        for item in (
            db.query(LimitEventDaily)
            .filter(LimitEventDaily.trade_date == trade_date)
            .filter(LimitEventDaily.limit_type == "U")
            .filter(LimitEventDaily.ts_code.in_(candidate_codes))
            .all()
        )
    }
    high_board_samples = [
        {
            "ts_code": code,
            "name": previous_limit_map.get(code, (0, None))[1],
            "yesterday_limit_times": previous_limit_map.get(code, (0, None))[0],
            "today_limit_times": current_limit_map.get(code),
            "is_advanced": code in advanced_codes,
        }
        for code in candidate_codes
    ]

    theme_rows = (
        db.query(ThemeHeatDaily)
        .filter(ThemeHeatDaily.trade_date == trade_date)
        .all()
    )
    theme_rows.sort(
        key=lambda item: (
            item.rank is None,
            item.rank if item.rank is not None else 10**9,
            -(float(item.score) if item.score is not None else 0.0),
            item.theme_code or "",
        )
    )
    theme_leaders = [
        {
            "theme_code": item.theme_code,
            "theme_name": item.theme_name,
            "rank": item.rank,
            "score": float(item.score) if item.score is not None else None,
        }
        for item in theme_rows[:20]
    ]

    return {
        "trade_date": trade_date,
        "summary": summary,
        "limit_up_samples": limit_up_samples,
        "limit_broken_samples": limit_broken_samples,
        "yday_limit_samples": yday_limit_samples,
        "high_board_samples": high_board_samples,
        "theme_leaders": theme_leaders,
    }
