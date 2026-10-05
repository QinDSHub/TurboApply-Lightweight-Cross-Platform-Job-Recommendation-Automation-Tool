import logging
import sys
from pathlib import Path

def setup_logging(level=logging.INFO, log_file="logs/run.log"):
      Path(log_file).parent.mkdir(exist_ok=True)
      fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-5s | %(message)s",
            datefmt = "%H:%M:%S",
      )

      root = logging.getLogger()
      root.setLevel(logging.DEBUG)
      root.handlers.clear()

      console = logging.StreamHandler(sys.stdout)
      console.setLevel(logging.INFO)
      console.setFormatter(fmt)
      root.addHandler(console)

      file = logging.FileHandler(log_file, encoding='utf-8')
      file.setLevel(logging.DEBUG)
      file.setFormatter(fmt)
      root.addHandler(file)