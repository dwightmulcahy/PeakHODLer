import os
from dataclasses import dataclass
import typing as t

# `frozen=True` makes the instance immutable after creation.
@dataclass(frozen=True, kw_only=True)
class AppConstants:
    """
    A class for strictly enforcing immutability of constants using dataclasses.
    """
    API_URL: str
    DEFAULT_REFRESH_RATE_MINUTES: int
    API_KEY_FILE: str
    REFRESH_RATE_FILE: str
    COINGLASS_URL: str
    APPKIT_NSFLOATINGWINDOWLEVEL: int

const: AppConstants = AppConstants(
    API_URL="https://open-api-v4.coinglass.com/api/bull-market-peak-indicator",
    DEFAULT_REFRESH_RATE_MINUTES=30,
    API_KEY_FILE=os.path.expanduser("~/.peakhodler_api_key"),
    REFRESH_RATE_FILE=os.path.expanduser("~/.peakhodler_refresh_rate"),
    COINGLASS_URL="https://www.coinglass.com/bull-market-peak-signals",
    APPKIT_NSFLOATINGWINDOWLEVEL=3,
)
