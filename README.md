# trackgen

> **Work in progress.** The core pipeline is functional; physics-based parameterization and vehicle constraints are still being implemented or are experimental.

A 3D flight path generator that produces smooth, physically-realistic trajectories and streams them over ZMQ. Paths are generated using cubic spline interpolation through random waypoints, transformed to real-world ECEF/LLA coordinates, and visualized with a 3D matplotlib animation. 
Sending telemetry via ZMQ pub socket is driven by the matplotlib animation loop right now.

## Features

- Smooth cubic spline paths through randomized waypoints
- Configurable flight volume: origin (lat/lon/alt), scale, and duration
- Real-world coordinate output (ECEF → LLA) via [pymap3d](https://github.com/geospace-code/pymap3d)
- ZMQ PUB socket streaming (JSON telemetry at each time step)
- 3D animated replay via matplotlib
- Reproducible runs via `--seed`

## Quickstart

```bash
uv sync
python src/main.py
```

This generates a 60-second flight path centered over Boise, ID at 10 km scale, animates it, and publishes telemetry on `tcp://0.0.0.0:5557`.

To receive the stream in another terminal:

```bash
python scripts/sub_data.py
```

## CLI Options

```
python src/main.py [options]

  --seed INT              Random seed for reproducibility (default: random)
  --num-waypoints INT     Number of control points (default: 6)
  --duration FLOAT        Flight duration in seconds (default: 60)
  --time-delta FLOAT      Time step between published points in seconds (default: 0.1)
  --scale-meters FLOAT    Side length of the cubic flight volume in meters (default: 10000)
  --origin-lla LAT LON ALT  Ground origin of the flight volume (default: Boise, ID)
  --marker-lla LAT LON ALT  Optional LLA marker to overlay on the animation
```

Example with a fixed seed and larger volume:

```bash
python src/main.py --seed 42 --num-waypoints 8 --scale-meters 20000
```

## How It Works

1. **Waypoints** — random 3D control points are generated in normalized [0,1]³ space.
2. **Spline** — a cubic spline is fit through the waypoints (`bc_type='natural'`), producing a smooth path function `path(s)` for `s ∈ [0,1]`.
3. **ECEF transform** — the generator maps normalized positions to East/North/Up offsets around the origin, then converts to ECEF using `pymap3d.enu2ecef`.
4. **Publish** — each `(time, position_ecef)` pair is converted to LLA and published as JSON over ZMQ.
5. **Replay** — `ReplayPlotterSender` animates the full path in 3D and optionally re-streams it through the publisher.

## Project Structure

```
src/trackgen/
  smooth.py           # CLI entry point and end-to-end pipeline
  tracks/
    waypoints.py      # Waypoint generation (random, sinusoidal, spiral)
    path.py           # Cubic spline path creation
    generator.py      # ECEF coordinate transform and time iteration
  io/
    publisher.py      # ZMQ PUB socket, ECEF→LLA, JSON serialization
  replay/
    replay.py         # Matplotlib 3D animation + optional ZMQ replay
scripts/
  sub_data.py         # ZMQ subscriber test client
  smooth2.py          # Experimental physics-constrained generator
research/             # Design notes and background reading
```

## Status

| Component | State |
|---|---|
| Core spline pipeline | Working |
| ZMQ publisher | Working |
| 3D matplotlib replay | Working |
| Physics-based parameterization | Experimental (`scripts/smooth2.py`) |
| Vehicle constraints (`vehicles.py`) | Defined, not wired in |
| Test suite | Not yet written |

## Requirements

- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) for dependency management

Key dependencies: `numpy`, `scipy`, `pymap3d`, `pyzmq`, `matplotlib`, `pydantic`.
