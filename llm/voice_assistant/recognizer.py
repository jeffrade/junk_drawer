"""
Vosk speech recognition integration
"""

import json
import logging
import queue
from pathlib import Path
from typing import Iterator, List, Optional

from vosk import KaldiRecognizer, Model, SetLogLevel

from . import utils

logger = logging.getLogger(__name__)


class RecognizerError(Exception):
    """Raised when recognizer initialization fails"""

    pass


class VoskRecognizer:
    """Manages Vosk speech recognition with wake word and full transcription modes"""

    def __init__(self, model_path: str, sample_rate: int = 16000, confidence_threshold: float = 0.5):
        """
        Initialize Vosk recognizer.

        Args:
            model_path: Path to Vosk model directory
            sample_rate: Sample rate in Hz
            confidence_threshold: Minimum confidence level for accepting recognition (0.0-1.0)
        """
        self.sample_rate = sample_rate
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold

        if not self.model_path.exists():
            raise RecognizerError(f"Model not found at {self.model_path}")

        try:
            logger.info(f"Loading Vosk model from {self.model_path}")
            self.model = Model(str(self.model_path))
            self.recognizer = None
            logger.debug("Vosk model loaded successfully")
        except Exception as e:
            raise RecognizerError(f"Failed to load Vosk model: {e}")

    @staticmethod
    def _extract_text(result_dict: dict) -> tuple[Optional[str], float]:
        """
        Extract text and confidence from Vosk result dict.

        Handles both Result() format {"text": "..."} and
        FinalResult() format {"result": [{"text": "...", "conf": 1.0}]}.

        Returns:
            (text, confidence) tuple
        """
        text = None
        confidence = 1.0

        if "result" in result_dict and result_dict["result"]:
            # FinalResult() format
            text = " ".join([r.get("text", "") for r in result_dict["result"]])
            confidences = [float(r.get("conf", 0)) for r in result_dict["result"]]
            confidence = sum(confidences) / len(confidences) if confidences else 0
        elif "text" in result_dict:
            # Result() format
            text = result_dict.get("text", "")

        return text, confidence

    def _process_recognized_text(
        self, text: str, confidence: float, source: str, json_str: str
    ) -> Iterator[str]:
        """
        Process recognized text, log JSON, and yield if confidence passes.

        Args:
            text: Recognized text
            confidence: Confidence score
            source: "Result" or "FinalResult" for logging
            json_str: Original JSON string from Vosk

        Yields:
            Text if confidence >= threshold
        """
        if not text or not text.strip():
            return

        # Log original JSON for any recognized text
        logger.info(f"Vosk {source} JSON: {json_str}")

        if confidence >= self.confidence_threshold:
            yield text.strip()
        else:
            logger.debug(f"Rejected low confidence: '{text}' (confidence: {confidence:.2f})")

    def recognize_from_queue(
        self,
        audio_queue: queue.Queue,
        grammar: Optional[List[str]] = None,
        partial_results: bool = False,
        should_continue: Optional[callable] = None,
    ) -> Iterator[str]:
        """
        Recognize speech from audio queue.

        Args:
            audio_queue: Queue containing audio chunks
            grammar: Optional list of words for limited vocabulary mode
            partial_results: If True, yield partial results as well
            should_continue: Optional callable that returns False to stop listening

        Yields:
            Recognized text strings
        """
        # Create recognizer for this session
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        logger.debug("Recognizer created")

        consecutive_timeouts = 0

        try:
            while True:
                # Check if should stop listening
                if should_continue is not None and not should_continue():
                    logger.debug("Recognizer stop signal received")
                    break

                try:
                    # Get audio chunk with timeout for responsive keyboard interrupt
                    data = audio_queue.get(timeout=0.1)

                    # Reset timeout counter when we get audio
                    consecutive_timeouts = 0

                    # Process audio chunk
                    result = self.recognizer.AcceptWaveform(data)

                    if result:
                        # Final result from AcceptWaveform
                        result_str = self.recognizer.Result()
                        result_dict = json.loads(result_str)
                        text, confidence = self._extract_text(result_dict)

                        yield from self._process_recognized_text(
                            text, confidence, "Result", result_str
                        )

                    elif partial_results:
                        # Partial result
                        result_str = self.recognizer.PartialResult()
                        result_dict = json.loads(result_str)
                        if "partial" in result_dict and result_dict["partial"]:
                            yield result_dict["partial"]

                except queue.Empty:
                    # Timeout waiting for audio - track consecutive timeouts
                    consecutive_timeouts += 1

                    # After ~1 second of silence (10 * 0.1s timeout), get final result
                    if consecutive_timeouts >= 10:
                        try:
                            result_str = self.recognizer.FinalResult()
                            result_dict = json.loads(result_str)
                            text, confidence = self._extract_text(result_dict)

                            yield from self._process_recognized_text(
                                text, confidence, "FinalResult", result_str
                            )
                        except (json.JSONDecodeError, Exception) as e:
                            logger.debug(f"Error getting FinalResult: {e}")

                        # Reset counter to avoid calling FinalResult again immediately
                        consecutive_timeouts = 0

        except KeyboardInterrupt:
            logger.info("Recognition interrupted by user")
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            raise

    def reset(self) -> None:
        """Reset the recognizer"""
        if self.recognizer:
            del self.recognizer
            self.recognizer = None
        logger.debug("Recognizer reset")

    def get_model_info(self) -> dict:
        """Get information about loaded model"""
        return {
            "path": str(self.model_path),
            "sample_rate": self.sample_rate,
        }
