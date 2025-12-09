"""
Safe command execution
"""

import logging
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of command execution"""

    success: bool
    output: str = ""
    error: str = ""


class ExecutorError(Exception):
    """Raised when execution fails"""

    pass


class CommandExecutor:
    """Executes commands safely with error handling"""

    def __init__(self, timeout: int = 30):
        """
        Initialize executor.

        Args:
            timeout: Command execution timeout in seconds
        """
        self.timeout = timeout
        logger.debug(f"Command executor initialized (timeout={timeout}s)")

    def execute(self, command: Dict[str, Any]) -> ExecutionResult:
        """
        Execute a command based on type.

        Args:
            command: Command data with type and parameters

        Returns:
            ExecutionResult with success status and output
        """
        command_type = command.get("type", "shell")

        try:
            if command_type == "builtin":
                return self._execute_builtin(command)
            elif command_type == "python":
                return self._execute_python(command)
            else:  # shell (default)
                return self._execute_shell(command)

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return ExecutionResult(success=False, error=str(e))

    def _execute_shell(self, command: Dict[str, Any]) -> ExecutionResult:
        """
        Execute shell command(s).

        Args:
            command: Command dict with 'commands' or 'command' field, and optional 'parameters' field

        Returns:
            ExecutionResult
        """
        commands = command.get("commands") or [command.get("command")]
        parameters = command.get("parameters", {})

        if not commands:
            return ExecutionResult(success=False, error="No shell command specified")

        all_output = []
        all_errors = []

        for cmd in commands:
            # Substitute parameters in command template
            if parameters:
                try:
                    cmd = cmd.format(**parameters)
                    logger.debug(f"Substituted parameters: {cmd}")
                except KeyError as e:
                    return ExecutionResult(
                        success=False,
                        error=f"Missing parameter in command template: {e}",
                    )

            logger.info(f"Executing shell command: {cmd}")

            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

                if result.stdout:
                    all_output.append(result.stdout)
                if result.stderr:
                    all_errors.append(result.stderr)

                if result.returncode != 0:
                    logger.warning(f"Command returned non-zero exit code: {result.returncode}")
                    if result.stderr:
                        return ExecutionResult(
                            success=False,
                            output="\n".join(all_output),
                            error=result.stderr,
                        )

            except subprocess.TimeoutExpired:
                msg = f"Command timed out after {self.timeout} seconds"
                logger.error(msg)
                return ExecutionResult(
                    success=False,
                    output="\n".join(all_output),
                    error=msg,
                )
            except Exception as e:
                logger.error(f"Shell execution error: {e}")
                return ExecutionResult(
                    success=False,
                    output="\n".join(all_output),
                    error=str(e),
                )

        output = "\n".join(all_output).strip()
        logger.info(f"Command output: {output[:100]}...")
        return ExecutionResult(success=True, output=output)

    def _execute_python(self, command: Dict[str, Any]) -> ExecutionResult:
        """
        Execute Python function.

        Args:
            command: Command dict with 'function' and optional 'module' fields, and 'parameters'

        Returns:
            ExecutionResult
        """
        function_name = command.get("function")
        module_name = command.get("module", "voice_assistant.custom_actions")
        parameters = command.get("parameters", {})

        if not function_name:
            return ExecutionResult(success=False, error="No Python function specified")

        logger.info(f"Executing Python function: {module_name}.{function_name}")

        try:
            # Import the module
            module = __import__(module_name, fromlist=[function_name])
            func = getattr(module, function_name, None)

            if func is None:
                return ExecutionResult(
                    success=False,
                    error=f"Function {function_name} not found in {module_name}",
                )

            # Execute function with parameters
            if parameters:
                logger.debug(f"Passing parameters to function: {parameters}")
                result = func(**parameters)
            else:
                result = func()

            # Convert result to string
            if result is None:
                output = f"Function {function_name} executed successfully"
            else:
                output = str(result)

            logger.info(f"Function output: {output[:100]}...")
            return ExecutionResult(success=True, output=output)

        except ImportError as e:
            msg = f"Could not import module {module_name}: {e}"
            logger.error(msg)
            return ExecutionResult(success=False, error=msg)
        except Exception as e:
            logger.error(f"Python execution error: {e}")
            return ExecutionResult(success=False, error=str(e))

    def _execute_builtin(self, command: Dict[str, Any]) -> ExecutionResult:
        """
        Execute built-in command.

        Args:
            command: Command dict with 'command' field

        Returns:
            ExecutionResult
        """
        builtin_cmd = command.get("command")

        if builtin_cmd == "exit":
            logger.info("Exit command received")
            return ExecutionResult(
                success=True,
                output="Goodbye!",
            )

        return ExecutionResult(
            success=False,
            error=f"Unknown built-in command: {builtin_cmd}",
        )
