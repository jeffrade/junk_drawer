# Voice Assistant - Vosk-Based Voice-to-CLI Automation Tool

A simple, modular Python voice assistant that listens for wake words, recognizes voice commands, and executes CLI actions. Built with Vosk for offline speech recognition.

## Features

- **Offline Speech Recognition**: Uses Vosk for 100% offline STT (no cloud dependency)
- **Wake Word Detection**: Continuously listens and only processes commands after detecting configured wake words
- **Voice Command Execution**: Map voice phrases to shell commands, Python functions, or built-in actions
- **Fuzzy Matching**: Handles minor variations in spoken commands
- **Parameter Extraction**: Extract variables from voice commands (e.g., "open Firefox")
- **Noise Filtering**: Optional experimental noise reduction (configurable via flag)
- **Smart Audio Device Detection**: Multi-tier fallback to find working microphone
- **Safe Execution**: Timeout handling, error capture, no arbitrary code execution

## Requirements

- Python 3.9 or later
- Audio input device (microphone)
- OS-specific audio system:
  - **Linux**: ALSA or PulseAudio
  - **macOS**: Core Audio (built-in)
  - **Windows**: WASAPI (built-in)

### Optional

- `whichmic` script (Linux only, for microphone detection but not required)

## Installation

### 0. Prerequisites

- Install PortAudio
```
# Ubuntu/Debian
sudo apt-get install libportaudio2

# Fedora/RHEL
sudo dnf install portaudio-devel

# Arch
sudo pacman -S portaudio
```

### 1. Install Python Dependencies

```bash
cd /home/jrade/code/junk_drawer/llm
make install
```

This installs all dependencies in an isolated virtual environment using Astral's `uv`.

### 2. Download Vosk Model (Automatic or Manual)

Models will be downloaded automatically on first run to `~/.cache/vosk/`.

To manually download the default model:

```bash
make download-model
```

## Configuration

Edit `config.yaml` to customize:

- **Wake words**: Phrases to trigger command mode (e.g., "Claudia" or "Scotty")
- **Audio device**: Microphone selection (auto-detected if not specified)
- **Voice commands**: Map speech phrases to actions
- **Execution timeout**: Maximum time for commands to run
- **Fuzzy matching threshold**: How strict phrase matching should be

### Basic Config Structure

The default `config.yaml` includes example commands:

```yaml
wake_words:
  - "claudia"
  - "scotty"

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

## Usage

### Basic Usage

```bash
# Run the voice assistant
make run
```

### Advanced Options

After running `make install`, you can use additional flags:

**With Noise Filtering**:
```bash
uv run python -m voice_assistant --noise-filter
```

**With Custom Configuration**:
```bash
uv run python -m voice_assistant --config custom_config.yaml
```

**With Verbose Logging**:
```bash
uv run python -m voice_assistant --verbose
```

**Combine Flags**:
```bash
uv run python -m voice_assistant --config custom.yaml --noise-filter --verbose
```

### Typical Workflow

1. **Start the assistant**:
   ```bash
   make run
   ```

2. **Wait for "Waiting for wake word..."**

3. **Say a wake word**:
   ```
   You: "Claudia"
   System: " Wake word detected"
   System: "Listening for command..."
   ```

4. **Say a command**:
   ```
   You: "What time is it"
   System: "You said: what time is it"
   System: "Executing: Display current time"
   System:  Command executed successfully

   02:45 PM
   ```

5. **Repeat or exit**:
   ```
   You: "goodbye"
   System: "Exit command received"
   System: "Shutting down Voice Assistant..."
   System: "Goodbye!"
   ```

## Adding New Voice Commands

Edit `config.yaml` and add a new command entry:

### Simple Shell Command

```yaml
- phrases:
    - "show system status"
    - "system info"
  action:
    type: "shell"
    command: "uname -a && uptime"
  description: "Display system information"
```

### Command with Parameters

Extract variables from voice input:

```yaml
- phrases:
    - "search for {query}"
    - "google {query}"
  action:
    type: "shell"
    command: "xdg-open 'https://www.google.com/search?q={query}'"
  description: "Search Google"
```

Usage:
```
You: "search for python tutorial"
� Opens: https://www.google.com/search?q=python+tutorial
```

### Multiple Commands in Sequence

```yaml
- phrases:
    - "update system"
  action:
    type: "shell"
    commands:
      - "apt update"
      - "apt upgrade -y"
  description: "Update system packages"
```

### Python Function

Create a Python module with callable functions:

**File: `voice_assistant/custom_actions.py`**

```python
"""Custom voice command actions"""

def get_weather():
    """Fetch and return weather information"""
    import subprocess
    result = subprocess.run(
        ["curl", "-s", "wttr.in"],
        capture_output=True,
        text=True
    )
    return result.stdout
```

**Add to `config.yaml`**:

```yaml
- phrases:
    - "what is the weather"
    - "tell me the weather"
  action:
    type: "python"
    function: "get_weather"
    module: "voice_assistant.custom_actions"
  description: "Get weather information"
```

## Configuration Details

### Wake Words

```yaml
wake_words:
  - "claudia"  # Exact phrases to listen for
  - "scotty"
