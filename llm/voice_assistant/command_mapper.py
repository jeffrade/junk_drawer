"""
Command mapping and fuzzy matching
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


@dataclass
class Command:
    """Represents a voice command"""

    phrases: List[str]
    action_type: str  # "shell", "python", "builtin"
    action_data: Dict[str, Any]
    description: str
    confidence: float = 0.0  # Fuzzy match confidence
    parameters: Dict[str, str] = None  # Extracted parameters from voice input


class CommandMapper:
    """Maps recognized text to configured commands"""

    def __init__(self, commands: List[Dict[str, Any]], threshold: float = 0.75):
        """
        Initialize command mapper.

        Args:
            commands: List of command definitions from config
            threshold: Fuzzy matching threshold (0.0 - 1.0)
        """
        self.commands = self._parse_commands(commands)
        self.threshold = threshold
        logger.debug(f"Command mapper initialized with {len(self.commands)} commands")
        logger.debug(f"Fuzzy matching threshold: {threshold}")

    def _parse_commands(self, commands: List[Dict[str, Any]]) -> List[Command]:
        """Parse command definitions from config"""
        parsed = []

        for cmd_config in commands:
            phrases = cmd_config.get("phrases", [])
            action = cmd_config.get("action", {})
            description = cmd_config.get("description", "Unknown")

            action_type = action.get("type", "shell")

            if action_type == "builtin":
                action_data = {"command": action.get("command")}
            elif action_type == "python":
                action_data = {
                    "function": action.get("function"),
                    "module": action.get("module"),
                }
            else:  # shell (default)
                # Handle both single command and multiple commands
                if "command" in action:
                    action_data = {"commands": [action["command"]]}
                elif "commands" in action:
                    action_data = {"commands": action["commands"]}
                else:
                    logger.warning(f"Command without action data: {description}")
                    continue

            cmd = Command(
                phrases=[p.lower().strip() for p in phrases],
                action_type=action_type,
                action_data=action_data,
                description=description,
            )
            parsed.append(cmd)

        return parsed

    def parse_command(self, text: str) -> Optional[Command]:
        """
        Parse and match recognized text to a command.

        Args:
            text: Recognized speech text

        Returns:
            Matched Command with confidence score, or None if no match
        """
        text_lower = text.lower().strip()

        best_match = None
        best_score = 0.0
        best_params = {}

        # Try each command
        for cmd in self.commands:
            # Check each phrase in the command
            for phrase in cmd.phrases:
                # Try multiple matching strategies
                score = max(
                    fuzz.token_set_ratio(text_lower, phrase) / 100.0,  # Token set matching
                    fuzz.partial_ratio(text_lower, phrase) / 100.0,    # Partial matching
                )

                extracted_params = {}
                # Handle parameter extraction
                if "{" in phrase and "}" in phrase:
                    extracted = self._extract_parameters(text_lower, phrase)
                    if extracted:
                        score = 1.0  # Perfect match with parameters
                        extracted_params = extracted

                if score > best_score:
                    best_score = score
                    best_params = extracted_params
                    best_match = Command(
                        phrases=cmd.phrases,
                        action_type=cmd.action_type,
                        action_data=cmd.action_data,
                        description=cmd.description,
                        confidence=score,
                        parameters=extracted_params if extracted_params else None,
                    )

        # Only return if above threshold
        if best_match and best_score >= self.threshold:
            logger.info(f"Command matched: {best_match.description} ({best_score:.2%})")
            if best_match.parameters:
                logger.debug(f"Extracted parameters: {best_match.parameters}")
            return best_match

        if best_match:
            logger.debug(
                f"Command '{best_match.description}' below threshold "
                f"({best_score:.2%} < {self.threshold:.2%})"
            )

        logger.warning(f"No command matched for: {text}")
        return None

    def _extract_parameters(self, text: str, phrase_template: str) -> Optional[Dict[str, str]]:
        """
        Extract parameters from text using phrase template.

        Args:
            text: Recognized text
            phrase_template: Command phrase with {param} placeholders

        Returns:
            Dict of extracted parameters, or None if extraction fails
        """
        # Convert template to regex pattern
        param_names = re.findall(r"\{(\w+)\}", phrase_template)
        if not param_names:
            return None

        # Replace {param} with regex capture groups
        regex_pattern = re.escape(phrase_template)

        for i, param in enumerate(param_names):
            # Use non-greedy for all but the last parameter
            if i < len(param_names) - 1:
                capture_group = r"(.+?)"
            else:
                # Last parameter: greedy match to end of phrase (not end of string)
                capture_group = r"(.+)"

            regex_pattern = regex_pattern.replace(f"\\{{{param}\\}}", capture_group, 1)

        # Try to match anywhere in the text (use search, not match)
        try:
            match = re.search(regex_pattern, text, re.IGNORECASE)
            if match:
                params = {name: value.strip() for name, value in zip(param_names, match.groups())}
                logger.debug(f"Extracted parameters: {params}")
                return params
        except Exception as e:
            logger.debug(f"Parameter extraction failed: {e}")

        return None

    def get_command_list(self) -> List[str]:
        """Get list of all available commands"""
        return [cmd.description for cmd in self.commands]

    def get_phrases_for_command(self, command_description: str) -> List[str]:
        """Get all phrases for a specific command"""
        for cmd in self.commands:
            if cmd.description == command_description:
                return cmd.phrases
        return []
