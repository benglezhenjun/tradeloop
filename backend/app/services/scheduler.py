"""
APScheduler 定时任务。

在交易日 15:35 自动触发数据同步。
FastAPI 启动时注册，关闭时停止。
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import SCHEDULER_HOUR, SCHEDULER_MINUTE

_scheduler: BackgroundScheduler | None = None
logger = logging.getLogger(__name__)


def _daily_sync_job():
    """定时任务执行函数。"""
    from app.services.data_sync import try_start_sync

    logger.info("[定时任务] 开始每日数据同步...")
    try:
        started = try_start_sync()
        if not started:
            logger.info("[定时任务] 跳过：已有同步任务在运行中")
        else:
            logger.info("[定时任务] 同步完成")
    except Exception:
        logger.exception("daily sync job failed")


def start_scheduler():
    """启动调度器。"""
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(
        _daily_sync_job,
        trigger=CronTrigger(
            hour=SCHEDULER_HOUR,
            minute=SCHEDULER_MINUTE,
            day_of_week="mon-fri",
        ),
        id="daily_sync",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"[调度器] 已启动，每个工作日 {SCHEDULER_HOUR:02d}:{SCHEDULER_MINUTE:02d} 自动同步数据")


def stop_scheduler():
    """停止调度器。"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("[调度器] 已停止")
