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
src/tracks/           # Main track generation package
  ├── generator.py    # Core track_generator() - transforms normalized paths to ECEF over time
  ├── path.py         # create_smooth_path() - spline interpolation for 3D paths
  ├── waypoints.py    # Waypoint generation and predefined path functions (sinusoidal, spiral)
src/smooth.py         # Example/demo script showing end-to-end usage
smooth2.py            # Experimental physics-constrained path generation (FlightConstraints)
vehicles.py           # Flight constraint definitions for different vehicle types
research/             # Design documentation and conversation history
```

## Architecture

### Data Flow

1. **Waypoint generation** (`waypoints.py`): Generate random or predefined waypoints in normalized [0,1]³ space
2. **Path creation** (`path.py`): Create smooth cubic spline path function from waypoints
3. **Track generation** (`generator.py`): Transform path to ECEF coordinates over time duration
4. **Output**: Generator yields `(time, position_ecef)` tuples for consumption

### Key Functions

**`create_waypoints(num_waypoints, seed)`** (waypoints.py:27)
- Generates random waypoints in normalized [0,1]³ space
- Returns `(t_waypoints, waypoints)` arrays

**`create_smooth_path(s_waypoints, waypoints)`** (path.py:7)
- Creates cubic spline interpolation through waypoints
- Returns callable: `path(s) -> position` where s ∈ [0,1]

**`track_generator(origin_ecef, scale_meters, duration_seconds, time_delta, path_func)`** (generator.py:6)
- Main track generation function
- Transforms normalized path to ECEF coordinates with specified scale and origin
- Yields `(time, position_ecef)` pairs over duration

### Coordinate Transformations

The transformation from normalized space to ECEF (generator.py:35-40):
1. Get position in [0,1]³: `pos_normalized = path_func(t_norm)`
2. Center around origin: `pos_centered = (pos_normalized - 0.5) * scale_meters`
3. Translate to ECEF: `pos_ecef = origin_ecef + pos_centered`

## Development Commands

### Setup
```bash
# Install dependencies (uses uv package manager)
uv sync
```

### Running Examples
```bash
# Run the main demo (generates and visualizes a flight path)
python src/smooth.py
```

### Testing
This project currently has no formal test suite. Testing is done via example scripts.

## Important Notes

- **Path parameterization**: Path functions use parameter `s` (or `t`) ∈ [0,1], NOT time directly
- **Time normalization**: In `track_generator`, time is normalized to [0,1] via `t_norm = t / duration_seconds` before querying the path function
- **Natural boundary conditions**: Cubic splines use `bc_type='natural'` for smoother curves at endpoints
- **ECEF origins**: Example uses Boise, ID coordinates: `[-2042359.37, -4150317.47, 4377856.4]`

## Vehicle Constraints

The `vehicles.py` file defines `FlightConstraints` for different vehicle types. These are used in the experimental `smooth2.py` but not yet integrated into the main track generator. Each constraint defines:
- `max_velocity` (m/s)
- `max_acceleration` (m/s²)
- `max_jerk` (m/s³)

Examples: `racing_drone`, `airliner`, `falcon`

## Research Documentation

The `research/` directory contains design documentation:
- **physics_based_spline_parameterization.md**: Explains the theoretical approach to incorporating physics into spline-based paths (separation of geometry and timing, parameter space conversion)
