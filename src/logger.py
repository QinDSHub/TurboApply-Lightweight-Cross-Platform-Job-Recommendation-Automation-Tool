import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "logs" / "run.log"


def setup_logging(level=logging.INFO):
    """Configure the root logger with console and file handlers.

    The root logger is set to ``DEBUG`` level and its existing handlers are
    cleared first. A console handler is added at the given ``level``, and a
    file handler is added at ``DEBUG`` level writing to ``LOG_FILE``. Both
    handlers share the same format and timestamp style.

    Args:
        level (int, optional): Minimum log level for the console handler.
            Defaults to ``logging.INFO``.

    Returns:
        None
    """
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    file = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(fmt)
    root.addHandler(file)