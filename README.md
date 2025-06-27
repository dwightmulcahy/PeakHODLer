# CoinGlass Bull Market Peak Indicator

----

`PeakHODLer` is a macOS menubar application to display the CoinGlass Bull Market Peak Indicator from CoinGlass.

```
NOTE: 
You will need to have a paid API Key from CoinGlass to use this.

```

## Articles

----

This shows the Bull Market Peak Indicator summary here: https://www.coinglass.com/bull-market-peak-signals

This idea came from the article that discussed this indicator: https://cointelegraph.com/news/30-bitcoin-price-top-indicators-hint-at-230k-bull-market-peak

## Logs

----

Application logs are stored in `/Users/<YOUR_USER_NAME>/Library/Logs/peakhodler/peakhodler.log`.  
You can also view the last 20 lines of the log by selecting the menu item `Show Logs`.

To view the complete log, you can open the `Console` application under [Applications/Utilities](/System/Applications/Utilities/Console.app).

## Building the standalone app

----

`setup.py` is used with `py2app` to create the application.  
You will need to execute the following command under terminal.

```bash
$ # Clean up and remove build directories
$ python3 setup.py clean --all
$ rm -rf build dist

$ # Build the application bundle
$ python3 setup.py py2app

$ # Test that application bundle works
$ open ./dist/PeakHODLER.app
```

## Menu Items

----

### Refresh Now

----

Refreshes the data feed.  It is not recommended to do this often as you could exceed your package plan for accesses.

### Open CoinGlass

----

This will open `https://www.coinglass.com/bull-market-peak-signals` in your default browser.

### Settings

----

#### Launch at Login

This will add `PeakHODLer` to your _Launch at Login_ list.  
A checkmark will appear next to it if the item is already enabled.
Selecting this again will remove it from your _Launch at Login_ list.

#### Set API Key

You will need a paid API key from CoinGlass to access their data.
They have several plans available at https://www.coinglass.com/pricing depending on your needs.

#### Set Refresh Rate (*)

Sets the minutes that the data from CoinGlass is updated.  
Values under 15 minutes are not accepted or recommended.

### Show Log

----

The last 20 lines of the application log are shown.
To view the complete log, use the [Console](/System/Applications/Utilities/Console.app) application.

### About PeakHODLer

----

Description and versioning information about this app.

### Quit

----

Quits the application.

## Future improvements

----

- [ ] Open `Set API Key` when there is no API Key set
- [ ] Webscrape CoinGlass for the data needed
- [ ] Notifications when one of the indicators is tripped
