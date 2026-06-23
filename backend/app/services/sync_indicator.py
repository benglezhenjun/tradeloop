"""V8 indicator persistence services."""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError

from app.config import HISTORY_START_DATE
from app.models import DailyIndicator, DailyQuote
from app.services.technical_indicators import calculate_stock_indicators


logger = logging.getLogger(__name__)


def _quote_to_dict(quote) -> dict:
    return {
        "trade_date": quote.trade_date,
        "close": float(quote.close or 0),
        "high": float(quote.high or 0),
        "low": float(quote.low or 0),
        "vol": float(quote.vol or 0),
        "turnover_rate": float(quote.turnover_rate or 0),
    }


def sync_indicators_daily(db, trade_dates: list[str]) -> dict:
    if not trade_dates:
        return {"synced_dates": 0, "total_rows": 0}

    total_rows = 0
    for idx, trade_date in enumerate(trade_dates):
        ts_codes = [
            row[0]
            for row in db.query(DailyQuote.ts_code)
            .filter(DailyQuote.trade_date == trade_date)
            .distinct()
            .all()
        ]

        rows = []
        for ts_code in ts_codes:
            try:
                quotes = (
                    db.query(DailyQuote)
                    .filter(DailyQuote.ts_code == ts_code, DailyQuote.trade_date <= trade_date)
                    .order_by(DailyQuote.trade_date.desc())
                    .limit(250)
                    .all()
                )
                if not quotes:
                    continue

                indicator_rows, _ = calculate_stock_indicators(
                    [_quote_to_dict(item) for item in reversed(quotes)]
                )
                if not indicator_rows:
                    continue
                row = dict(indicator_rows[-1])
                row["ts_code"] = ts_code
                row["trade_date"] = trade_date
                rows.append(row)
            except SQLAlchemyError:
                logger.error(
                    "[sync][indicator] database error trade_date=%s ts_code=%s",
                    trade_date,
                    ts_code,
                    exc_info=True,
                )
                raise
            except Exception as exc:
                logger.warning(
                    "[sync][indicator] skip trade_date=%s ts_code=%s error=%s",
                    trade_date,
                    ts_code,
                    exc,
                )
                continue

        if rows:
            db.commit()
            with db.begin():
                db.query(DailyIndicator).filter(DailyIndicator.trade_date == trade_date).delete()
                db.execute(DailyIndicator.__table__.insert(), rows)
            total_rows += len(rows)
        else:
            db.commit()

        if (idx + 1) % 20 == 0 or idx == len(trade_dates) - 1:
            logger.info(
                "[sync][indicator] %s/%s trade_date=%s rows=%s",
                idx + 1,
                len(trade_dates),
                trade_date,
                len(rows),
            )

    return {"synced_dates": len(trade_dates), "total_rows": total_rows}


def backfill_indicators(db, start_date: str = "20150101") -> dict:
    ts_codes = [row[0] for row in db.query(DailyQuote.ts_code).distinct().order_by(DailyQuote.ts_code).all()]
    total_rows = 0

    for idx, ts_code in enumerate(ts_codes):
        quotes = (
            db.query(DailyQuote)
            .filter(DailyQuote.ts_code == ts_code, DailyQuote.trade_date >= HISTORY_START_DATE)
            .order_by(DailyQuote.trade_date.asc())
            .all()
        )
        if not quotes:
            continue

        indicator_rows, _ = calculate_stock_indicators([_quote_to_dict(item) for item in quotes])
        rows = []
        for quote, indicator in zip(quotes, indicator_rows, strict=True):
            if quote.trade_date < start_date:
                continue
            row = dict(indicator)
            row["ts_code"] = ts_code
            row["trade_date"] = quote.trade_date
            rows.append(row)

        db.query(DailyIndicator).filter(DailyIndicator.ts_code == ts_code).delete()
        if rows:
            db.execute(DailyIndicator.__table__.insert(), rows)
            total_rows += len(rows)
        db.commit()

        if (idx + 1) % 100 == 0 or idx == len(ts_codes) - 1:
            logger.info(
                "[backfill][indicator] %s/%s ts_code=%s rows=%s",
                idx + 1,
                len(ts_codes),
                ts_code,
                len(rows),
            )

    return {"synced_stocks": len(ts_codes), "total_rows": total_rows}
