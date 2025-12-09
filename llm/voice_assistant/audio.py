"""
Audio stream management for voice assistant
"""

import logging
import queue
import subprocess
from pathlib import Path
from typing import Optional

import sounddevice as sd
import numpy as np

logger = logging.getLogger(__name__)


class AudioStreamError(Exception):
    """Raised when audio stream initialization fails"""

    pass


class AudioStream:
    """Manages audio input stream using sounddevice"""

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 4096,
        device: Optional[int] = None,
        use_noise_filter: bool = False,
    ):
        """
        Initialize audio stream.

        Args:
            sample_rate: Sample rate in Hz (default 16000 for Vosk)
            chunk_size: Audio chunk size for processing
            device: Audio device ID (None for default)
            use_noise_filter: Enable noise reduction filter
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device = device or self._select_device()
        self.use_noise_filter = use_noise_filter
        self.stream = None
        self.audio_queue = None

    def _select_device(self) -> int:
        """
        Select audio device with intelligent fallback.

        Returns:
            Audio device ID
        """
        # Try default device first
        default_device = sd.default.device
        if default_device[0] is not None:
            logger.debug(f"Using default input device: {default_device[0]}")
            return default_device[0]

        # Try whichmic if available
        whichmic_path = self._find_whichmic()
        if whichmic_path:
            try:
                result = subprocess.run(
                    [str(whichmic_path)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    # Parse whichmic output for device info
                    device_id = None
                    device_path = None

                    for line in result.stdout.split('\n'):
                        if 'Audio detected on device:' in line:
                            device_id = line.split('Audio detected on device:')[1].strip()
                        elif 'Device location:' in line:
                            device_path = line.split('Device location:')[1].strip()

                    if device_id and device_path:
                        # Extract card number from ALSA device ID (e.g., "1,0" -> card "1")
                        # sounddevice uses numeric IDs, not ALSA device strings
                        try:
                            card_num = int(device_id.split(',')[0])
                            logger.info(f"Selected device via whichmic: {device_path} (card {card_num})")
                            # Find sounddevice ID for this ALSA card
                            for i, dev in enumerate(sd.query_devices()):
                                if dev["max_input_channels"] > 0 and card_num in str(i):
                                    logger.debug(f"Mapped ALSA card {card_num} to sounddevice ID {i}")
                                    return i
                            # Fallback to just using the card number as device ID
                            return card_num
                        except (ValueError, IndexError):
                            logger.debug(f"Could not parse whichmic device: {device_id}")
                            return None
            except Exception as e:
                logger.error(f"whichmic failed: {e}")

        # List available devices and raise error
        logger.error("Could not auto-detect audio device")
        self._log_available_devices()
        raise AudioStreamError(
            "No audio device found. Please specify device ID in config.yaml"
        )

    def _find_whichmic(self) -> Optional[Path]:
        """Find whichmic script if available in PATH"""
        try:
            result = subprocess.run(
                ["which", "whichmic"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except Exception:
            pass
        return None

    def _log_available_devices(self) -> None:
        """Log available audio devices for user reference"""
        try:
            devices = sd.query_devices()
            logger.info("Available audio devices:")
            for i, device in enumerate(devices):
                if device["max_input_channels"] > 0:
                    logger.info(f"  Device {i}: {device['name']}")
        except Exception as e:
            logger.error(f"Could not query devices: {e}")

    def start_stream(self) -> queue.Queue:
        """
        Start audio stream and return queue for audio data.

        Returns:
            Queue containing audio chunks
        """
        self.audio_queue = queue.Queue()
        self._chunk_count = 0

        def audio_callback(indata, frames, time_info, status):
            """Callback for audio stream"""
            if status:
                logger.warning(f"Audio callback status: {status}")

            # RawInputStream provides bytes directly
            audio_data = bytes(indata)

            # Log audio data info (chunk count, size)
            self._chunk_count += 1

            # Calculate RMS level for monitoring (convert bytes to int16 then to float)
            audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0
            rms_level = float(np.sqrt(np.mean(audio_float ** 2)))
            queue_size = self.audio_queue.qsize()

            if self._chunk_count % 10 == 0:  # Log every 10th chunk to avoid spam
                logger.debug(f"Audio chunk {self._chunk_count}: size={len(audio_data)} bytes, RMS={rms_level:.4f}, queue_depth={queue_size}")

            # Apply noise filter if enabled
            if self.use_noise_filter:
                audio_data_filtered = self._apply_noise_filter(audio_float)
                # Convert back to int16 bytes
                audio_int16_filtered = np.clip(audio_data_filtered * 32768.0, -32768, 32767).astype(np.int16)
                audio_data = bytes(audio_int16_filtered)

            self.audio_queue.put(audio_data)

        try:
            # Use RawInputStream to get raw bytes directly (matching Vosk example)
            self.stream = sd.RawInputStream(
                device=self.device,
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.chunk_size,
                callback=audio_callback,
            )
            self.stream.start()
            logger.info(f"Audio stream started (device={self.device})")
            return self.audio_queue

        except Exception as e:
            raise AudioStreamError(f"Failed to start audio stream: {e}")

    def stop_stream(self) -> None:
        """Stop the audio stream"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            logger.info("Audio stream stopped")

    def _apply_noise_filter(self, audio_chunk: np.ndarray) -> np.ndarray:
        """
        Apply noise reduction filter to audio chunk.

        This is a stub implementation. Future enhancements could include:
        - Use noisereduce library (pip install noisereduce)
        - Apply spectral subtraction
        - Use bandpass filter for voice frequencies (300-3400 Hz)
        - Implement gate/threshold-based noise removal

        Args:
            audio_chunk: Audio data as numpy array

        Returns:
            Filtered audio data
        """
        # TODO: Implement actual noise reduction
        # For now, return audio as-is
        # Example approaches for future implementation:
        #
        # Option 1: Using noisereduce library
        # import noisereduce as nr
        # return nr.reduce_noise(y=audio_chunk, sr=self.sample_rate)
        #
        # Option 2: Simple energy-based gate
        # energy = np.mean(audio_chunk ** 2)
        # noise_threshold = 0.001
        # if energy < noise_threshold:
        #     return audio_chunk * 0.5  # Attenuate quiet noise
        #
        # Option 3: Bandpass filter for voice
        # from scipy import signal
        # sos = signal.butter(4, [300, 3400], 'bp', fs=self.sample_rate, output='sos')
        # return signal.sosfilt(sos, audio_chunk)

        return audio_chunk

    def get_device_info(self) -> dict:
        """Get information about the current device"""
        try:
            return sd.query_devices(self.device)
        except Exception as e:
            logger.error(f"Could not get device info: {e}")
            return {}
