"""Tests for executor module"""

import pytest
from voice_assistant.executor import CommandExecutor, ExecutionResult


def test_shell_command_parameter_substitution():
    """Test that shell command parameters are substituted correctly"""
    executor = CommandExecutor(timeout=5)

    command = {
        "type": "shell",
        "command": "echo {message}",
        "parameters": {"message": "Hello World"},
    }

    result = executor.execute(command)

    assert result.success is True
    assert "Hello World" in result.output


def test_shell_command_without_parameters():
    """Test shell command without parameters"""
    executor = CommandExecutor(timeout=5)

    command = {
        "type": "shell",
        "command": "echo 'test'",
    }

    result = executor.execute(command)

    assert result.success is True
    assert "test" in result.output


def test_shell_command_missing_parameter():
    """Test shell command with missing parameter substitution"""
    executor = CommandExecutor(timeout=5)

    command = {
        "type": "shell",
        "command": "echo {undefined}",
        "parameters": {"other": "value"},
    }

    result = executor.execute(command)

    assert result.success is False
    assert "Missing parameter" in result.error


def test_builtin_exit_command():
    """Test built-in exit command"""
    executor = CommandExecutor(timeout=5)

    command = {
        "type": "builtin",
        "command": "exit",
    }

    result = executor.execute(command)

    assert result.success is True
    assert "Goodbye" in result.output


def test_builtin_unknown_command():
    """Test unknown built-in command"""
    executor = CommandExecutor(timeout=5)

    command = {
        "type": "builtin",
        "command": "invalid",
    }

    result = executor.execute(command)

    assert result.success is False
    assert "Unknown" in result.error
