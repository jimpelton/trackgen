# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a 3D flight path generation and visualization library. It generates smooth, physically-realistic flight trajectories using spline interpolation, supporting various flight dynamics constraints (e.g., racing drones, commercial airliners, birds).

**Key concepts:**
- **Normalized space**: All paths are initially generated in [0,1]³ space, then transformed to ECEF coordinates
- **Physics-based parameterization**: The project separates geometric paths (splines) from timing/physics (see research/physics_based_spline_parameterization.md)
- **ECEF coordinates**: Earth-Centered, Earth-Fixed coordinate system used for final output

## Project Structure

```
src/trackgen/           # Main package
  ├── smooth.py         # parse_args(), main() — end-to-end pipeline
  ├── tracks/           # Core path generation
  │   ├── waypoints.py  # create_waypoints(), Waypoints dataclass; sinusoidal_path(), spiral_path()
  │   ├── path.py       # create_smooth_path() — CubicSpline interpolation
  │   └── generator.py  # track_generator() — ECEF transformation and time iteration
  ├── io/
  │   └── publisher.py  # Publisher — ZMQ PUB socket, converts ECEF→LLA, publishes JSON
  └── replay/
      └── replay.py     # ReplayPlotterSender — matplotlib 3D animation + ZMQ replay
src/main.py             # CLI entry point: calls trackgen.smooth.main()
scripts/
  ├── smooth2.py        # Experimental physics-constrained generator (not integrated)
  └── sub_data.py       # ZMQ subscriber test client
vehicles.py             # FlightConstraints presets: racing_drone, airliner, falcon
research/               # Design documentation and conversation history
```

## Architecture

### Data Flow

1. **Waypoint generation** (`waypoints.py`): Generate random waypoints in normalized [0,1]³ space
2. **Path creation** (`path.py`): Create smooth cubic spline path function from waypoints
3. **Track generation** (`generator.py`): Transform path to ECEF coordinates over time duration
4. **Output**: Publish via ZMQ (`Publisher`) and/or visualize (`ReplayPlotterSender`)

### Key Functions

**`create_waypoints(num_waypoints, seed=None)`** (trackgen/tracks/waypoints.py)
- Generates random waypoints in normalized [0,1]³ space
- Returns `Waypoints` dataclass with `t_waypoints` and `waypoints` arrays
- Auto-generates a random seed if none provided (stored for reproducibility)

**`create_smooth_path(s_waypoints, waypoints)`** (trackgen/tracks/path.py)
- Creates cubic spline interpolation through waypoints
- Returns callable: `path(s) -> position` where s ∈ [0,1], clamped to avoid extrapolation

**`track_generator(origin_lla, scale_meters, duration_seconds, time_delta, path_func)`** (trackgen/tracks/generator.py)
- Transforms normalized path to ECEF coordinates with specified scale and origin
- `origin_lla` is `(lat_deg, lon_deg, alt_meters)` — the ground point below the flight volume
- Yields `(time, position_ecef)` pairs over duration; altitude is always at or above origin

**`Publisher(ip, port=5557, topic="telemetry")`** (trackgen/io/publisher.py)
- Binds a ZMQ PUB socket; `publish_nowait(pos_ecef)` converts ECEF→LLA and sends JSON
- Uses NOBLOCK flag — messages are dropped if no subscriber is ready

**`ReplayPlotterSender(positions, times, publisher=None)`** (trackgen/replay/replay.py)
- `plot_positions()` creates an animated matplotlib 3D plot
- Optionally publishes each frame via a `Publisher` instance

### Coordinate Transformations

The transformation from normalized space to ECEF (generator.py):
1. Normalize time: `t_norm = t / duration_seconds`
2. Get position in [0,1]³: `pos_normalized = path_func(t_norm)`
3. Map to ENU offsets: East/North centered (±scale/2), Up always positive ([0, scale])
4. Convert to ECEF: `pymap3d.enu2ecef(east, north, up, lat, lon, alt)`

## Development Commands

### Setup
```bash
uv sync
```

### Running
```bash
python src/main.py
python src/main.py --seed 42 --num-waypoints 8 --scale-meters 20000
```

CLI args: `--seed`, `--num-waypoints` (default 6), `--duration` (default 60s), `--time-delta` (default 0.1s), `--scale-meters` (default 10000), `--origin-lla`, `--marker-lla`

Default origin: Boise, ID (43.6116°N, 116.2034°W, 824m)

### Testing
No formal test suite. Use `scripts/sub_data.py` to verify ZMQ output while running the main demo.

## Important Notes

- **Path parameterization**: Path functions use parameter `s` ∈ [0,1], NOT time directly
- **Natural boundary conditions**: Cubic splines use `bc_type='natural'` (zero second derivative at endpoints)
- **sinusoidal_path / spiral_path** in `waypoints.py` are defined but not wired into the main pipeline — they can be passed directly to `track_generator()` as `path_func`

## Vehicle Constraints

`vehicles.py` defines `FlightConstraints` for different vehicle types. Used by `scripts/smooth2.py` (experimental) but not yet integrated into the main pipeline. Each defines `max_velocity` (m/s), `max_acceleration` (m/s²), and `max_jerk` (m/s³).

Presets: `racing_drone` (50 m/s, 30 m/s²), `airliner` (250 m/s, 5 m/s²), `falcon` (90 m/s, 25 m/s²)

## Research Documentation

The `research/` directory contains design documentation:
- **physics_based_spline_parameterization.md**: Theoretical approach to physics-integrated splines (separation of geometry and timing, parameter space conversion)
- **procedural.md**: Brainstorming for real-time/procedural generation (noise, steering behaviors, random walk — not implemented)
