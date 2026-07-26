# trackgen

> **Work in progress.** The core pipeline is functional; physics-based parameterization and vehicle constraints are planned to be done one day, but not today. 

`trackgen` generates 3D flight paths and publishes latitude/longitude/altitude telemetry over a ZMQ PUB socket. You pick a track shape — a spline through randomized waypoints, a circular orbit, or a lawnmower survey grid — which is mapped into a configurable local flight volume, sampled, converted to real-world coordinates, and optionally replayed in a 3D matplotlib window.

## Features

- Three track shapes, each its own subcommand: `smooth`, `circle`, and `grid`
- Configurable flight volume: origin, horizontal scale, vertical scale, duration, and publish interval
- Real-world WGS-84 latitude/longitude/altitude output via [pymap3d](https://github.com/geospace-code/pymap3d)
- ZMQ PUB socket streaming with JSON telemetry messages
- 3D animated replay via matplotlib
- Headless publishing mode for terminals, containers, and remote sessions
- Options settable by flag, `TRACKGEN_*` environment variable, or TOML config file
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
uv run trackgen smooth
```

This generates a 60-second flight path centered over Boise, Idaho, opens a 3D matplotlib replay window, and publishes telemetry on `tcp://0.0.0.0:5557`.

Every run names a track shape. See what is available with:

```bash
uv run trackgen --help
```

Each shape has its own options on top of the shared ones, so check the shape you want:

```bash
uv run trackgen circle --help
```

You can also run the source entry point directly:

```bash
uv run python src/main.py smooth
```

## Receive Telemetry

In one terminal, start the generator:

```bash
uv run trackgen smooth
```

In another terminal, start the included subscriber:

```bash
uv run python scripts/sub_data.py
```

The publisher uses the `telemetry` topic on port `5557` by default. Use `Ctrl-C` to stop either process.

## Headless Mode

Use `--no-plot` when you only want to publish telemetry and do not want the matplotlib UI:

```bash
uv run trackgen circle --no-plot
```

Useful for docker containers. Headless runs loop over the generated path until stopped; add `--no-loop` for a single pass that exits on its own:

```bash
uv run trackgen circle --no-plot --no-loop
```

The reverse also works — `--loop` makes the matplotlib replay repeat instead of playing once.

## Track Shapes

### `smooth`

A cubic spline through randomized waypoints in the flight volume.

```bash
uv run trackgen smooth --seed 42 --num-waypoints 8
```

The seed used is logged at startup, so a run you liked can be reproduced by passing it back with `--seed`.

### `circle`

A level circular orbit around the origin.

```bash
uv run trackgen circle --radius-m 3000 --altitude-m 400 --revolutions 3
```

### `grid`

A lawnmower survey pattern that sweeps back and forth at a fixed altitude, then retraces itself so it loops seamlessly.

```bash
uv run trackgen grid --num-lines 8 --margin-m 500
```

## Examples

Generate a longer path in a larger flight volume:

```bash
uv run trackgen smooth --seed 42 --num-waypoints 8 --duration 120 --scale-meters 20000 --vert-scale-meters 1000
```

Bind the publisher to a specific interface and port:

```bash
uv run trackgen circle --ip 127.0.0.1 --port 6000
```

Run without installing the console script:

```bash
uv run python src/main.py smooth --seed 42 --no-plot
```

## CLI Options

Shape-specific options, which go after the shape name:

```text
smooth
  --seed INT                  Random seed (default: random, a new path each run)
  --num-waypoints INT         Number of spline control points (default: 6, minimum 2)

circle
  --radius-m FLOAT            Orbit radius in meters (default: 40% of --scale-meters)
  --altitude-m FLOAT          Altitude above the origin in meters (default: 50% of --vert-scale-meters)
  --revolutions FLOAT         Full loops flown over --duration (default: 1.0)

grid
  --num-lines INT             Back-and-forth passes across the grid (default: 5, minimum 2)
  --altitude-m FLOAT          Altitude above the origin in meters (default: 50% of --vert-scale-meters)
  --margin-m FLOAT            Inset from the edge of the flight volume (default: 10% of --scale-meters)
```

Shared options, accepted by every shape:

```text
  --origin-lla LAT LON ALT    Ground origin of the flight volume (default: Boise, Idaho)
  --marker-lla LAT LON ALT    Accepted but not yet implemented
  --scale-meters FLOAT        Horizontal size of the flight volume in meters (default: 10000.0)
  --vert-scale-meters FLOAT   Height of the flight volume in meters (default: 500.0)
  --duration FLOAT            Flight duration in seconds (default: 60.0)
  --step-delta FLOAT          Seconds between generated/published points (default: 0.10)
  --ip IP                     IPv4 address to bind the ZMQ publisher to (default: 0.0.0.0)
  --port PORT                 Port to bind the ZMQ publisher to (default: 5557)
  --plot / --no-plot          Show the matplotlib replay window (default: --plot)
  --loop / --no-loop          Repeat when the path ends (default: loop when --no-plot, play once otherwise)
```

Shape parameters are given in meters and converted against the flight volume, so `--radius-m` above half of `--scale-meters` is rejected rather than silently flying outside the volume. Their defaults are percentages of the volume, so shrinking `--scale-meters` shrinks them to match.

## Configuration

Options can also come from the environment or a config file. Values resolve in this order, first match wins:

1. Command-line flag
2. `TRACKGEN_*` environment variable
3. `--config` TOML file
4. Built-in default

Every option has an environment variable named after it, which is handy in containers:

```bash
TRACKGEN_PORT=6000 TRACKGEN_IP=0.0.0.0 uv run trackgen circle --no-plot
```

A config file collects a whole scenario. `[common]` applies to every shape and a per-shape table overrides it for that shape alone; keys may be written with dashes or underscores. See [scenarios/example.toml](scenarios/example.toml):

```toml
[common]
origin-lla = [43.6116, -116.2034, 824.0]
scale-meters = 20000.0
port = 5557

[circle]
radius-m = 6000.0
revolutions = 3.0
```

```bash
uv run trackgen --config scenarios/example.toml circle --no-plot
```

Note that `--config` belongs to `trackgen` itself, so it goes before the shape name.

## Shell Completion

```bash
eval "$(_TRACKGEN_COMPLETE=zsh_source trackgen)"
```

Use `bash_source` or `fish_source` for those shells. Add the line to your shell profile to make it stick.

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

1. **Shape** - the chosen subcommand builds a path function over normalized `[0, 1]^3` space. `smooth` samples random control points, `circle` and `grid` are analytic.
2. **Normalization** - meter-valued shape options such as `--radius-m` are divided by the flight volume scale to land in that same normalized space.
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
