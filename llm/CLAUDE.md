# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**Junk Drawer** is a personal collection of utilities and experiments. The primary component is **Voice Assistant** (`llm/`), a production-quality Python voice automation system that uses Vosk for offline speech-to-text recognition and executes CLI commands or Python functions based on voice input.

## Primary Project: Voice Assistant

### Quick Start

```bash
cd llm
make install          # Install dependencies (uv)
make download-model   # Get Vosk speech model
make run             # Start the voice assistant
```

### Key Dependencies

- **Python 3.9+** with `uv` package manager
- **Vosk** (v0.3.45+) - Offline speech-to-text via Kaldi
- **sounddevice** (v0.4.6+) - Cross-platform audio capture
- **PyYAML**, **RapidFuzz**, **NumPy** - Config, fuzzy matching, audio processing
- **Black** (formatter), **Ruff** (linter) - Code quality (line-length: 100)
- **pytest** - Testing framework

### Build and Test Commands

```bash
make install         # Install dependencies (uv sync)
make run            # Run voice assistant with verbose logging
make dev            # Install with dev dependencies (black, ruff, pytest, pyinstaller)
make test           # Run pytest on tests/
make clean          # Remove __pycache__, *.pyc, build artifacts
make download-model # Download default Vosk model to ~/.cache/vosk
make release        # Build single-file executable with PyInstaller
```

### Running Individual Tests

```bash
cd llm
make install
# Run all tests:
uv run pytest tests/

# Run specific test file:
uv run pytest tests/test_config.py -v

# Run single test:
uv run pytest tests/test_command_mapper.py::test_fuzzy_matching -v
```

### Code Style

- **Formatter**: Black (100 char line limit)
- **Linter**: Ruff (100 char line limit)
- Both configured in `llm/pyproject.toml`
- Run formatting: `black llm/voice_assistant` (if Black is installed)
- Run linting: `ruff check llm/voice_assistant` (if Ruff is installed)

## Architecture

### Core Modules (llm/voice_assistant/)

| Module | Purpose |
|--------|---------|
| `__main__.py` | Application entry point, main event loop, SIGINT/SIGTERM handling |
| `audio.py` | Audio capture via sounddevice, multi-tier device detection, RMS monitoring |
| `recognizer.py` | Vosk integration for speech-to-text, confidence scoring |
| `wake_word.py` | Wake word detection (currently stubbed) |
| `command_mapper.py` | Fuzzy phrase matching (RapidFuzz), parameter extraction via regex |
| `executor.py` | Safe shell/Python/built-in command execution with timeout |
| `config.py` | YAML parsing, validation, configuration schema |
| `utils.py` | Logging setup, Vosk model download, audio device listing |

### Data Flow

```
Microphone → AudioStream (capture, device detection)
          → VoskRecognizer (audio → text, confidence filtering)
          → Main loop (wake word + command detection)
          → CommandMapper (fuzzy match with params)
          → CommandExecutor (shell/Python/built-in)
          → Output (console/next cycle)
```

### Key Design Patterns

1. **Offline-First**: Uses Vosk (Kaldi) instead of cloud APIs. Models cached in `~/.cache/vosk/`.
2. **Queue-Based Pipeline**: Audio stream → queue → recognizer decouples capture from processing.
3. **Fuzzy Matching**: RapidFuzz for command recognition with configurable thresholds.
4. **Safe Execution**: Timeouts, output capture, no arbitrary code execution (explicit Python imports only).
5. **Multi-Tier Device Detection**: Default → whichmic script → error list (handles Linux ALSA/PulseAudio, macOS Core Audio, Windows WASAPI).
6. **Configuration-Driven**: All voice commands and settings in `config.yaml`.

## Configuration (llm/config.yaml)

Essential sections:

```yaml
wake_words:              # Phrases to trigger command mode
  - "claudia"
  - "scotty"

audio:
  sample_rate: 16000     # Vosk standard, do not change
  device: null           # null = auto-detect, or device ID (int)
  noise_filter: false    # Experimental noise reduction

vosk:
  model: "vosk-model-small-en-us-0.15"  # Default 40MB model
  cache_dir: "~/.cache/vosk"             # Model storage

execution_timeout: 30                    # Max seconds per command
match_threshold: 0.75                    # Fuzzy match strictness (0.0-1.0)
confidence_threshold: 0.5                # Speech confidence (0.0-1.0)

commands:
  - phrases:
      - "what time is it"
    action:
      type: "shell"
      command: "date '+%I:%M %p'"
    description: "Display current time"

  - phrases:
      - "open {application}"
    action:
      type: "shell"
      command: "xdg-open {application}"
    description: "Open an application"
```

### Command Types

1. **Shell**: Single command or list of commands
   ```yaml
   action:
     type: "shell"
     command: "date"
     # OR
     commands:
       - "apt update"
       - "apt upgrade -y"
   ```

2. **Python Function**: Dynamic module import
   ```yaml
   action:
     type: "python"
     module: "voice_assistant.custom_actions"
     function: "get_weather"
   ```

3. **Built-in**: Currently only "exit"
   ```yaml
   action:
     type: "builtin"
     command: "exit"
   ```

### Parameter Extraction

Voice phrases can include placeholders that extract variables:

```yaml
- phrases:
    - "search for {query}"
  action:
    type: "shell"
    command: "xdg-open 'https://www.google.com/search?q={query}'"
```

