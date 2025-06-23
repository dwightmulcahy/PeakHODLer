import logging
import subprocess
import sys
import os
import plistlib  # For reading Info.plist from .app bundles

logger = logging.getLogger(__name__)


class LoginItemManager:
   """
   Manages macOS Login Items for the application.

   This class automatically detects if the application is running as a
   .app bundle or a standalone Python script and configures itself accordingly.
   It can enable, disable, and check the status of the application as a login item.
   """

   def __init__(self, app_name: str | None = None):
      """
      Initializes the LoginItemManager.

      It determines the application's type (app bundle or script) and its path.
      If 'app_name' is not provided, it attempts to derive it intelligently
      from the .app bundle's Info.plist or the script's filename.

      Args:
          app_name: The desired name for the login item. This should ideally
                    match the application's display name for .app bundles,
                    or the script's name for standalone scripts.
                    If None, the class will attempt to derive it.
      """
      self._is_app_bundle = self._detect_app_bundle()
      self._app_path = self._determine_application_path()

      if self._app_path is None:
         raise RuntimeError("Could not determine application path. Cannot proceed with LoginItemManager.")

      if app_name:
         self._app_name = app_name
      else:
         self._app_name = self._derive_app_name_from_path()
         if not self._app_name:
            raise ValueError("Could not determine a suitable APP_NAME. Please provide one explicitly.")

      if not self._app_name:  # Final check after derivation attempt
         raise ValueError("APP_NAME could not be determined or was empty.")

   def _detect_app_bundle(self) -> bool:
      """
      Detects if the current execution is within a macOS .app bundle.
      This is typically true if the executable path or any parent directory
      ends with '.app'.
      """
      # Prioritize checking sys.executable for bundled apps
      path_to_check = os.path.abspath(sys.executable)

      # Traverse up from sys.executable
      while path_to_check and path_to_check != os.path.dirname(path_to_check):
         if path_to_check.endswith('.app'):
            return True
         path_to_check = os.path.dirname(path_to_check)

      # If not found via sys.executable, check __file__ (for cases where __file__ might be deeper
      # in a bundle than sys.executable, or for development within a bundle structure)
      path_to_check = os.path.abspath(__file__)
      while path_to_check and path_to_check != os.path.dirname(path_to_check):
         if path_to_check.endswith('.app'):
            return True
         path_to_check = os.path.dirname(path_to_check)

      return False

   def _determine_application_path(self) -> str | None:
      """
      Determines the correct application path for macOS login items.
      Returns the .app bundle path if detected, otherwise the script's absolute path.
      """
      if self._is_app_bundle:
         current_path = os.path.abspath(sys.executable)
         while current_path and current_path != os.path.dirname(current_path):
            if current_path.endswith('.app'):
               return current_path
            current_path = os.path.dirname(current_path)

         # This case should ideally not be reached if _is_app_bundle is True
         # but serves as a fallback.
         logger.warning(f"Detected as app bundle but could not find .app root. Using sys.executable: {sys.executable}")
         return os.path.abspath(sys.executable)
      else:
         return os.path.abspath(__file__)

   def _derive_app_name_from_path(self) -> str:
      """
      Derives a suitable application name based on the detected app type and path.
      For .app bundles, it attempts to read CFBundleDisplayName from Info.plist.
      For scripts, it uses the script's filename.
      """
      if self._is_app_bundle:
         info_plist_path = os.path.join(self._app_path, 'Contents', 'Info.plist')  # type: ignore
         if os.path.exists(info_plist_path):
            try:
               with open(info_plist_path, 'rb') as fp:
                  plist_data = plistlib.load(fp)
                  # Prefer CFBundleDisplayName, fallback to CFBundleName
                  return plist_data.get('CFBundleDisplayName') or plist_data.get('CFBundleName') or os.path.basename(  # type: ignore
                     self._app_path).replace('.app', '')
            except Exception as e:
               logger.warning(
                  f"Could not read Info.plist for '{self._app_path}'. Error: {e}. Falling back to bundle name.")
         return os.path.basename(self._app_path).replace('.app', '')  # type: ignore
      else:
         return os.path.basename(self._app_path)  # type: ignore

   def is_login_item_enabled(self) -> bool:
      """
      Checks if the application is currently listed as a login item.

      Returns:
          True if the login item is enabled, False otherwise.
      """
      try:
         result = subprocess.run(
            ['osascript', '-e', 'tell application "System Events" to get the name of every login item'],
            capture_output=True, text=True, check=True, encoding='utf-8'  # Specify encoding
         )
         # osascript output for login items is often a comma-separated string: "App1, App2, App3"
         login_items = [item.strip() for item in result.stdout.split(',') if item.strip()]
         return self._app_name in login_items
      except subprocess.CalledProcessError as e:
         logger.error(f"osascript failed to check login item status. Stderr: {e.stderr.strip()}")
         return False
      except Exception as e:
         logger.error(f"An unexpected error occurred while checking login item status: {e}")
         return False

   def enable_login_item(self) -> bool:
      """
      Enables the application as a login item.

      Returns:
          True if the login item was successfully enabled, False otherwise.
      """
      if not self._app_path:
         logger.error("Application path not determined, cannot enable login item.")
         return False

      try:
         # Ensure path is properly quoted in AppleScript for spaces/special chars
         escaped_app_path = self._app_path.replace('"', '\\"')
         escaped_app_name = self._app_name.replace('"', '\\"')

         script = (
            f'tell application "System Events" to make login item at end '
            f'with properties {{name: "{escaped_app_name}", path: "{escaped_app_path}", hidden: false}}'
         )

         subprocess.run(
            ['osascript', '-e', script],
            check=True,
            capture_output=True, text=True, encoding='utf-8'  # Specify encoding
         )
         logger.info(f"Successfully enabled login item for '{self._app_name}' at path: '{self._app_path}'")
         return True
      except subprocess.CalledProcessError as e:
         logger.error(f"Failed to enable login item for '{self._app_name}'. osascript Stderr: {e.stderr.strip()}")
      except Exception as e:
         logger.error(f"An unexpected error occurred while enabling login item: {e}")

      return False

   def disable_login_item(self) -> bool:
      """
      Disables (deletes) the application from login items.

      Returns:
          True if the login item was successfully disabled, False otherwise.
      """
      try:
         escaped_app_name = self._app_name.replace('"', '\\"')
         script = f'tell application "System Events" to delete login item "{escaped_app_name}"'

         subprocess.run(
            ['osascript', '-e', script],
            check=True,
            capture_output=True, text=True, encoding='utf-8'  # Specify encoding
         )
         logger.info(f"Successfully disabled login item for '{self._app_name}'")
         return True
      except subprocess.CalledProcessError as e:
         # Log the specific error from osascript
         logger.error(f"Failed to disable login item '{self._app_name}'. osascript Stderr: {e.stderr.strip()}")

         # Fallback for scripts if the primary name failed, and the script name is different
         if not self._is_app_bundle:
            script_filename = os.path.basename(self._app_path)  # type: ignore
            if script_filename and script_filename != self._app_name:
               logger.warning(
                  f"Login item '{self._app_name}' not found. Attempting to delete by script filename: '{script_filename}'")
               try:
                  escaped_script_filename = script_filename.replace('"', '\\"')
                  fallback_script = f'tell application "System Events" to delete login item "{escaped_script_filename}"'
                  subprocess.run(
                     ['osascript', '-e', fallback_script],
                     check=True,
                     capture_output=True, text=True, encoding='utf-8'
                  )
                  logger.info(f"Successfully disabled login item by script filename: '{script_filename}'")
                  return True
               except subprocess.CalledProcessError as e_fallback:
                  logger.error(
                     f"Failed to disable login item by script filename '{script_filename}'. osascript Stderr: {e_fallback.stderr.strip()}")
               except Exception as e_fallback:
                  logger.error(f"An unexpected error occurred during fallback disable attempt: {e_fallback}")
            else:
               logger.debug(
                  "Running as a script, but script filename is the same as APP_NAME, or filename empty. No alternative name to try for disable.")
         else:
            logger.debug("Running as an app bundle, no script filename fallback attempted for disable.")

      except Exception as e:
         logger.error(f"An unexpected error occurred while disabling login item: {e}")

      return False

   def get_app_type_info(self) -> dict:
      """
      Returns information about the detected application type and paths.
      """
      return {
         "is_app_bundle": self._is_app_bundle,
         "application_path": self._app_path,
         "login_item_name_used": self._app_name
      }
