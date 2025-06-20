import asyncio
import os
import sys
import webbrowser
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Union, TypedDict

import aiohttp
import rumps

import src.constants as constants

from src.app_info import APP_NAME, APP_VERSION
from src.colorlogging import setup_logging
from src.login_item import is_login_item_enabled, disable_login_item, enable_login_item

# Call setup_logging once at the start
logger, log_path = setup_logging(APP_NAME)


# Define a TypedDict for the structure of an indicator item
class IndicatorItem(TypedDict):
    """Represents the structure of an individual indicator returned by the API."""
    name: str
    hit_status: Optional[bool]
    hit: Optional[bool]  # Some APIs might use 'hit' instead of 'hit_status'
    hit_time: Optional[int]  # Unix timestamp in milliseconds


class PeakHODLerStatusApp(rumps.App):
    """
    A macOS menubar application to display the CoinGlass BTC Bull Market Peak Indicator.

    Provides real-time updates, configuration for API key and refresh rate,
    and a list of triggered indicators.
    """

    # Constants for exponential backoff
    MAX_RETRIES: int = 5
    BASE_DELAY: float = 1.0  # seconds for initial retry delay

    def __init__(self) -> None:
        """
        Initializes the BullMarketStatusApp.
        """
        super().__init__("📊 Loading...")

        self.api_key: Optional[str] = self._load_file_content(constants.API_KEY_FILE)
        self.refresh_rate_minutes: int = self._load_refresh_rate()
        # Changed to List[str] as _format_indicator_item returns a string
        self.indicator_list: List[str] = []
        self.last_updated: str = "Never"
        self._update_lock: asyncio.Lock = asyncio.Lock()

        # Initialize menu items
        self.refresh_item: rumps.MenuItem
        self.last_updated_item: rumps.MenuItem
        self.last_updated_data: rumps.MenuItem
        self.triggered_menu: rumps.MenuItem
        self.open_coinglass_item: rumps.MenuItem
        self.set_api_key_item: rumps.MenuItem
        self.set_refresh_rate_item: rumps.MenuItem
        self.about_item: rumps.MenuItem
        self.show_logs_item: rumps.MenuItem
        self.settings_menu: rumps.MenuItem

        self._setup_menu_items()
        self._build_menu()

        # Start the periodic update timer
        self.timer: rumps.Timer = rumps.Timer(self._schedule_update, self.refresh_rate_minutes * 60)
        self.timer.start()

    def _setup_menu_items(self) -> None:
        """Initializes and configures the individual menu items."""
        self.refresh_item = rumps.MenuItem("Refresh Now", callback=self.manual_refresh)
        self.last_updated_item = rumps.MenuItem(f"Last Updated: {self.last_updated}")
        self.last_updated_data = rumps.MenuItem("Not updated yet.")
        self.triggered_menu = rumps.MenuItem("No Triggered Indicators", callback=None)
        self.open_coinglass_item = rumps.MenuItem("Open CoinGlass", callback=self.open_coinglass)

        self.set_api_key_item = rumps.MenuItem("Set API Key...", callback=self.set_api_key)
        self.set_refresh_rate_item = rumps.MenuItem(
            f"Set Refresh Rate ({self.refresh_rate_minutes} min)...", callback=self.set_refresh_rate)
        self.launch_at_login_item = rumps.MenuItem( "Launch at Login" )

        # About menu item
        self.about_item = rumps.MenuItem(f"About {APP_NAME}", callback=self.about_app)
        self.show_logs_item = rumps.MenuItem("Show Log", callback=self.show_log)

        # Settings submenu
        self.settings_menu = rumps.MenuItem("Settings")
        self.settings_menu.add(self.launch_at_login_item)
        self.settings_menu.add(self.set_api_key_item)
        self.settings_menu.add(self.set_refresh_rate_item)

        if not is_login_item_enabled(APP_NAME):
            self.launch_at_login_item.set_callback(self.toggle_launch_at_login)

    def _build_menu(self) -> None:
        """Constructs the application's menubar menu."""
        # Type hints for .add() can be omitted as it's part of rumps' internal structure,
        # but the items themselves are typed in _setup_menu_items.
        self.menu.add(self.last_updated_item)
        self.menu.add(self.last_updated_data)
        self.menu.add(self.refresh_item)
        self.menu.add(None)  # Separator
        self.menu.add(self.open_coinglass_item)
        self.menu.add(self.triggered_menu)
        self.menu.add(None)  # Separator
        self.menu.add(self.settings_menu)
        self.menu.add(self.show_logs_item)
        self.menu.add(None)  # Separator
        self.menu.add(self.about_item)  # Add About item to the main menu
        self.menu.add(None)  # Separator

    @staticmethod
    def _load_file_content(filepath: str) -> Optional[str]:
        """
        Loads content from a specified file.

        Args:
            filepath: The path to the file.

        Returns:
            The stripped content of the file if it exists, otherwise None.
        """
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return f.read().strip()
            except IOError as e:
                logger.error(f"Error reading file {filepath}: {e}")
        return None

    @staticmethod
    def _save_file_content(filepath: str, content: str) -> bool:
        """
        Saves content to a specified file.

        Args:
            filepath: The path to the file.
            content: The string content to write.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with open(filepath, "w") as f:
                f.write(content.strip())
            return True
        except IOError as e:
            logger.error(f"Failed to save content to {filepath}: {e}")
            rumps.alert("Error", f"Failed to save to {os.path.basename(filepath)}.")
            return False

    def _load_api_key(self) -> Optional[str]:
        """Loads the API key from its designated file."""
        return self._load_file_content(constants.API_KEY_FILE)

    def _save_api_key(self, key: str) -> bool:
        """Saves the API key to its designated file."""
        return self._save_file_content(constants.API_KEY_FILE, key)

    def _load_refresh_rate(self) -> int:
        """
        Loads the refresh rate from its designated file, or returns the default.
        """
        rate_str: Optional[str] = self._load_file_content(constants.REFRESH_RATE_FILE)
        if rate_str:
            try:
                return int(rate_str)
            except ValueError:
                logger.warning(f"Invalid refresh rate found in {constants.REFRESH_RATE_FILE}. Using default.")
        return constants.DEFAULT_REFRESH_RATE_MINUTES

    def _save_refresh_rate(self, rate: int) -> bool:
        """Saves the refresh rate to its designated file."""
        return self._save_file_content(constants.REFRESH_RATE_FILE, str(rate))

    @staticmethod
    def toggle_launch_at_login(sender: rumps.MenuItem) -> None:
        app_path = os.path.abspath(sys.argv[0])
        if sender.state:
            disable_login_item()
            sender.state = False
            logger.info("Launch at Login disabled.")
        else:
            enable_login_item(app_path)
            sender.state = True
            logger.info("Launch at Login enabled.")

    # noinspection PyProtectedMember
    @rumps.clicked("Settings", "Set API Key...")
    def set_api_key(self, _sender: rumps.MenuItem) -> None:
        """
        Prompts the user to enter their CoinGlass API key and saves it.

        Args:
            _sender: The MenuItem that triggered this callback (unused, but required by rumps).
        """
        window: rumps.Window = rumps.Window(
            "Enter your CoinGlass API Key:",
            "Set API Key",
            default_text=self.api_key or "",
            ok='OK',
            cancel='Cancel',
        )
        # Hack to assure that the window appears in front
        # Added type: ignore for rumps' internal _alert which is not officially typed
        window._alert.window().setLevel_(constants.APPKIT_NSFLOATINGWINDOWLEVEL)  # type: ignore
        response = window.run()
        if response.clicked != 0:  # OK button was clicked
            new_key: str = response.text.strip()
            if self._save_api_key(new_key):
                self.api_key = new_key
                logger.info("API Key updated. Triggering data refresh.")
                asyncio.run(self.update_data())

    # noinspection PyProtectedMember
    def set_refresh_rate(self, _sender: rumps.MenuItem) -> None:
        """
        Prompts the user to enter a new refresh rate and updates the timer.

        Args:
            _sender: The MenuItem that triggered this callback (unused, but required by rumps).
        """
        window: rumps.Window = rumps.Window(
            "Enter refresh rate in minutes (e.g., 30):",
            "Set Refresh Rate",
            default_text=str(self.refresh_rate_minutes),
            ok='OK',
            cancel='Cancel',
        )
        # Hack to assure that the window appears in front
        window._alert.window().setLevel_(constants.APPKIT_NSFLOATINGWINDOWLEVEL)  # type: ignore
        response = window.run()
        if response.clicked != 0:  # OK button was clicked
            try:
                new_rate: int = int(response.text.strip())
                if new_rate <= 0:
                    rumps.alert("Invalid Input", "Refresh rate must be a positive number.")
                    logger.warning("User entered invalid refresh rate (<= 0).")
                    return

                # Update the refresh interval if a new rate is inputted
                if self.refresh_rate_minutes != new_rate and self._save_refresh_rate(new_rate):
                    self.refresh_rate_minutes = new_rate
                    # Update the menu item title directly
                    self.set_refresh_rate_item.title = f"Set Refresh Rate ({new_rate} min)..."
                    self.timer.stop()
                    self.timer = rumps.Timer(self._schedule_update, self.refresh_rate_minutes * 60)
                    self.timer.start()
                    logger.info(f"Refresh rate updated to {new_rate} minutes. Triggering data refresh.")
            except ValueError:
                rumps.alert("Invalid Input", "Please enter a valid integer for the refresh rate.")
                logger.warning("User entered non-integer refresh rate.")

    @rumps.clicked("Open CoinGlass")
    def open_coinglass(self, _sender: rumps.MenuItem) -> None:
        """
        Opens the CoinGlass website in the default web browser.

        Args:
            _sender: The MenuItem that triggered this callback (unused, but required by rumps).
        """
        logger.info(f"Opening CoinGlass website: {constants.COINGLASS_URL}")
        webbrowser.open(constants.COINGLASS_URL)

    @rumps.clicked("Refresh Now")
    def manual_refresh(self, _sender: rumps.MenuItem) -> None:
        """
        Triggers an immediate manual data refresh.

        Args:
            _sender: The MenuItem that triggered this callback (unused, but required by rumps).
        """
        logger.info("Manual refresh triggered by user.")
        asyncio.run(self.update_data())

    def _schedule_update(self, _sender: rumps.Timer) -> None:
        """
        Callback for the rumps timer to trigger data updates.

        Args:
            _sender: The Timer object that triggered this callback (unused, but required by rumps).
        """
        logger.debug("Scheduled update triggered.")
        asyncio.run(self.update_data())

    async def update_data(self) -> None:
        """
        Asynchronously fetches and updates the bull market status data.

        This method uses an asyncio.Lock to prevent multiple concurrent updates.
        It updates the menubar title, last updated time, and triggered indicators list.
        """
        if self._update_lock.locked():
            logger.warning("An update is already in progress. Skipping this request.")
            return

        async with self._update_lock:
            hold, sell, label, indicators = await self._fetch_hold_sell(self.api_key)
            now_str: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # More precise timestamp
            self.last_updated = now_str
            self.last_updated_item.title = f"Last Updated: {now_str}"

            if hold is None:
                self.title = "🔴 Error"
                logger.error(f"Failed to fetch data. Menubar status set to 'Error'. Reason: {label}")
                rumps.notification("Bull Market Status", "Update Failed", label)
                return

            # Extract emoji from label; handle cases where label might not have one.
            # Updated to be more robust to labels without leading emojis
            emoji_map: Dict[str, str] = {
                "Unwavering": "💎", "Confident": "🛡️", "Watchful": "📈", "Cautious": "🐂",
                "Neutral": "⚖️", "Caution": "⚠️", "Mitigate": "🧯", "Divest": "🏃",
                "Urgent": "🔥", "Liquidate": "🚨"
            }
            current_emoji: str = "📊"  # Default neutral emoji
            label_without_emoji: str = label  # Initialize with full label

            for key, emoji_val in emoji_map.items():
                if label.endswith(key):
                    label_without_emoji = key
                    current_emoji = emoji_val
                    break
            else:
                # If no specific label part is found, and it starts with an emoji, remove it.
                # Otherwise, use the label as is.
                first_char: str = label[0] if label else ''
                if first_char in ["💎", "🛡️", "📈", "🐂", "⚖️", "⚠️", "🧯", "🏃", "🔥", "🚨"]:
                    current_emoji = first_char
                    label_without_emoji = label[2:].strip()  # Remove emoji and space
                # Else: label_without_emoji remains the full original label

            self.title = f"{current_emoji} {label_without_emoji}"

            # Create the message of the indicators that are triggered
            self.indicator_list.clear()
            if indicators:
                self.indicator_list.extend([
                    self._format_indicator_item(item) for item in indicators
                ])
                # Only set callback if there are indicators to show
                self.triggered_menu.set_callback(self.triggered_indicators)
                self.triggered_menu.title = "Triggered Indicators"
                logger.info(f"{len(indicators)} indicators triggered.")
                for indicator in indicators:
                    logger.info(f"{self._format_indicator_item(indicator)}")
            else:
                self.indicator_list.append("✔ None Triggered")
                # Unset callback if no indicators, or potentially keep it with a "None triggered" message
                self.triggered_menu.set_callback(None)
                self.triggered_menu.title = "No Triggered Indicators"
                logger.info("No indicators currently triggered.")

            # Ensured hold and sell are floats before formatting
            self.last_updated_data.title = f"Hold:{hold:.1f}% | Sell:{sell:.1f}% | Signal:{label}"

    @staticmethod
    def _get_sell_label(sell_percent: float) -> str:
        """
        Determines the sentiment label based on the sell percentage.

        Args:
            sell_percent: The calculated percentage of indicators suggesting a 'sell'.

        Returns:
            A string representing the sentiment label, prefixed with an emoji.
        """
        # Using a list of tuples for scale is clear and extensible.
        # Type hints for the tuples enhance readability.
        scale: List[Tuple[int, int, str]] = [
            (0, 9, "💎 Unwavering"),
            (10, 19, "🛡️ Confident"),
            (20, 29, "📈 Watchful"),
            (30, 39, "🐂 Cautious"),
            (40, 49, "⚖️ Neutral"),
            (50, 59, "⚠️ Caution"),
            (60, 69, "🧯 Mitigate"),
            (70, 79, "🏃 Divest"),
            (80, 89, "🔥 Urgent"),
            (90, 100, "🚨 Liquidate"),
        ]
        for low, high, label in scale:
            if low <= sell_percent <= high:
                return label
        return "Unknown"

    @staticmethod
    async def _attempt_fetch_data(session: aiohttp.ClientSession,
                                  headers: Dict[str, str]) -> Tuple[bool, Union[Dict[str, Any], str], Optional[int]]:
        """
        Attempts to fetch data from CoinGlass API once.
        Returns (success: bool, result: Union[Dict[str, Any], str] (json data or error message), status_code: Optional[int]).
        """
        try:
            async with session.get(constants.API_URL, headers=headers) as resp:
                # Check for specific retriable status codes *before* raising for status
                if resp.status in [429, 500, 502, 503, 504]:
                    logger.warning(f"API returned retriable status {resp.status}.")
                    return False, f"API Error: Retriable status {resp.status}", resp.status

                resp.raise_for_status()  # Raises HTTPStatusError for other bad responses (4xx, 5xx)
                json_data: Dict[str, Any] = await resp.json()
                return True, json_data, None

        except aiohttp.ClientResponseError as e:
            # This catches errors raised by resp.raise_for_status() for non-retriable 4xx codes (e.g., 401, 403)
            logger.error(f"HTTP error during single fetch attempt: {e.status} - {e.message}")
            return False, f"HTTP Error ({e.status}): {e.message}", e.status
        except aiohttp.ClientError as e:
            # Catches connection errors, DNS errors, etc. (network errors)
            logger.warning(f"Network error during single fetch attempt: {e}")
            return False, f"Network Error: {e}", None
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"An unexpected error occurred during single fetch attempt: {e}")
            return False, f"Unexpected Error: {e}", None

    async def _fetch_hold_sell(self, api_key: Optional[str] = None) -> \
            Tuple[Optional[float], Optional[float], str, List[dict[str, Any]]]:
        """
        Fetches the bull market peak indicator data from the CoinGlass API with exponential backoff.

        Args:
            api_key: An optional CoinGlass API key for authenticated requests.

        Returns:
            A tuple containing:
            - hold_pct (float or None): The calculated hold percentage.
            - sell_pct (float or None): The calculated sell percentage.
            - label (str): The sentiment label based on sell percentage or an error message.
            - hits (List[IndicatorItem]): A list of triggered indicators.
        """
        headers: Dict[str, str] = {"Accept": "application/json"}
        if api_key:
            headers["cg-api-key"] = api_key

        async with aiohttp.ClientSession() as session:
            for retries in range(self.MAX_RETRIES + 1):  # Loop for 0 to MAX_RETRIES attempts
                if retries > 0:
                    current_delay: float = self.BASE_DELAY * (2 ** (retries - 1))  # Exponential backoff calculation
                    logger.info(f"Retrying API call (attempt {retries}/{self.MAX_RETRIES}). Waiting {current_delay:.1f}s...")
                    await asyncio.sleep(current_delay)  # Wait before retrying
                else:
                    logger.info("Fetching data from CoinGlass API...")

                success, result_or_error_msg, status_code = await self._attempt_fetch_data(session, headers)

                if success and result_or_error_msg["code"] == '200':  # type: ignore
                    json_data: Dict[str, Any] = result_or_error_msg  # type: ignore
                    data: List[Dict[str, Any]] = json_data.get("data", [])
                    total: int = len(data)
                    hits: List[Dict[str, Any]] = [item for item in data if
                                                  item.get("hit_status") is True or item.get("hit") is True]

                    sell_pct: float = (len(hits) / total) * 100 if total else 0.0
                    hold_pct: float = 100.0 - sell_pct
                    label: str = self._get_sell_label(sell_pct)

                    logger.info(f"Hold: {hold_pct:.2f}% | Sell: {sell_pct:.2f}% | Signal: {label}")
                    return round(hold_pct, 2), round(sell_pct, 2), label, hits
                elif result_or_error_msg["code"] == '400':  # type: ignore
                    # Bad API request somehow
                    logger.error(f"Failed API call. Reason: `{result_or_error_msg['msg']}`")  # type: ignore
                    return None, None, str(result_or_error_msg), []
                else:
                    # Handle failure of the attempt
                    # Status_code is None for network errors caught by aiohttp.ClientError
                    if status_code in [429, 500, 502, 503, 504] or status_code is None:
                        # This is a retriable error or network error. Continue to next retry if allowed.
                        if retries < self.MAX_RETRIES:
                            # Logger message already provided by _attempt_fetch_data or the retry sleep line
                            pass
                        else:
                            # Max retries reached for a retriable error
                            logger.error(f"Failed after {self.MAX_RETRIES} retries. Reason: {result_or_error_msg}")
                            return None, None, str(result_or_error_msg), []
                    else:
                        # Non-retriable error (e.g., 401 Unauthorized, 403 Forbidden, invalid URL, etc.)
                        logger.error(f"Non-retriable error. Reason: {result_or_error_msg}")
                        return None, None, str(result_or_error_msg), []

        # This part should ideally not be reached if MAX_RETRIES is handled correctly within the loop
        logger.error("Unexpected exit from _fetch_hold_sell retry loop.")
        return None, None, "Unknown Error After All Retries", []

    @staticmethod
    def _format_indicator_item(item: Dict[str, Any]) -> str:
        """Helper to format a single indicator item for display."""
        name: str = item.get("name", "Unknown Indicator")
        hit_time_ms: Optional[int] = item.get("hit_time")
        if hit_time_ms:
            try:
                # Convert milliseconds to seconds for datetime.fromtimestamp
                dt_object: datetime = datetime.fromtimestamp(hit_time_ms / 1000)
                formatted_time: str = dt_object.strftime('%b %d %H:%M')
                return f"✔ {name} @ {formatted_time}"
            except (TypeError, ValueError) as e:
                logger.error(f"Error converting hit_time {hit_time_ms} for indicator {name}: {e}")
                return f"✔ {name} (Invalid Time)"
        return f"✔ {name}"

    def triggered_indicators(self, _sender: rumps.MenuItem) -> None:
        """
        Displays a list of all currently triggered bull market indicators.

        Args:
            _sender: The MenuItem that triggered this callback (unused, but required by rumps).
        """
        if not self.indicator_list:
            msg: str = "No indicators have been triggered yet."
        else:
            msg = "\n".join(self.indicator_list)
        rumps.alert("Triggered Indicators", msg)

    @rumps.clicked(f"About {APP_NAME}")  # The decorator for the new About menu item
    def about_app(self, _sender: rumps.MenuItem) -> None:
        """
        Displays an About box for the application.

        Args:
            _sender: The MenuItem that triggered this callback.
        """
        rumps.alert(
            title=f"About {APP_NAME}",
            message=(
                f"{APP_NAME} v{APP_VERSION}\n\n"
                "A macOS menubar application to display the CoinGlass BTC Bull Market Peak Indicator.\n\n"
                "Data provided by CoinGlass.\n"
                "© 2025 dWiGhT. All rights reserved."
            ),
            ok='Close'
        )
        logger.info("About dialog displayed.")

    # noinspection PyProtectedMember
    @staticmethod
    def show_log(_sender: rumps.MenuItem) -> None:
        logger.info("Attempting to show application log...")
        log_content: str = "Log file not found or empty."
        try:
            with open(log_path, 'r', encoding="utf-8") as f:
                lines: List[str] = f.readlines()
                log_content = "".join(lines[-20:])
            logger.info(f"Successfully read log file: {log_path}")
        except FileNotFoundError:
            logger.error(f"Log file not found at: {log_path}")
            log_content = f"Error: Log file not found at {log_path}"
        except Exception as e:
            logger.error(f"Error reading log file: {e}", exc_info=True)
            log_content = f"Error reading log file: {e}"

        # Use rumps.Window for scrollable text
        # The 'default_text' parameter provides a scrollable text input field
        try:
            window: rumps.Window = rumps.Window(
                message="Application Log",
                title=f"{APP_NAME} App Log",
                default_text=log_content,
                ok='Close',
                dimensions=(700, 360)
            )
            window._alert.window().setLevel_(constants.APPKIT_NSFLOATINGWINDOWLEVEL)  # type: ignore
            window.run()
            logger.info("Application log window displayed.")
        except Exception as e:
            logger.error(f"Error displaying log window: {e}", exc_info=True)
            rumps.alert(title="Error!", message=f"Could not display log window: {e}")


if __name__ == "__main__":
    logger.info("Starting Bull Market Status App.")
    PeakHODLerStatusApp().run()
    logger.info("Stopping Bull Market Status App.")