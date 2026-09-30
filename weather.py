#!/usr/bin/env python3
"""Local weather relative to five years of historical daily means."""
import argparse
import calendar
from collections import Counter
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import statistics
import subprocess
import tempfile
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / 'Library/Application Support/Daily Weather'
APP = DATA / 'Daily Weather.app'
LABELS = ['Cold 🥶', 'Cool 🤧', 'Mild 😊', 'Warm 🌞', 'Hot 🥵']

def classify(value, mean, sigma):
    if sigma <= 0:
        raise ValueError('Historical temperatures must have nonzero variation.')
    z = (value - mean) / sigma
    return LABELS[0 if z < -2 else 1 if z < -1 else 2 if z <= 1 else 3 if z <= 2 else 4]

def fetch(host, **params):
    with urlopen(host + '?' + urlencode(params), timeout=60) as response:
        return json.load(response)

def native(mode, body=None):
    with tempfile.TemporaryDirectory() as temp:
        result = Path(temp) / 'result.json'
        command = ['/usr/bin/open', '-W', '-n', str(APP), '--args', mode, str(result)]
        if body is not None:
            command.append(body)
        subprocess.run(command, check=True, timeout=110)
        value = json.loads(result.read_text())
        if 'error' in value:
            raise RuntimeError(value['error'])
        return value

def historical(lat, lon, today, timezone):
    # Exact rolling five-year interval, including Feb 29 where applicable.
    start = today.replace(year=today.year - 5, day=min(today.day, calendar.monthrange(today.year - 5, today.month)[1]))
    end = today - timedelta(days=1)
    cache = DATA / f'history-{lat:.2f}-{lon:.2f}-{today}-{timezone.replace("/", "_")}.json'
    if cache.exists():
        return json.loads(cache.read_text())
    result = fetch('https://archive-api.open-meteo.com/v1/archive', latitude=lat, longitude=lon,
                   start_date=start.isoformat(), end_date=end.isoformat(), timezone=timezone,
                   daily='temperature_2m_mean', models='era5')
    daily = result['daily']
    rows = [(day, value) for day, value in zip(daily['time'], daily['temperature_2m_mean']) if value is not None]
    # ERA5 arrives several days late. Never disguise an incomplete baseline.
    expected = (today - start).days
    if len(rows) < expected - 10:
        raise ValueError(f'History incomplete: {len(rows)} of {expected} days.')
    DATA.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows))
    for old in DATA.glob('history-*.json'):
        if old != cache:
            old.unlink()
    return rows

def experiment(rows, mean, sigma):
    out = ['# Annual baseline experiment', '', f'Historical range: {rows[0][0]} through {rows[-1][0]} ({len(rows)} days).',
           f'Mean: {mean:.2f}°C; population standard deviation: {sigma:.2f}°C.', '',
           'Percent of historical daily means in each label. This is a descriptive check on the same data used to fit the baseline, not a forecast validation.', '',
           '| Month | Cold 🥶 | Cool 🤧 | Mild 😊 | Warm 🌞 | Hot 🥵 |', '|---|---:|---:|---:|---:|---:|']
    for month in range(1, 13):
        values = [v for d, v in rows if date.fromisoformat(d).month == month]
        counts = Counter(classify(v, mean, sigma) for v in values)
        out.append('| ' + calendar.month_name[month] + ' | ' + ' | '.join(f'{100*counts[label]/len(values):.1f}%' for label in LABELS) + ' |')
    out += ['', '## Example days', '']
    ordered = sorted(rows, key=lambda row: row[1])
    for fraction in [0, .1, .5, .9, 1]:
        day, value = ordered[round(fraction * (len(ordered)-1))]
        out.append(f'- {day}: {value:.1f}°C — {classify(value, mean, sigma)}')
    out += ['', 'Data: [Open-Meteo ERA5 reanalysis](https://open-meteo.com/en/docs/historical-weather-api). Recent days may be unavailable because the archive lags.',
            'Keep the annual baseline until we review these results together. Labels describe relative temperature, not clothing advice.']
    return '\n'.join(out) + '\n'

def due(now, last_date):
    return now.hour >= 7 and last_date != now.date().isoformat()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--location', nargs=2, type=float, metavar=('LAT', 'LON'))
    parser.add_argument('--notify', action='store_true')
    parser.add_argument('--scheduled', action='store_true')
    parser.add_argument('--experiment', type=Path)
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    state = DATA / 'last-report.txt'
    if args.scheduled and not due(datetime.now().astimezone(), state.read_text().strip() if state.exists() else None):
        return
    lat, lon = args.location or (lambda loc: (loc['latitude'], loc['longitude']))(native('location'))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Invalid latitude or longitude.')
    forecast = fetch('https://api.open-meteo.com/v1/forecast', latitude=lat, longitude=lon,
                     daily='temperature_2m_mean,temperature_2m_min,temperature_2m_max', timezone='auto', forecast_days=2)
    today = datetime.now(ZoneInfo(forecast['timezone'])).date()
    daily = forecast['daily']
    index = daily['time'].index(today.isoformat())
    rows = historical(lat, lon, today, forecast['timezone'])
    values = [value for _, value in rows]
    mean, sigma = statistics.mean(values), statistics.pstdev(values)
    lines = [f'{today} · {lat:.2f}, {lon:.2f}']
    for label, key in [('Mean', 'mean'), ('High', 'max'), ('Low', 'min')]:
        value = daily[f'temperature_2m_{key}'][index]
        lines.append(f'{label}: {classify(value, mean, sigma)} · {value:.1f}°C / {value*9/5+32:.1f}°F')
    lines.append(f'Baseline: {mean:.1f}°C, σ {sigma:.1f}°C · {len(rows)} days')
    message = '\n'.join(lines)
    print(message, flush=True)
    if args.experiment:
        args.experiment.write_text(experiment(rows, mean, sigma))
    if args.notify or args.scheduled:
        native('notify', message)
        if args.scheduled:
            state.write_text(datetime.now().astimezone().date().isoformat())

if __name__ == '__main__':
    main()
