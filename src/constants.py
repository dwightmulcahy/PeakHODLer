import os


# ========== Constants ==========
API_URL: str = "https://open-api-v4.coinglass.com/api/bull-market-peak-indicator"
DEFAULT_REFRESH_RATE_MINUTES: int = 30
API_KEY_FILE: str = os.path.expanduser("~/.peakhodler_api_key")
REFRESH_RATE_FILE: str = os.path.expanduser("~/.peakhodler_refresh_rate")
COINGLASS_URL: str = "https://www.coinglass.com/bull-market-peak-signals"
APPKIT_NSFLOATINGWINDOWLEVEL: int = 3
