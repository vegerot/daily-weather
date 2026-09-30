# Daily Weather 😊

A Mac morning notification showing forecast daily mean, high, and low in °C and °F, each classified against a shared rolling five-year baseline of historical daily mean temperatures at your current location.

| Relative temperature | Label |
|---|---|
| Below −2σ | Cold 🥶 |
| −2σ to below −1σ | Cool 🤧 |
| −1σ through +1σ | Mild 😊 |
| Above +1σ through +2σ | Warm 🌞 |
| Above +2σ | Hot 🥵 |

σ is the population standard deviation. These labels describe relative temperature; actual temperatures help you decide what to wear. The mean is the API's daily mean, not the midpoint of the high and low.

## Run

Requires macOS, Python 3.9+, and Apple's Swift compiler (Command Line Tools). No Python dependencies or API key.

```sh
./install
./weather
./weather --notify
./weather --location 37.7749 -122.4194 --experiment experiment-san-francisco.md
python3 -m unittest discover --start-directory tests
```

Allow Daily Weather access in System Settings → Privacy & Security → Location Services and System Settings → Notifications. Location coordinates are sent to Open-Meteo to fetch weather. There is no IP-location fallback: a denied location request fails visibly in the error log.

Installation creates `~/Library/Application Support/Daily Weather/Daily Weather.app` and a user launch agent. The schedule runs at 7 a.m. in the Mac's current time zone. It also checks every 15 minutes and at login, so a sleeping Mac delivers on wake and a failed request can retry. Successful scheduled reports are deduplicated by the Mac's local date. Manual notifications do not suppress the morning schedule. No delivery before 7 a.m.; launchd runs one scheduled process at a time.

The notification helper checks authorization and submission to macOS. Submission does not prove a banner was visible: Focus settings and notification preferences control presentation. The notification includes the coordinate location so you can check where the forecast applies.

Logs and the last successful scheduled date live in `~/Library/Application Support/Daily Weather/`. Run `./weather --notify` after enabling permissions to verify a report immediately.

## Historical experiment

The experiment file shows monthly label percentages and representative historical days. It checks whether annual thresholds make labels too repetitive within seasons. Keep the annual baseline until we review the evidence together. Example-location experiments do not establish your device's current location.

Data comes from [Open-Meteo](https://open-meteo.com/), with [ERA5 historical reanalysis](https://open-meteo.com/en/docs/historical-weather-api). Reanalysis combines observations and modeling; it is not a thermometer record at your exact coordinates. We request the preceding five calendar years through yesterday, exclude unavailable days, disclose the actual coverage, and fail if more than ten days are missing. Recent ERA5 days arrive late. The population standard deviation uses the returned daily means. History is cached for the day/location; old caches are removed after fetching a new one.

## Remove the schedule

```sh
launchctl bootout "gui/$(id -u)/com.vegerot.daily-weather"
rm "$HOME/Library/LaunchAgents/com.vegerot.daily-weather.plist"
```

The source and application remain available. Moving the source directory requires rerunning `./install` because the launch agent references its absolute path.

## Design decisions

1. Requirements: show actual temperatures alongside relative labels; test seasonal usefulness.
2. Delete: no server, database, third-party Python dependencies, or permanent daemon.
3. Simplify: one weather script and a native permission/notification helper.
4. Accelerate: location override and a daily historical cache make verification quick.
5. Automate: a user launch agent checks the local date and sends one successful morning report.
