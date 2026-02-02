# Uses qcp_global_utils
import os

from logging import getLogger, basicConfig
logger = getLogger(__name__)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

basicConfig(
    level=log_level,
    # format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    format="%(message)s",
)
# warn and info
warn= lambda msg: logger.warning(f"WARNING: {msg}")
info= lambda msg: logger.info(f"INFO: {msg}")
debug= lambda msg: logger.debug(f"DEBUG: {msg}")