"""
Configuration management for voice assistant
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration is invalid"""

    pass


class Config:
    """Load and validate configuration from YAML file"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config.yaml. If None, uses default in llm/ directory
        """
        if config_path is None:
            # Use default config.yaml in project directory
            config_path = Path(__file__).parent.parent / "config.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        self.config_path = config_path
        self.config = self._load_yaml()
        self._validate()

    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
                if config is None:
                    config = {}
                return config
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse YAML: {e}")
        except IOError as e:
            raise ConfigError(f"Failed to read configuration: {e}")

    def _validate(self) -> None:
        """Validate configuration structure"""
        # Check required fields
        if not self.get_wake_words():
            logger.warning("No wake words configured. Using default: ['hey assistant']")
            if "wake_words" not in self.config:
                self.config["wake_words"] = []
            if not self.config["wake_words"]:
                self.config["wake_words"] = ["hey assistant"]

        # Validate commands structure
        commands = self.get_commands()
        for i, cmd in enumerate(commands):
            if "phrases" not in cmd:
                raise ConfigError(f"Command {i} missing 'phrases' field")
            if "action" not in cmd:
                raise ConfigError(f"Command {i} missing 'action' field")
            if not isinstance(cmd["phrases"], list):
                raise ConfigError(f"Command {i} 'phrases' must be a list")
            if not cmd["phrases"]:
                raise ConfigError(f"Command {i} has empty phrases list")

    def get_wake_words(self) -> List[str]:
        """Get list of wake words"""
        wake_words = self.config.get("wake_words", [])
        if isinstance(wake_words, list):
            return wake_words
        return [wake_words] if wake_words else []

    def get_audio_config(self) -> Dict[str, Any]:
        """Get audio configuration"""
        default_audio = {
            "sample_rate": 16000,
            "device": None,
            "noise_filter": False,
        }
        audio_config = self.config.get("audio", {})
        default_audio.update(audio_config)
        return default_audio

    def get_vosk_config(self) -> Dict[str, Any]:
        """Get Vosk configuration"""
        default_vosk = {
            "model": "vosk-model-small-en-us-0.15",
            "cache_dir": os.path.expanduser("~/.cache/vosk"),
        }
        vosk_config = self.config.get("vosk", {})
        default_vosk.update(vosk_config)
        return default_vosk

    def get_commands(self) -> List[Dict[str, Any]]:
        """Get list of configured commands"""
        return self.config.get("commands", [])

    def get_execution_timeout(self) -> int:
        """Get command execution timeout in seconds"""
        return self.config.get("execution_timeout", 30)

    def get_match_threshold(self) -> float:
        """Get fuzzy matching threshold (0.0 - 1.0)"""
        threshold = self.config.get("match_threshold", 0.75)
        if not 0.0 <= threshold <= 1.0:
            logger.warning(f"Invalid match_threshold {threshold}, using 0.75")
            threshold = 0.75
        return threshold

    def get_confidence_threshold(self) -> float:
        """Get speech recognition confidence threshold (0.0 - 1.0)"""
        threshold = self.config.get("confidence_threshold", 0.5)
        if not 0.0 <= threshold <= 1.0:
            logger.warning(f"Invalid confidence_threshold {threshold}, using 0.5")
            threshold = 0.5
        return threshold
