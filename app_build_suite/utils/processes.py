import logging
import subprocess  # nosec: we need it to invoke binaries from system
from typing import List, Any

logger = logging.getLogger(__name__)


def run_and_log(args: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
    print_debug = "print_debug" in kwargs and bool(kwargs["print_debug"])
    logger.info("Running command:")
    logger.info(" ".join(args))
    if "text" not in kwargs:
        kwargs["text"] = True
    if "capture_output" not in kwargs:
        kwargs["capture_output"] = True
    if print_debug:
        del kwargs["print_debug"]
    run_res = subprocess.run(args, **kwargs)  # nosec
    if print_debug:
        logger.debug("Command stdout is:")
        for line in run_res.stdout.splitlines():
            logger.debug(line)
    if run_res.stderr:
        logger.info("Command stderr is:")
        for line in run_res.stderr.splitlines():
            logger.info(line)
    else:
        logger.info("Command hasn't printed anything on 'stderr'.")
    logger.info(f"Command executed, exit code: {run_res.returncode}.")
    return run_res
