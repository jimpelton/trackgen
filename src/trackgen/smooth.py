#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

import logging

import numpy as np

from .replay import ReplayPlotterSender
from .tracks import track_generator
from .tracks import create_smooth_path
from .tracks import create_waypoints
from .io import Publisher

logger = logging.getLogger(__name__)

_BOISE_LLA = np.array([43.6116, -116.2034, 824.0])


def parse_args():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    import argparse

    parser = argparse.ArgumentParser(description="Generate a smooth flight path.")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: random, for a new path)",
    )
    parser.add_argument(
        "--num-waypoints", type=int, default=6, help="Number of waypoints for the path"
    )
    parser.add_argument(
        "--duration", type=float, default=60.0, help="Duration of the flight in seconds"
    )
    parser.add_argument(
        "--step-delta",
        type=float,
        default=0.10,
        help="Time step between points in seconds, same as the rate that points are sent.",
    )
    parser.add_argument(
        "--scale-meters",
        type=float,
        default=10000.0,
        help="Horizontal (on the ground) size of the flight volume in meters",
    )
    parser.add_argument(
        "--vert-scale-meters",
        type=float,
        default=500.0,
        help="Flight volume height in meters",
    )
    parser.add_argument(
        "--origin-lla",
        type=float,
        nargs=3,
        default=_BOISE_LLA,
        help="Origin of the flight volume (default Boise, ID). A point on the ground around which the flight volume will be centered above.",
    )
    parser.add_argument(
        "--marker-lla",
        type=float,
        nargs=3,
        default=None,
        help="Marker to place at some LLA",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Publish telemetry without displaying the matplotlib window (for headless / container use)",
    )
    return parser.parse_args()


# Example usage
def main():
    args = parse_args()
    num_waypoints = args.num_waypoints
    seed = args.seed
    origin_lla = args.origin_lla
    scale_meters = args.scale_meters
    vert_scale_meters = args.vert_scale_meters
    duration_seconds = args.duration
    step_delta = args.step_delta

    waypoints = create_waypoints(num_waypoints, seed=seed)
    path_func = create_smooth_path(waypoints.t_waypoints, waypoints.waypoints)

    # Generate a smooth track
    gen = track_generator(
        origin_lla=origin_lla,
        scale_meters=scale_meters,
        vert_scale_meters=vert_scale_meters,
        duration_seconds=duration_seconds,
        step_delta=step_delta,
        path_func=path_func,
    )

    # Collect points
    times = []
    enu_positions = []
    for t, enu in gen:
        times.append(t)
        enu_positions.append(enu)

    enu_positions = np.array(enu_positions)

    logger.info(f"\nGenerated {len(enu_positions)} points with seed {waypoints.seed}")
    logger.info(
        f"Distance traveled: {np.sum(np.linalg.norm(np.diff(enu_positions, axis=0), axis=1)):.1f} m"
    )

    publisher = Publisher(ip="0.0.0.0", port=5557)

    if args.no_plot:
        import time
        import pymap3d as pm

        logger.info(
            "Running in headless mode — publishing %d positions", len(enu_positions)
        )
        try:
            while True:
                for pos in enu_positions:
                    lla = pm.enu2geodetic(*pos, *origin_lla)
                    publisher.publish_nowait(*lla)
                    time.sleep(step_delta)
        finally:
            publisher.close()
    else:
        plot = ReplayPlotterSender(
            enu_positions=enu_positions,
            origin_lla=origin_lla,
            publisher=publisher,
            interval_ms=step_delta * 1_000,
        )
        plot.plot_positions()
