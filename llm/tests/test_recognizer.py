"""
Tests for VoskRecognizer
"""

import pytest
from voice_assistant.recognizer import VoskRecognizer, RecognizerError


class TestExtractText:
    """Test the _extract_text static method that handles both Vosk JSON formats"""

    def test_extract_text_result_format(self):
        """Test extraction from Result() format: {"text": "..."}"""
        result_dict = {"text": "scotty"}
        text, confidence = VoskRecognizer._extract_text(result_dict)

        assert text == "scotty"
        assert confidence == 1.0

    def test_extract_text_result_format_empty(self):
        """Test extraction from Result() format with empty text"""
        result_dict = {"text": ""}
        text, confidence = VoskRecognizer._extract_text(result_dict)

        assert text == ""
        assert confidence == 1.0

    def test_extract_text_finalresult_format_single_entry(self):
        """Test extraction from FinalResult() format with single entry"""
        result_dict = {"result": [{"text": "claudia", "conf": 1.0}]}
        text, confidence = VoskRecognizer._extract_text(result_dict)

        assert text == "claudia"
        assert confidence == 1.0

    def test_extract_text_finalresult_format_multiple_entries(self):
        """Test extraction from FinalResult() format with multiple entries"""
        result_dict = {
            "result": [
                {"text": "hello", "conf": 0.9},
                {"text": "world", "conf": 0.8},
            ]
        }
        text, confidence = VoskRecognizer._extract_text(result_dict)

        # Should join with space
        assert text == "hello world"
        # Should average confidence
        assert confidence == pytest.approx(0.85, abs=0.01)

    def test_extract_text_finalresult_empty_result(self):
        """Test extraction from FinalResult() with empty result array"""
        result_dict = {"result": []}
        text, confidence = VoskRecognizer._extract_text(result_dict)

        assert text is None
        assert confidence == 1.0  # Default confidence when no result array to process

    def test_extract_text_finalresult_missing_conf(self):
        """Test extraction handles missing confidence values"""
        result_dict = {"result": [{"text": "hello"}]}
        text, confidence = VoskRecognizer._extract_text(result_dict)

        assert text == "hello"
        # Default confidence for missing "conf" is 0
        assert confidence == 0

    def test_extract_text_no_recognized_text(self):
        """Test extraction when neither format has text"""
        result_dict = {"unknown": "value"}
        text, confidence = VoskRecognizer._extract_text(result_dict)

        assert text is None
        assert confidence == 1.0

    def test_extract_text_partial_result(self):
        """Test extraction from partial result (not handled by _extract_text but should return None)"""
        result_dict = {"partial": "scot"}
        text, confidence = VoskRecognizer._extract_text(result_dict)

        # _extract_text only handles "text" and "result" keys
        assert text is None
        assert confidence == 1.0
