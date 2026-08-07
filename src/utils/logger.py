import os
import sys
import logging

# Ensure UTF-8 output on Windows streams
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Enable ANSI colors on Windows Terminal / PowerShell / CMD
if sys.platform == "win32":
    os.system("")

class ColoredFormatter(logging.Formatter):
    """
    Custom Logging Formatter to add ANSI colors to timestamps, log levels, and logger names.
    """
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD_RED = "\033[1;31m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"

    LEVEL_COLORS = {
        logging.DEBUG: CYAN,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def format(self, record):
        # Colorize timestamp (Cyan)
        asctime = f"{self.CYAN}{self.formatTime(record, '%Y-%m-%d %H:%M:%S')}{self.RESET}"
        
        # Colorize log level (Green for INFO, Yellow for WARN, Red for ERROR)
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        levelname = f"{color}[{record.levelname}]{self.RESET}"
        
        # Colorize logger name (Magenta)
        name = f"{self.MAGENTA}{record.name}{self.RESET}"
        
        # Format full message line
        message = record.getMessage()
        return f"{asctime} {levelname} {name}: {message}"

# Initialize global logger
logger = logging.getLogger("ELT_Pipeline")
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
