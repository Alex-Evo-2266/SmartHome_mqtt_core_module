import asyncio
import time
import traceback
from app.pkg.logger import MyLogger

CALLBACK_WARN_TIMEOUT = 2.0  # сек, подстрой под себя

logger = MyLogger().get_logger(__name__)

async def _run_callback_with_debug(
    callback,
    topic: str,
    payload: str,
    topic_pattern: str,
):
    cb_name = f"{callback.__module__}.{callback.__qualname__}"
    start = time.monotonic()

    try:
        logger.debug(
            f"[CALLBACK START] {cb_name} "
            f"(pattern={topic_pattern}, topic={topic})"
        )

        await callback(topic, payload)

        duration = time.monotonic() - start
        logger.debug(
            f"[CALLBACK DONE] {cb_name} "
            f"(pattern={topic_pattern}) in {duration:.3f}s"
        )

    except asyncio.CancelledError:
        logger.warning(
            f"[CALLBACK CANCELLED] {cb_name} "
            f"(pattern={topic_pattern})"
        )
        raise

    except Exception as e:
        logger.error(
            f"[CALLBACK ERROR] {cb_name} "
            f"(pattern={topic_pattern}): {e}",
            exc_info=True
        )

async def _watch_task(task: asyncio.Task, callback, topic, topic_pattern):
    cb_name = f"{callback.__module__}.{callback.__qualname__}"

    try:
        await asyncio.wait_for(task, timeout=CALLBACK_WARN_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error(
            f"[CALLBACK HANG] {cb_name} "
            f"(pattern={topic_pattern}, topic={topic}) "
            f"running > {CALLBACK_WARN_TIMEOUT}s"
        )
    except Exception:
        # ошибка уже залогирована в основной задаче
        pass
