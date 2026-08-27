#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

import ipaddress
import logging
import tomllib
from pathlib import Path
from typing import Any, Callable, Dict

import click

from .pipeline import TrackConfig, run_track
from .tracks import (
    create_circular_path,
    create_grid_path,
    create_smooth_path,
    create_waypoints,
)

logger = logging.getLogger(__name__)

_BOISE_LLA = (43.6116, -116.2034, 824.0)
_SHAPES = ("smooth", "circle", "grid")


def _validate_ip(ctx, param, value: str) -> str:
    if value == "*":
        return value
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise click.BadParameter(
            f"{value!r} is not a valid IP address (use '*' to bind every interface)",
            ctx=ctx,
            param=param,
        )
    return value


def _normalize_keys(table: Dict[str, Any]) -> Dict[str, Any]:
    """Accept both --scale-meters and scale_meters spellings in config files."""
    return {key.replace("-", "_"): value for key, value in table.items()}


def load_config(path: Path) -> Dict[str, Dict[str, Any]]:
    """Build click's ``default_map`` from a TOML file.

    ``[common]`` applies to every shape; a per-shape table such as ``[circle]``
    overrides it for that shape alone.
    """
    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    unknown = set(raw) - {"common", *_SHAPES}
    if unknown:
        raise click.BadParameter(
            f"unknown section(s) {', '.join(sorted(unknown))} in {path}; "
            f"expected any of: common, {', '.join(_SHAPES)}",
            param_hint="--config",
        )

    common = _normalize_keys(raw.get("common", {}))
    return {
        shape: {**common, **_normalize_keys(raw.get(shape, {}))} for shape in _SHAPES
    }


def common_options(f: Callable) -> Callable:
    """Apply the options every shape shares.

    Listed in help order and applied in reverse, since decorators stack bottom-up.
    """
    options = [
        click.option(
            "--origin-lla",
            nargs=3,
            type=float,
            default=_BOISE_LLA,
            show_default=True,
            metavar="LAT LON ALT",
            envvar="TRACKGEN_ORIGIN_LLA",
            show_envvar=True,
            help="Ground origin the flight volume is centered above (default: Boise, ID).",
        ),
        click.option(
            "--marker-lla",
            nargs=3,
            type=float,
            default=None,
            metavar="LAT LON ALT",
            envvar="TRACKGEN_MARKER_LLA",
            show_envvar=True,
            help="Marker to place at some LLA. Accepted but not yet implemented.",
        ),
        click.option(
            "--scale-meters",
            type=click.FloatRange(min=0, min_open=True),
            default=10000.0,
            show_default=True,
            envvar="TRACKGEN_SCALE_METERS",
            show_envvar=True,
            help="Horizontal (on the ground) size of the flight volume in meters.",
        ),
        click.option(
            "--vert-scale-meters",
            type=click.FloatRange(min=0, min_open=True),
            default=500.0,
            show_default=True,
            envvar="TRACKGEN_VERT_SCALE_METERS",
            show_envvar=True,
            help="Flight volume height in meters.",
        ),
        click.option(
            "--duration",
            type=click.FloatRange(min=0, min_open=True),
            default=60.0,
            show_default=True,
            envvar="TRACKGEN_DURATION",
            show_envvar=True,
            help="Duration of the flight in seconds.",
        ),
        click.option(
            "--step-delta",
            type=click.FloatRange(min=0, min_open=True),
            default=0.10,
            show_default=True,
            envvar="TRACKGEN_STEP_DELTA",
            show_envvar=True,
            help="Seconds between points, which is also the rate they are published at.",
        ),
        click.option(
            "--ip",
            type=str,
            default="0.0.0.0",
            show_default=True,
            callback=_validate_ip,
            envvar="TRACKGEN_IP",
            show_envvar=True,
            help="IP addr to bind to (v4, tcp).",
        ),
        click.option(
            "--port",
            type=click.IntRange(1, 65535),
            default=5557,
            show_default=True,
            envvar="TRACKGEN_PORT",
            show_envvar=True,
            help="Port to bind publisher to.",
        ),
        click.option(
            "--plot/--no-plot",
            default=True,
            show_default=True,
            envvar="TRACKGEN_PLOT",
            show_envvar=True,
            help="Show the matplotlib replay window. --no-plot publishes only, "
            "for headless / container use.",
        ),
        click.option(
            "--loop/--no-loop",
            default=None,
            envvar="TRACKGEN_LOOP",
            show_envvar=True,
            help="Repeat the path when it ends  [default: loop when --no-plot, "
            "play once otherwise]",
        ),
    ]
    for option in reversed(options):
        f = option(f)
    return f


def _check_volume(cfg: TrackConfig) -> None:
    """Cross-parameter checks that apply to every shape."""
    if cfg.step_delta > cfg.duration:
        raise click.BadParameter(
            f"{cfg.step_delta:g} is longer than --duration ({cfg.duration:g}); "
            "no points would be generated",
            param_hint="--step-delta",
        )


def _reject_if_over(value: float, limit: float, hint: str, limit_name: str) -> None:
    if value > limit:
        raise click.BadParameter(
            f"{value:g} exceeds {limit_name} ({limit:g})", param_hint=hint
        )


