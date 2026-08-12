"""Runtime policies shared by services."""

import logging

from app.core.config import settings
from app.repositories.oracle import OracleRepositoryError

logger = logging.getLogger(__name__)


def use_memory_fallback(context: str, error: OracleRepositoryError) -> None:
    """Allow explicit demo fallback while making database outages visible."""
    if not settings.app_allow_memory_data:
        raise error
    logger.warning("Oracle unavailable; using volatile memory for %s", context)
