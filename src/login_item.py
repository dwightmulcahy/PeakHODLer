import logging
import subprocess
import sys

from app_info import APP_NAME

logger = logging.getLogger(__name__)

def is_login_item_enabled(app_name: str) -> bool:
    try:
        result = subprocess.run(
            ['osascript', '-e', 'tell application "System Events" to get the name of every login item'],
            capture_output=True, text=True
        )
        return app_name in result.stdout
    except Exception as e:
        logger.error(f"Failed to check login item status: {e}")
        return False

def enable_login_item(app_path: str) -> None:
    try:
        subprocess.run(
            ['osascript', '-e',
             f'tell application "System Events" to make login item at end with properties {{name: "{APP_NAME}", path: "{app_path}", hidden: false}}'],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to enable login item: {e}")

def disable_login_item() -> None:
    try:
        subprocess.run(
            ['osascript', '-e', f'tell application "System Events" to delete login item "{APP_NAME}"'],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to disable login item: {e}")
