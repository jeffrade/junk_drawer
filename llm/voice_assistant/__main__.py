"""
Voice Assistant - Main application entry point
"""

import argparse
import logging
import signal
import sys
from pathlib import Path

from .audio import AudioStream, AudioStreamError
from .command_mapper import CommandMapper
from .config import Config, ConfigError
from .executor import CommandExecutor
from .recognizer import VoskRecognizer, RecognizerError
from .utils import setup_logging, get_model_path

logger = logging.getLogger(__name__)


class VoiceAssistantError(Exception):
    """General voice assistant error"""

    pass


class VoiceAssistant:
    """Main voice assistant application"""

    def __init__(self, config_path: str = None, use_noise_filter: bool = False, verbose: bool = False):
        """
        Initialize voice assistant.

        Args:
            config_path: Path to config.yaml
            use_noise_filter: Enable noise filtering
            verbose: Enable verbose logging
        """
        # Setup logging
        log_level = "DEBUG" if verbose else "INFO"
        setup_logging(log_level)

        logger.info("Initializing Voice Assistant...")

        # Load configuration
        try:
            self.config = Config(config_path)
            logger.info(f"Configuration loaded from {self.config.config_path}")
        except ConfigError as e:
            logger.error(f"Configuration error: {e}")
            raise VoiceAssistantError(f"Failed to load configuration: {e}")

        # Get configuration settings
        audio_config = self.config.get_audio_config()
        vosk_config = self.config.get_vosk_config()

        # Override noise filter from CLI if specified
        if use_noise_filter:
            audio_config["noise_filter"] = True
            logger.info("Noise filtering enabled via CLI flag")

        # Setup Vosk model
        try:
            model_path = get_model_path(
                vosk_config["model"],
                vosk_config["cache_dir"],
            )
            logger.info(f"Using Vosk model: {vosk_config['model']}")
        except Exception as e:
            logger.error(f"Failed to get Vosk model: {e}")
            raise VoiceAssistantError(f"Model setup failed: {e}")

        # Initialize components
        try:
            self.audio_stream = AudioStream(
                sample_rate=audio_config["sample_rate"],
                device=audio_config.get("device"),
                use_noise_filter=audio_config.get("noise_filter", False),
            )
            logger.debug("Audio stream initialized")

            self.recognizer = VoskRecognizer(
                model_path=str(model_path),
                sample_rate=audio_config["sample_rate"],
                confidence_threshold=self.config.get_confidence_threshold(),
            )
            logger.debug("Vosk recognizer initialized")

            self.command_mapper = CommandMapper(
                commands=self.config.get_commands(),
                threshold=self.config.get_match_threshold(),
            )
            logger.debug("Command mapper initialized")

            self.executor = CommandExecutor(
                timeout=self.config.get_execution_timeout(),
            )
            logger.debug("Command executor initialized")

        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise VoiceAssistantError(f"Initialization failed: {e}")

        self.running = False
        logger.info("Voice Assistant initialized successfully")

    def run(self) -> None:
        """Run the main voice assistant loop"""
        self.running = True
        logger.info("Starting voice assistant...")
        logger.info(f"Listening for wake words: {self.config.get_wake_words()}")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            # Start audio stream
            audio_queue = self.audio_stream.start_stream()

            while self.running:
                try:
                    # Wait for wake word
                    logger.info("Waiting for wake word...")
                    self._listen_for_wake_word(audio_queue)

                    if not self.running:
                        break

                    # Reset recognizer and audio stream for command mode
                    self.recognizer.reset()
                    self.audio_stream.stop_stream()
                    audio_queue = self.audio_stream.start_stream()

                    # Listen for command
                    logger.info("Listening for command...")
                    if not self._listen_for_command(audio_queue):
                        # User said exit
                        break

                except KeyboardInterrupt:
                    logger.info("Interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    # Restart
                    continue

        except AudioStreamError as e:
            logger.error(f"Audio stream error: {e}")
            raise VoiceAssistantError(f"Audio error: {e}")
        finally:
            self.shutdown()

    def _listen_for_wake_word(self, audio_queue) -> None:
        """
        Listen for wake word in audio stream.

        Args:
            audio_queue: Queue containing audio chunks
        """
        self.recognizer.reset()
        wake_words = self.config.get_wake_words()

        for text in self.recognizer.recognize_from_queue(audio_queue, should_continue=lambda: self.running):
            if text:
                text_lower = text.lower().strip()
                logger.debug(f"Detected text: {text}")

                # Check if any wake word is in the recognized text
                for wake_word in wake_words:
                    if wake_word.lower() in text_lower:
                        logger.info(f"✓ Wake word detected: '{wake_word}'")
                        return

    def _listen_for_command(self, audio_queue) -> bool:
        """
        Listen for and execute voice command.

        Args:
            audio_queue: Queue containing audio chunks

        Returns:
            True to continue, False to exit
        """
        for text in self.recognizer.recognize_from_queue(audio_queue, should_continue=lambda: self.running):
            if text:
                logger.info(f"You said: {text}")

                # Parse command
                command = self.command_mapper.parse_command(text)

                if command:
                    # Check for exit command
                    if command.action_type == "builtin" and command.action_data.get("command") == "exit":
                        logger.info("Exit command received")
                        return False

                    # Execute command
                    logger.info(f"Executing: {command.description}")
                    execute_dict = {
                        "type": command.action_type,
                        **command.action_data,
                    }
                    if command.parameters:
                        execute_dict["parameters"] = command.parameters
                    result = self.executor.execute(execute_dict)

                    if result.success:
                        logger.info("✓ Command executed successfully")
                        if result.output:
                            print(f"\n{result.output}\n")
                    else:
                        logger.error(f"✗ Command failed: {result.error}")
                        if result.output:
                            print(f"\n{result.output}\n")

                    return True
                else:
                    logger.info("Command not recognized, please try again")
                    logger.info("Returning to command listening mode...")
                    return True

        # Timeout without recognition or interrupted by user
        if not self.running:
            return False
        logger.info("No command recognized (timeout)")
        return True

    def _signal_handler(self, signum, frame) -> None:
        """Handle interrupt signals"""
        logger.info("Received interrupt signal, shutting down...")
        self.running = False

    def shutdown(self) -> None:
        """Shutdown the assistant"""
        logger.info("Shutting down Voice Assistant...")
        try:
            self.audio_stream.stop_stream()
        except Exception as e:
            logger.warning(f"Error stopping audio stream: {e}")
        logger.info("Goodbye!")


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Vosk-based voice-to-CLI automation tool",
    )
    parser.add_argument(
        "--config",
        help="Path to config.yaml",
        default=None,
    )
    parser.add_argument(
        "--noise-filter",
        action="store_true",
        help="Enable noise reduction filter",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    try:
        assistant = VoiceAssistant(
            config_path=args.config,
            use_noise_filter=args.noise_filter,
            verbose=args.verbose,
        )
        assistant.run()
    except VoiceAssistantError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
