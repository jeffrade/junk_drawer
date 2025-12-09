"""
Wake word detection using Vosk
"""

import logging
import queue
from typing import Iterator, List

from .recognizer import VoskRecognizer

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Detects wake words and switches to command mode"""

    def __init__(self, recognizer: VoskRecognizer, wake_words: List[str]):
        """
        Initialize wake word detector.

        Args:
            recognizer: VoskRecognizer instance
            wake_words: List of wake word phrases
        """
        self.recognizer = recognizer
        self.wake_words = [w.lower().strip() for w in wake_words]

        if not self.wake_words:
            raise ValueError("At least one wake word is required")

        logger.debug(f"Wake word detector initialized with: {self.wake_words}")

    def listen(self, audio_queue: queue.Queue) -> bool:
        """
        Listen for wake words.

        Args:
            audio_queue: Queue containing audio chunks

        Returns:
            True if wake word detected, False if interrupted
        """
        logger.info(f"Listening for wake words: {self.wake_words}")

        try:
            for text in self.recognizer.recognize_from_queue(audio_queue):
                if text:
                    text_lower = text.lower().strip()
                    logger.debug(f"Detected: {text}")

                    # Check if any wake word is in the recognized text
                    for wake_word in self.wake_words:
                        if wake_word in text_lower:
                            logger.info(f"Wake word detected: '{wake_word}'")
                            return True

        except KeyboardInterrupt:
            logger.info("Wake word listening interrupted")
            return False
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
            raise

        return False

    def wait_for_wake_word(self, audio_queue: queue.Queue) -> Iterator[bool]:
        """
        Continuously listen for wake words, yielding when detected.

        Args:
            audio_queue: Queue containing audio chunks

        Yields:
            True when wake word detected
        """
        while True:
            if self.listen(audio_queue):
                yield True
