from typing import Any

from setuptools import setup, find_packages # Good, keep find_packages

# The imports below are fine *because setup.py is not inside src*
# It's at the project root, so it can import directly from src package
from src.app_info import APP_NAME, APP_VERSION

APP = ['./src/peakhodler.py'] # Correctly points to your main script within src
DATA_FILES: list[Any] = []
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'LSUIElement': True,
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleIdentifier': f'com.yourcompany.{APP_NAME.lower().replace(" ", "")}', # More robust identifier
        'CFBundleVersion': APP_VERSION,
    },
    'packages': [
        'rumps',
        'requests',
        'aiohttp',
        'asyncio',
        'logging',
        'colorlog',
        # 'src', # <--- If you use find_packages and package_dir, you might not need 'src' here,
               # but it doesn't hurt. find_packages will handle it more systematically.
    ],
    'iconfile': './resources/peakhodler.png',
    'strip': True, # Good practice
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],

    name=APP_NAME,
    version=APP_VERSION,
    url='https://github.com/dwightmulcahy',
    license='MIT License',
    author='dWiGhT',
    author_email='dWiGhTMulcahy@gmail.com',
    description='A macOS menubar application to display a summary of the CoinGlass Bull Market Peak Indicator.',

    # --- Add this for more robust package finding ---
    packages=find_packages(where='./src'), # Search for packages within src
    package_dir={'': 'src'}, # Tell setuptools that top-level packages are found in 'src'
    # -----------------------------------------------
)