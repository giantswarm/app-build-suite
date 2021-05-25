import logging
import subprocess  # nosec: we need it to invoke binaries from system
from typing import List, Any

logger = logging.getLogger(__name__)


def run_and_log(args: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
    logger.info("Running command:")
    logger.info(" ".join(args))
    if "text" not in kwargs:
        kwargs["text"] = True
    run_res = subprocess.run(args, **kwargs)  # nosec
    logger.info(f"Command executed, exit code: {run_res.returncode}.")
    return run_res
