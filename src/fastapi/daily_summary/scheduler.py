import asyncio
import json
import logging
import threading
import time

import schedule

from src.fastapi.daily_summary.repositories import IDailySummaryRepository
from src.fastapi.daily_summary.schemas import DailyVehicleSummary
from src.fastapi.database.dependencies import verify_database
from src.fastapi.redis.redis import redis_manager

logger = logging.getLogger(__name__)


class DailySummaryScheduler:
    def __init__(
        self,
        daily_summary_repo: IDailySummaryRepository,
        loop: asyncio.AbstractEventLoop,
    ):
        self.daily_summary_repo = daily_summary_repo
        self.loop = loop

    def run(self):
        schedule.every(10).seconds.do(self.run_job)
        threading.Thread(target=self._schedule_loop, daemon=True).start()
        logger.info("Running the scheduler")

    def _schedule_loop(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    async def get_summary_keys(self):
        client = redis_manager.redis_client
        cursor = 0
        summary_keys = []

        while True:
            cursor, keys = await client.scan(
                cursor=cursor, match="summary:*", count=500
            )
            summary_keys.extend(keys)
            if cursor == 0:
                break

        return summary_keys

    def run_job(self):
        # Run the async task in the background
        asyncio.run_coroutine_threadsafe(self._save_summaries_to_db(), self.loop)

    async def _save_summaries_to_db(self):
        logger.info("Starting save summaries")
        saved_keys = await self.get_summary_keys()
        for key in saved_keys:
            serialized = await redis_manager.redis_client.get(key)
            if not serialized:
                continue

            try:
                data = json.loads(serialized)
                summary = DailyVehicleSummary(**data)
                summary_model = summary.to_model()
                db = await verify_database()
                await self.daily_summary_repo.upsert_summary(db, summary_model)
                logger.info(f"Save summary successfully to DB with {key}")
            except Exception as e:
                logger.error(f"Failed to process key {key}: {e}")
