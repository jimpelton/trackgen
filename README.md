# trackgen

> **Work in progress.** The core pipeline is functional; physics-based parameterization and vehicle constraints are planned to be done one day, but not today. 

`trackgen` generates smooth 3D flight paths and publishes latitude/longitude/altitude telemetry over a ZMQ PUB socket. Paths are built from randomized waypoints that are smoothed with cubic spline interpolation and then mapped into a configurable local flight volume. Finally the path is sampled and converted to real-world coordinates and optionally replayed in a 3D matplotlib window.

## Features

- Smooth cubic spline paths through randomized waypoints
- Configurable flight volume: origin, horizontal scale, vertical scale, duration, and publish interval
- Real-world WGS-84 latitude/longitude/altitude output via [pymap3d](https://github.com/geospace-code/pymap3d)
- ZMQ PUB socket streaming with JSON telemetry messages
- 3D animated replay via matplotlib
- Headless publishing mode for terminals, containers, and remote sessions
- Reproducible runs via `--seed`

## Requirements

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) for dependency management

Dependencies are managed by `uv` from `pyproject.toml`. 

## Quickstart

Clone the repository, install dependencies, and run the generator:

```bash
git clone <url> trackgen
cd trackgen
uv sync
uv run trackgen
```

This generates a 60-second flight path centered over Boise, Idaho, and opens a 3D matplotlib replay window, and publishes telemetry on `tcp://0.0.0.0:5557`.

You can also run the source entry point directly:

```bash
uv run python src/main.py
```

## Receive Telemetry

In one terminal, start the generator:

```bash
uv run trackgen
```

In another terminal, start the included subscriber:

```bash
uv run python scripts/sub_data.py
```

The publisher uses the `telemetry` topic on port `5557` by default. Use `Ctrl-C` to stop either process.

## Headless Mode

Use `--no-plot` when you only want to publish telemetry and do not want the matplotlib UI:

```bash
uv run trackgen --no-plot
```

Useful for docker containers. In headless mode trackgen loops over the generated path continuously until stopped.

## Examples

Generate the same path every run:

```bash
uv run trackgen --seed 42
```

Generate a longer path in a larger flight volume:

```bash
uv run trackgen --seed 42 --num-waypoints 8 --duration 120 --scale-meters 20000 --vert-scale-meters 1000
```

Bind the publisher to a specific interface and port:

```bash
uv run trackgen --ip 127.0.0.1 --port 6000
```

Run without installing the console script:

```bash
uv run python src/main.py --seed 42 --no-plot
```

## CLI Options

```text
uv run trackgen [options]

  --seed INT                  Random seed for reproducibility (default: random)
  --num-waypoints INT         Number of control points (default: 6)
  --duration FLOAT            Flight duration in seconds (default: 60.0)
  --step-delta FLOAT          Time step between generated/published points in seconds (default: 0.10)
  --scale-meters FLOAT        Horizontal size of the flight volume in meters (default: 10000.0)
  --vert-scale-meters FLOAT   Height of the flight volume in meters (default: 500.0)
  --origin-lla LAT LON ALT    Ground origin of the flight volume (default: Boise, Idaho)
  --marker-lla LAT LON ALT    Optional LLA marker to overlay on the animation
  --no-plot                   Publish telemetry without displaying the matplotlib window
  --ip IP                     IPv4 address to bind the ZMQ publisher to (default: 0.0.0.0)
  --port PORT                 Port to bind the ZMQ publisher to (default: 5557)
```

## Telemetry Format

Telemetry is sent as a multipart ZMQ message:

```text
topic: telemetry
payload: JSON
```

Payload example:

```json
{
  "version": "v1",
  "timestamp_us": 1782945600000000,
  "name": "aircraft_telemetry",
  "msg_id": "00000000-0000-0000-0000-000000000000",
  "lat_deg": 43.6123456,
  "lon_deg": -116.2034567,
  "alt_hae_m": 1024.123
}
```

## How It Works

1. **Waypoints** - random 3D control points are generated in normalized `[0, 1]^3` space.
2. **Spline** - a cubic spline is fit through the waypoints, producing a smooth path function over `[0, 1]`.
3. **Track generation** - the path is evaluated at `--step-delta` intervals and mapped into East/North/Up offsets around `--origin-lla`.
4. **Coordinate conversion** - ENU positions are converted to geodetic latitude/longitude/altitude with `pymap3d`.
5. **Publish and replay** - telemetry is published over ZMQ while the path is replayed in matplotlib, unless `--no-plot` is used.

## Development

Install development dependencies:

```bash
uv sync --dev
```

Format the code:

```bash
uv run black src
```