When spoken "search for python tutorial", `{query}` becomes "python tutorial".

## Development Workflow

### Adding a Voice Command

1. Edit `llm/config.yaml` - add new entry to `commands` list
2. Test by running `make run` and speaking the command
3. Check logs: `tail -f ~/.cache/voice-assistant/voice-assistant.log`

### Creating Custom Python Actions

1. Create `llm/voice_assistant/custom_actions.py` with callable functions
2. Add to `config.yaml` with `type: "python"`, module and function names
3. Example:
   ```python
   def get_weather():
       """Fetch weather"""
       import subprocess
       result = subprocess.run(["curl", "-s", "wttr.in"], capture_output=True, text=True)
       return result.stdout
   ```

### Testing

```bash
cd llm
make test                                  # Run all tests
uv run pytest tests/test_config.py -v     # Specific test file
uv run pytest tests/test_command_mapper.py::test_fuzzy_matching -v  # Single test
```

Test files:
- `tests/test_config.py` - Configuration loading/validation
- `tests/test_command_mapper.py` - Fuzzy matching, parameter extraction (5 tests)
- `tests/test_executor.py` - Command execution safety
- `tests/test_recognizer.py` - Vosk JSON parsing, static method testing (8 tests)

Total: 24 tests passing

## Recent Fixes and Improvements (Session 2)

### Wake Word Recognition Latency
- **Issue**: Recognition took 20+ seconds due to repeated FinalResult() calls during silence
- **Fix**: Implemented consecutive timeout counter - calls FinalResult() only once after ~1 second of sustained silence (10 × 0.1s timeouts)
- **File**: `llm/voice_assistant/recognizer.py:125-179`
- **Result**: Latency reduced from 20+ seconds to ~1-2 seconds

### Parameter Extraction in Noisy Speech
- **Issue**: Parameters like `{text}` weren't extracted when speech had noise before the phrase (e.g., "the echo hello world")
- **Root cause**: Used `re.match()` which requires pattern at string start
- **Fix**: Changed to `re.search()` to find pattern anywhere in text
- **File**: `llm/voice_assistant/command_mapper.py:143-182`
- **Example**: "the echo hello" now correctly extracts `{text}` = "hello"

### Code Quality and Testability
- Refactored `_extract_text()` to `@staticmethod` for isolation and testability
- Added 8 comprehensive recognizer unit tests covering:
  - Result() format: `{"text": "..."}`
  - FinalResult() format: `{"result": [{"text": "...", "conf": 1.0}]}`
  - Edge cases: empty results, missing confidence, partial results
- Added test for parameter extraction with prefix noise
- All tests pass, no mocking needed (pure logic testing)

## Special Notes

### Vosk Models

- **Default**: `vosk-model-small-en-us-0.15` (40MB, recommended)
- **Alternative**: `vosk-model-en-us-0.22` (1.8GB, higher accuracy)
- Models auto-download to `~/.cache/vosk/` on first run or via `make download-model`
- To switch models, update `config.yaml` `vosk.model` field

### Audio Device Configuration

Find your device:
```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

Look for entries with `max_input_channels > 0`. Set in `config.yaml`:
```yaml
audio:
  device: 2  # Your device ID
```

### Logging

- Console: INFO level (DEBUG with `--verbose` flag)
- File: Always DEBUG, stored at `~/.cache/voice-assistant/voice-assistant.log`
- Monitor: `tail -f ~/.cache/voice-assistant/voice-assistant.log`

### Cross-Platform Commands

Some shell commands differ by OS. Adjust `config.yaml` accordingly:

**Opening Applications:**
- Linux: `xdg-open {app}`
- macOS: `open -a {app}`
- Windows: `start {app}`

**Time Display:**
- Linux/macOS: `date '+%I:%M %p'`
- Windows: `powershell -Command "Get-Date -Format 'HH:mm tt'"`

## Auxiliary Components

- `bin/` - Standalone utilities (ASCII table, Bitcoin price/news, microphone detection)
- `ruby/install.sh` - Ruby environment setup
- `raspberrypi/setup.sh` - RaspberryPi OS + pi-hole installer

These are less critical and documented minimally.

## Performance and Security Considerations

- **Command Execution**: Uses `timeout` and `subprocess` with output capture. Shell=True (required for piping, though vectored for safety).
- **Python Imports**: Explicit module/function specification (no eval/exec).
- **Audio**: Processed locally, no cloud transmission.
- **Confidence Thresholds**: Both speech recognition and fuzzy matching have configurable filters.

## Future Enhancements (from README)

- [ ] Text-to-speech feedback (espeak)
- [ ] Noise reduction filter implementation
- [ ] Multi-language support
- [ ] MCP server integration for Claude Code
- [ ] Command chaining and scripting
- [ ] Machine learning-based wake word detection

## Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Microphone not found | Run `python -c "import sounddevice; print(sounddevice.query_devices())"` and set device ID in config |
| Speech not recognized | Check mic volume (alsamixer), test with `arecord -d 3 test.wav`, enable --verbose |
| Model download fails | Check internet; manually download from https://alphacephei.com/vosk/models#model-list |
| Wake word not detected | Lower `match_threshold` in config, try different wake words |
| Command times out | Increase `execution_timeout` in config, check if command works in shell |

## Git Workflow

The human manages all git commits and pushes. Claude Code will show changes via `git diff` and `git log`.
