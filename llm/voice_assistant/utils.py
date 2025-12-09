"""
Utility functions for voice assistant
"""

import logging
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional
from urllib.request import urlopen

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """
    Setup application logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)

    # File handler (optional)
    log_dir = Path.home() / ".cache" / "voice-assistant"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "voice-assistant.log"

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logger.debug(f"Logging initialized at {log_file}")


def get_model_path(model_name: str, cache_dir: str) -> Path:
    """
    Get path to Vosk model, downloading if necessary.

    Args:
        model_name: Name of the model (e.g., "vosk-model-small-en-us-0.15")
        cache_dir: Directory to cache models in

    Returns:
        Path to the model directory
    """
    cache_dir = Path(cache_dir).expanduser()
    model_path = cache_dir / model_name

    if model_path.exists():
        logger.debug(f"Found model at {model_path}")
        return model_path

    logger.info(f"Model not found at {model_path}, downloading...")
    download_vosk_model(model_name, str(cache_dir))

    if model_path.exists():
        return model_path

    raise FileNotFoundError(f"Failed to download or locate model: {model_name}")


def download_vosk_model(model_name: str, cache_dir: str) -> None:
    """
    Download Vosk model from GitHub releases.

    Args:
        model_name: Name of the model (e.g., "vosk-model-small-en-us-0.15")
        cache_dir: Directory to save model to
    """
    cache_dir = Path(cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_url = f"https://alphacephei.com/vosk/models/{model_name}.zip"

    model_zip = cache_dir / f"{model_name}.zip"
    model_path = cache_dir / model_name

    # Skip if already exists
    if model_path.exists():
        logger.debug(f"Model already exists at {model_path}")
        return

    try:
        logger.info(f"Downloading {model_name} from {model_url}")
        logger.info("This may take a few minutes...")

        with urlopen(model_url) as response:
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            chunk_size = 8192

            with open(model_zip, "wb") as out_file:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        logger.debug(f"Downloaded {percent:.1f}%")

        logger.info(f"Extracting model to {model_path}")
        with zipfile.ZipFile(model_zip, "r") as zip_ref:
            zip_ref.extractall(cache_dir)

        model_zip.unlink()  # Remove zip file after extraction
        logger.info(f"Model ready at {model_path}")

    except Exception as e:
        if model_zip.exists():
            model_zip.unlink()
        logger.error(f"Failed to download model: {e}")
        raise


def find_whichmic_path() -> Optional[Path]:
    """
    Find whichmic script if available in PATH.

    Returns:
        Path to whichmic script or None if not found
    """
    try:
        result = subprocess.run(
            ["which", "whichmic"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception as e:
        logger.debug(f"Could not find whichmic: {e}")

    return None


def list_audio_devices() -> None:
    """
    List available audio devices for user to choose from.
    """
    try:
        import sounddevice

        logger.info("Available audio devices:")
        logger.info(sounddevice.query_devices())
    except Exception as e:
        logger.error(f"Could not query audio devices: {e}")


def get_open_command() -> str:
    """
    Get the platform-specific command to open applications/URLs.

    Returns:
        Command string: 'open' for macOS/Linux, 'start' for Windows
    """
    if sys.platform == "darwin":
        return "open"
    elif sys.platform == "win32":
        return "start"
    else:
        return "xdg-open"
