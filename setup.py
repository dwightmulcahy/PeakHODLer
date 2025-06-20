from setuptools import setup

from src.app_info import APP_NAME, APP_VERSION

APP = ['./src/peakhodler.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'LSUIElement': True,
    },
    'packages': [
        'rumps',
        'requests',
        'aiohttp',
        'asyncio',
        'logging',
        'colorlog',
    ],
    'iconfile': './resources/peakhodler.png',
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],

    name=APP_NAME,
    version=APP_VERSION,
    url='',
    license='MIT License',
    author='dWiGhT',
    author_email='dWiGhTMulcahy@gmail.com',
    description='A macOS menubar application to display a summary of the CoinGlass Bull Market Peak Indicator.'
)
