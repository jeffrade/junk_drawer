.PHONY: install run dev test clean download-model release help

# Vosk model configuration
VOSK_MODEL := vosk-model-en-us-0.22
VOSK_CACHE_DIR := ~/.cache/vosk

# Default target
all: install

install:
	uv sync

run:
	uv run python -m voice_assistant

dev:
	uv sync --all-extras

test:
	uv run pytest tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache build dist .coverage

download-model:
	uv run python -c "from voice_assistant.utils import get_model_path; get_model_path('$(VOSK_MODEL)', '$(VOSK_CACHE_DIR)')"

release:
	uv run pyinstaller --onefile --name voice-assistant voice_assistant/__main__.py
	@echo ""
	@echo "✓ Executable created: dist/voice-assistant"
	@echo "  Copy to bin: cp dist/voice-assistant ~/.local/bin/"

help:
	@echo "Voice Assistant - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Common usage:"
	@echo "  make install       - Install dependencies"
	@echo "  make run           - Run the voice assistant"
	@echo "  make download-model - Download Vosk model"
	@echo "  make release       - Build single executable"
	@echo "  make clean         - Remove cache files"
	@echo ""
	@echo "For more info, see README.md"