```

### Audio Configuration

```yaml
audio:
  sample_rate: 16000      # Vosk standard (do not change)
  device: null            # null = auto-detect, or device ID (int)
  noise_filter: false     # Enable noise reduction (experimental)
```

To find your device ID:

```bash
# List audio devices
python -c "import sounddevice; print(sounddevice.query_devices())"

# Then set in config:
audio:
  device: 2  # Use device 2 (index from list above)
```

### Vosk Model

```yaml
vosk:
  model: "vosk-model-small-en-us-0.15"  # Model name
  cache_dir: "~/.cache/vosk"             # Where to store models
```

Available models:
- `vosk-model-small-en-us-0.15` (40MB, recommended)
- `vosk-model-en-us-0.22` (1.8GB, higher accuracy)

**To use a different model:**

1. Update in `config.yaml`:
   ```yaml
   vosk:
     model: "vosk-model-en-us-0.22"  # Change to desired model
   ```

2. (Optional) Update the Makefile variable to change the default for `make download-model`:
   ```makefile
   # Edit Makefile, lines 4-5:
   VOSK_MODEL := vosk-model-en-us-0.22
   VOSK_CACHE_DIR := ~/.cache/vosk
   ```

For a complete list of available Vosk models, see: https://alphacephei.com/vosk/models#model-list

### Execution Settings

```yaml
execution_timeout: 30      # Max seconds for command execution
match_threshold: 0.75      # Fuzzy matching strictness (0.0-1.0)
```

Fuzzy matching threshold:
- **0.75 (default)**: Allow small variations ("what's the time" vs "what time is it")
- **0.9**: Stricter matching
- **0.5**: Very permissive (may match unintended commands)

## Platform-Specific Configuration

The voice assistant works on Linux, macOS, and Windows, but some commands need to be adjusted per platform.

### Opening Applications

The default example uses `xdg-open` (Linux). Update for your OS:

**Linux:**
```yaml
- phrases:
    - "open {application}"
  action:
    type: "shell"
    command: "xdg-open {application}"
  description: "Open application"
```

**macOS:**
```yaml
- phrases:
    - "open {application}"
  action:
    type: "shell"
    command: "open -a {application}"
  description: "Open application"
```

**Windows:**
```yaml
- phrases:
    - "open {application}"
  action:
    type: "shell"
    command: "start {application}"
  description: "Open application"
```

### Time/Date Commands

Time formatting differs by OS:

**Linux/macOS:**
```yaml
command: "date '+%I:%M %p'"
```

**Windows (PowerShell):**
```yaml
command: "powershell -Command \"Get-Date -Format 'HH:mm tt'\""
```

### System Information

**Linux:**
```yaml
command: "uname -a && uptime && df -h / && free -h"
```

**macOS:**
```yaml
command: "uname -a && uptime && df -h / && vm_stat"
```

**Windows:**
```yaml
command: "systeminfo && disk usage && Get-WmiObject Win32_OperatingSystem"
```

## Recent Improvements

### Recognition Latency (Session 2)
- **Previous behavior**: Recognition took 20+ seconds
- **Current behavior**: Recognition completes in 1-2 seconds
- **How it works**: Calls FinalResult() only once after ~1 second of silence, rather than repeatedly during timeouts

### Parameter Extraction Improvements (Session 2)
- **Previous behavior**: Parameters only extracted when phrase was at the start of recognized text
- **Current behavior**: Parameters extract correctly even with noise/filler words before the phrase
- **Example**: Saying "the echo hello world" now correctly executes with `{text}` = "hello world"

## Troubleshooting

### Audio Device Not Found

If you get "Could not auto-detect audio device":

1. List available devices:
   ```bash
   python -c "import sounddevice; print(sounddevice.query_devices())"
   ```

2. Find a device with `max_input_channels > 0` (input device)

3. Set in `config.yaml`:
   ```yaml
   audio:
     device: 2  # Your device ID
   ```

4. Test the device:
   ```bash
   make run
   ```

### Speech Not Being Recognized

1. **Check microphone volume**:
   ```bash
   alsamixer  # Adjust levels with arrow keys
   ```

2. **Test microphone directly**:
   ```bash
   # Record 3 seconds of audio
   arecord -d 3 test.wav
   aplay test.wav  # Play back to verify
   ```

3. **Enable verbose logging**:
   ```bash
   # After running `make install`:
   uv run python -m voice_assistant --verbose
   ```

4. **Check log file**:
   ```bash
   tail -f ~/.cache/voice-assistant/voice-assistant.log
   ```

### Model Download Fails

1. Check internet connection
2. Try manual download:
   ```bash
   mkdir -p ~/.cache/vosk
   cd ~/.cache/vosk
   # Replace URL with your model
   wget https://alphacephei.com/vosk/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   ```

### Wake word not detected

1. **Adjust fuzzy matching threshold** in `config.yaml`:
   ```yaml
   match_threshold: 0.65  # More permissive
   ```

2. **Try different wake words**:
   ```yaml
   wake_words:
     - "claudia"  # Default names
     - "scotty"
   ```

