"""Tests for command_mapper module"""

import pytest
from voice_assistant.command_mapper import CommandMapper


def test_parameter_extraction():
    """Test that parameters are extracted from voice input"""
    commands = [
        {
            "phrases": ["open {application}"],
            "action": {"type": "shell", "command": "xdg-open {application}"},
            "description": "Open application",
        }
    ]

    mapper = CommandMapper(commands, threshold=0.75)
    command = mapper.parse_command("open waterfox")

    assert command is not None
    assert command.parameters == {"application": "waterfox"}
    assert command.description == "Open application"


def test_parameter_extraction_multiple():
    """Test extraction of multiple parameters"""
    commands = [
        {
            "phrases": ["search {engine} for {query}"],
            "action": {"type": "shell", "command": "xdg-open 'https://{engine}/search?q={query}'"},
            "description": "Search",
        }
    ]

    mapper = CommandMapper(commands, threshold=0.5)
    command = mapper.parse_command("search google for python tutorial")

    assert command is not None
    assert "engine" in command.parameters
    assert "query" in command.parameters


def test_no_parameters():
    """Test command without parameters"""
    commands = [
        {
            "phrases": ["what time is it"],
            "action": {"type": "shell", "command": "date '+%I:%M %p'"},
            "description": "Tell time",
        }
    ]

    mapper = CommandMapper(commands, threshold=0.75)
    command = mapper.parse_command("what time is it")

    assert command is not None
    assert command.parameters is None
    assert command.description == "Tell time"


def test_fuzzy_matching():
    """Test fuzzy matching of commands"""
    commands = [
        {
            "phrases": ["what time is it"],
            "action": {"type": "shell", "command": "date"},
            "description": "Tell time",
        }
    ]

    mapper = CommandMapper(commands, threshold=0.6)
    # Similar but not exact match
    command = mapper.parse_command("what's the time")

    assert command is not None
    assert command.description == "Tell time"


def test_parameter_extraction_with_prefix():
    """Test parameter extraction when phrase appears in middle of text"""
    commands = [
        {
            "phrases": ["echo {text}"],
            "action": {"type": "shell", "command": "echo {text}"},
            "description": "Echo text to terminal",
        }
    ]

    mapper = CommandMapper(commands, threshold=0.7)
    # Text has "the " before "echo {text}"
    command = mapper.parse_command("the echo the")

    assert command is not None
    assert command.parameters == {"text": "the"}
    assert command.description == "Echo text to terminal"