@click.group(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 100,
    }
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    envvar="TRACKGEN_CONFIG",
    help="TOML file of option defaults, with a [common] section plus one per shape.",
)
@click.pass_context
def cli(ctx: click.Context, config: Path | None):
    """Generate 3D flight paths and publish LLA telemetry over a ZMQ PUB socket.

    Pick a track shape below. Each shape has its own options on top of the shared
    flight-volume and publisher options, so see e.g. `trackgen circle --help`.

    Values resolve in this order: command line, then TRACKGEN_* environment
    variable, then --config file, then the built-in default.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    if config is not None:
        ctx.default_map = load_config(config)


@cli.command()
@click.option(
    "--seed",
    type=int,
    default=None,
    show_default="random, for a new path each run",
    envvar="TRACKGEN_SEED",
    show_envvar=True,
    help="Random seed, for a reproducible path.",
)
@click.option(
    "--num-waypoints",
    type=click.IntRange(min=2),
    default=6,
    show_default=True,
    envvar="TRACKGEN_NUM_WAYPOINTS",
    show_envvar=True,
    help="Number of spline control points.",
)
@common_options
def smooth(seed: int | None, num_waypoints: int, **common):
    """Cubic-spline path through randomized waypoints."""
    cfg = TrackConfig(**common)
    _check_volume(cfg)

    waypoints = create_waypoints(num_waypoints, seed=seed)
    logger.info("Seed: %d", waypoints.seed)

    run_track(create_smooth_path(waypoints.t_waypoints, waypoints.waypoints), cfg)


@cli.command()
@click.option(
    "--radius-m",
    type=click.FloatRange(min=0, min_open=True),
    default=None,
    show_default="40% of --scale-meters",
    envvar="TRACKGEN_RADIUS_M",
    show_envvar=True,
    help="Orbit radius in meters, at most half of --scale-meters.",
)
@click.option(
    "--altitude-m",
    type=click.FloatRange(min=0),
    default=None,
    show_default="50% of --vert-scale-meters",
    envvar="TRACKGEN_ALTITUDE_M",
    show_envvar=True,
    help="Altitude above the origin in meters, at most --vert-scale-meters.",
)
@click.option(
    "--revolutions",
    type=click.FloatRange(min=0, min_open=True),
    default=1.0,
    show_default=True,
    envvar="TRACKGEN_REVOLUTIONS",
    show_envvar=True,
    help="Full loops flown over --duration.",
)
@common_options
def circle(
    radius_m: float | None, altitude_m: float | None, revolutions: float, **common
):
    """Level circular orbit around the origin."""
    cfg = TrackConfig(**common)
    _check_volume(cfg)

    # Defaults track the volume, so shrinking --scale-meters cannot put the
    # circle outside its own flight volume.
    radius_m = 0.4 * cfg.scale_meters if radius_m is None else radius_m
    altitude_m = 0.5 * cfg.vert_scale_meters if altitude_m is None else altitude_m
    _reject_if_over(
        radius_m, cfg.scale_meters / 2, "--radius-m", "half of --scale-meters"
    )
    _reject_if_over(
        altitude_m, cfg.vert_scale_meters, "--altitude-m", "--vert-scale-meters"
    )

    run_track(
        create_circular_path(
            radius=radius_m / cfg.scale_meters,
            height=altitude_m / cfg.vert_scale_meters,
            revolutions=revolutions,
        ),
        cfg,
    )


@cli.command()
@click.option(
    "--num-lines",
    type=click.IntRange(min=2),
    default=5,
    show_default=True,
    envvar="TRACKGEN_NUM_LINES",
    show_envvar=True,
    help="Number of back-and-forth passes across the grid.",
)
@click.option(
    "--altitude-m",
    type=click.FloatRange(min=0),
    default=None,
    show_default="50% of --vert-scale-meters",
    envvar="TRACKGEN_ALTITUDE_M",
    show_envvar=True,
    help="Altitude above the origin in meters, at most --vert-scale-meters.",
)
@click.option(
    "--margin-m",
    type=click.FloatRange(min=0),
    default=None,
    show_default="10% of --scale-meters",
    envvar="TRACKGEN_MARGIN_M",
    show_envvar=True,
    help="Inset from the edge of the flight volume in meters.",
)
@common_options
def grid(num_lines: int, altitude_m: float | None, margin_m: float | None, **common):
    """Lawnmower survey pattern at a fixed altitude."""
    cfg = TrackConfig(**common)
    _check_volume(cfg)

    altitude_m = 0.5 * cfg.vert_scale_meters if altitude_m is None else altitude_m
    margin_m = 0.1 * cfg.scale_meters if margin_m is None else margin_m
    _reject_if_over(
        altitude_m, cfg.vert_scale_meters, "--altitude-m", "--vert-scale-meters"
    )
    if margin_m >= cfg.scale_meters / 2:
        raise click.BadParameter(
            f"{margin_m:g} must be less than half of --scale-meters "
            f"({cfg.scale_meters / 2:g}), or the sweep has no room",
            param_hint="--margin-m",
        )

    run_track(
        create_grid_path(
            num_lines=num_lines,
            height=altitude_m / cfg.vert_scale_meters,
            margin=margin_m / cfg.scale_meters,
        ),
        cfg,
    )
