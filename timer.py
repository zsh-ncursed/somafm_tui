"""Sleep timer module"""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class SleepTimer:
    """Sleep timer for automatic shutdown"""

    end_time: Optional[float] = None  # Unix timestamp

    def set(self, minutes: int) -> None:
        """Set timer for specified minutes from now"""
        self.end_time = time.time() + (minutes * 60)

    def cancel(self) -> None:
        """Cancel active timer"""
        self.end_time = None

    def get_remaining_seconds(self) -> int:
        """Get remaining seconds, 0 if inactive or expired"""
        if self.end_time is None:
            return 0
        remaining = int(self.end_time - time.time())
        return max(0, remaining)

    def is_active(self) -> bool:
        """Check if timer is running"""
        return self.end_time is not None and self.end_time > time.time()

    def format_remaining(self) -> str:
        """Format remaining time as 'MM:SS'"""
        seconds = self.get_remaining_seconds()
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"