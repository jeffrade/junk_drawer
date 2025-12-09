"""Tests for config module"""

import tempfile
from pathlib import Path

import pytest
import yaml

from voice_assistant.config import Config, ConfigError


def test_config_load_default():
    """Test loading default config file"""
    config = Config()

    assert config.get_wake_words() == ["claudia", "scotty"]
    assert config.get_audio_config()["sample_rate"] == 16000
    assert config.get_execution_timeout() == 30


def test_config_get_match_threshold():
    """Test getting match threshold"""
    config = Config()

    threshold = config.get_match_threshold()
    assert 0.0 <= threshold <= 1.0


def test_config_get_confidence_threshold():
    """Test getting confidence threshold"""
    config = Config()

    threshold = config.get_confidence_threshold()
    assert 0.0 <= threshold <= 1.0


def test_config_invalid_threshold():
    """Test invalid threshold values"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "test_config.yaml"
        config_data = {
            "wake_words": ["test"],
            "match_threshold": 1.5,  # Invalid: > 1.0
            "commands": [],
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = Config(str(config_file))
        # Should use default (0.75) for invalid value
        assert config.get_match_threshold() == 0.75


def test_config_missing_file():
    """Test loading non-existent config file"""
    with pytest.raises(ConfigError):
        Config("/nonexistent/path/config.yaml")


def test_config_commands():
    """Test loading commands from config"""
    config = Config()

    commands = config.get_commands()
    assert len(commands) > 0
    assert all("phrases" in cmd for cmd in commands)
    assert all("action" in cmd for cmd in commands)
