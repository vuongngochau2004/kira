import logging

from loguru import logger

from src.shared.infrastructure.monitoring.logger import InterceptHandler


def test_intercepted_message_with_angle_brackets_is_logged_verbatim() -> None:
    records: list[str] = []
    sink_id = logger.add(records.append, level="DEBUG", format="{message}")
    std_logger = logging.getLogger("tests.intercept")
    std_logger.handlers = [InterceptHandler()]
    std_logger.propagate = False
    std_logger.setLevel(logging.DEBUG)
    try:
        std_logger.debug("[#0000]  _: <POOL> created, routing address %s", "localhost:7687")
    finally:
        logger.remove(sink_id)
    assert any("<POOL> created, routing address localhost:7687" in record for record in records)