3. **Enable noise filter**:
   ```bash
   # After running `make install`:
   uv run python -m voice_assistant --noise-filter
   ```

## Commands Reference

### Makefile Commands

```bash
make install         # Install dependencies (uv sync)
make run            # Run the voice assistant
make dev            # Install with dev dependencies
make test           # Run all 24 unit tests
make clean          # Remove cache and compiled files
make download-model # Download default Vosk model
make help           # Show this help message
```

### Direct Commands

These use `uv run` directly (only needed if you prefer not to use Makefile or need custom flags):

```bash
# First ensure dependencies are installed:
make install

# Then use any of these:

# Basic run (prefer: make run)
uv run python -m voice_assistant

# With noise filtering
uv run python -m voice_assistant --noise-filter

# With custom config
uv run python -m voice_assistant --config my_config.yaml

# Verbose mode
uv run python -m voice_assistant --verbose

# All options combined
uv run python -m voice_assistant --config config.yaml --noise-filter --verbose
```

## Architecture

### Components

1. **audio.py** - Audio stream capture with sounddevice
   - Multi-tier device detection
   - Optional noise filtering stub
   - Queue-based audio delivery

2. **recognizer.py** - Vosk speech recognition
   - Model loading and caching
   - Audio-to-text conversion
   - Partial and final result handling

3. **wake_word.py** - Wake word detection
   - Listens for configured phrases
   - Triggers command mode

4. **command_mapper.py** - Command parsing and matching
   - Fuzzy phrase matching
   - Parameter extraction from voice
   - Command lookup

5. **executor.py** - Safe command execution
   - Shell command execution with timeout
   - Python function invocation
   - Error handling and output capture

6. **config.py** - Configuration management
   - YAML file parsing
   - Schema validation
   - Setting retrieval with defaults

7. **__main__.py** - Application orchestration
   - Component initialization
   - Main event loop
   - Signal handling

### Data Flow

```
Microphone
    �
Audio Stream (audio.py)
    �
Vosk Recognizer (recognizer.py)
    �
Wake Word Detector (wake_word.py)
    �
Command Mapper (command_mapper.py)
    �
Command Executor (executor.py)
    �
CLI Command / Output
```

## Advanced Usage

### Custom Python Actions

Create `voice_assistant/custom_actions.py`:

```python
"""Custom voice command actions"""

def play_music(genre: str = "jazz"):
    """Play music by genre"""
    import subprocess
    subprocess.run(["spotify", "--play", f"genre:{genre}"])
    return f"Playing {genre} music"

def get_weather():
    """Fetch weather information"""
    import subprocess
    result = subprocess.run(
        ["curl", "-s", "wttr.in"],
        capture_output=True,
        text=True
    )
    return result.stdout
```

Then in `config.yaml`:

```yaml
- phrases:
    - "play {genre} music"
  action:
    type: "python"
    function: "play_music"
    module: "voice_assistant.custom_actions"
  description: "Play music by genre"

- phrases:
    - "weather"
    - "what's the weather"
  action:
    type: "python"
    function: "get_weather"
    module: "voice_assistant.custom_actions"
  description: "Get weather information"
```

### Implementing Noise Filtering

The `audio.py` file has a stub for noise filtering. To implement:

```python
def _apply_noise_filter(self, audio_chunk):
    # Option 1: Use noisereduce library
    import noisereduce as nr
    return nr.reduce_noise(y=audio_chunk, sr=self.sample_rate)

    # Option 2: Bandpass filter for voice (300-3400 Hz)
    from scipy import signal
    sos = signal.butter(4, [300, 3400], 'bp', fs=self.sample_rate, output='sos')
    return signal.sosfilt(sos, audio_chunk)
```

### Extending for MCP Server Integration

The modular architecture supports future MCP server integration:

```python
# Future MCP server could expose these tools:
- execute_voice_command(command: str)
- list_available_commands()
- start_listening()
- stop_listening()
```

Each module has clean interfaces for tool wrapping.

## Logging

Logs are written to `~/.cache/voice-assistant/voice-assistant.log` and console.

View logs:

```bash
# Real-time monitoring
tail -f ~/.cache/voice-assistant/voice-assistant.log

# All logs with timestamps
cat ~/.cache/voice-assistant/voice-assistant.log
```

## License

This project is provided as-is for voice automation and educational purposes.

## Contributing

To add features or improvements:

1. Update `config.yaml` with test configurations
2. Test voice commands thoroughly
3. Check logs for errors: `~/.cache/voice-assistant/voice-assistant.log`

## Future Enhancements

- [ ] Text-to-speech feedback via `espeak` or similar
- [ ] Noise reduction filter implementation
- [ ] Multi-language support
- [ ] MCP server integration for Claude Code
- [ ] Command chaining and scripting
- [ ] Machine learning-based wake word detection
- [ ] Audio visualization/metrics

## About the Wake Word Names

**Claudia** is named after Claude, Anthropic's large language model, which serves as the intellectual foundation and inspiration for this voice automation tool.

**Scotty** is named after Édouard-Léon Scott de Martinville, the French inventor of the phonautograph (1857), one of the first sound recording devices and a pioneering technology in audio capture and voice recognition.
