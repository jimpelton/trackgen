import logging

import numpy as np
import pymap3d

from .replay import ReplayPlotterSender
from .tracks import track_generator
from .tracks import create_smooth_path
from .tracks import create_waypoints
from .io import Publisher

logger = logging.getLogger(__name__)


_BOISE_ECEF = np.array([-2042359.37, -4150317.47, 4377856.4])
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
        "--time-delta", type=float, default=0.10, help="Time step between points in seconds"
    )
    parser.add_argument(
        "--scale-meters", type=float, default=10000.0, help="Scale of the flight volume in meters"
    )
    parser.add_argument(
        "--origin-lla",
        type=float,
        nargs=3,
        default=_BOISE_LLA,
        help="Origin of the flight volume (default Boise, ID). A point on the ground around which the flight volume will be centered above.",
    )
    parser.add_argument(
        "--marker-lla", type=float, nargs=3, default=None, help="Marker to place at some LLA"
    )
    return parser.parse_args()


# Example usage
def main():
    # origin = np.array([6378137.0, 0.0, 0.0])  # On equator at prime meridian
    args = parse_args()
    num_waypoints = args.num_waypoints
    seed = args.seed
    origin_lla = args.origin_lla
    scale_meters = args.scale_meters
    duration_seconds = args.duration
    time_delta = args.time_delta

    # s_waypoints, waypoints = create_waypoints(6, seed=42)
    waypoints = create_waypoints(num_waypoints, seed=seed)
    path_func = create_smooth_path(waypoints.t_waypoints, waypoints.waypoints)

    # Generate a smooth track
    gen = track_generator(
        origin_ecef=np.array(pymap3d.geodetic2ecef(*origin_lla)),
        scale_meters=scale_meters,
        duration_seconds=duration_seconds,
        time_delta=time_delta,
        path_func=path_func,
    )

    # Collect points
    times = []
    positions = []
    for t, pos in gen:
        times.append(t)
        positions.append(pos)
        # if t % 10 == 0:  # Print every 10 seconds
        #     print(f"Generating... t={t:6.1f}s: ECEF {pos}")

    positions = np.array(positions)

    print(f"\nGenerated {len(positions)} points with seed {waypoints.seed}")
    print(f"Distance traveled: {np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1)):.1f} m")

    publisher = Publisher(ip="0.0.0.0", port=5557)

    plot = ReplayPlotterSender(positions=positions, times=times, publisher=publisher)
    plot.plot_positions()

    # for t, pos in zip(times, positions):
    #     print(f"t={t:6.1f}s: ECEF {pos}")
    #     plot.update_curr_pos(pos)
    #     time.sleep(t)
