# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
NFC configuration settings for TheOpenMusicBox.
"""

from dataclasses import dataclass


@dataclass
class NFCConfig:
    """
    Configuration parameters for NFC hardware and detection logic.

    This is the single source of truth for all NFC-related settings.
    """

    # Hardware settings
    read_timeout: float = 0.1  # Timeout for NFC read operations in seconds
    retry_delay: float = 0.1  # Delay between read retries in seconds
    max_retries: int = 3  # Maximum number of read retries

    # Tag detection settings
    tag_cooldown: float = 0.5  # Cooldown period after tag detection
    tag_removal_threshold: float = 1.0  # Time to confirm tag removal
    max_errors: int = 3  # Max consecutive errors before reset
    debounce_time: float = 0.2  # Debounce time for tag detection

    # Playback control
    manual_action_priority_window: float = 1.0  # Window for manual actions to override NFC
    pause_threshold: float = 3.0  # Time before auto-pause triggers
    auto_resume_delay: float = 0.5  # Delay before auto-resume after tag detected

    # Auto-pause configuration
    auto_pause_enabled: bool = True  # Enable automatic pause on tag removal
    auto_resume_enabled: bool = True  # Enable automatic resume on tag detection

    # NFC hardware interface
    use_spi: bool = False  # Use SPI interface (False = I2C)
    i2c_bus: int = 1  # I2C bus number
    i2c_address: int = 0x24  # NFC reader I2C address

    # Mock NFC settings for simulation
    mock_scan_frequency: int = 50  # Frequency of simulated scans (every N cycles)
    mock_scan_interval: float = 0.1  # Interval between scan cycles in seconds
    mock_detection_interval: float = 5.0  # Interval for simulated tag detection in seconds
    mock_detection_window: float = 0.1  # Window of opportunity for tag detection

    def validate(self) -> None:
        """
        Validate NFC configuration values.
        """
        if self.read_timeout <= 0:
            raise ValueError(f"read_timeout must be positive, got {self.read_timeout}")

        if self.retry_delay <= 0:
            raise ValueError(f"retry_delay must be positive, got {self.retry_delay}")

        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative, got {self.max_retries}")

        if self.tag_cooldown < 0:
            raise ValueError(f"tag_cooldown must be non-negative, got {self.tag_cooldown}")

        if self.pause_threshold < 0:
            raise ValueError(f"pause_threshold must be non-negative, got {self.pause_threshold}")
