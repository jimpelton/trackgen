import numpy as np
import matplotlib.pyplot as plt
import pymap3d

from tracks.generator import track_generator
from tracks.path import create_smooth_path
from tracks.waypoints import create_waypoints


def plot_positions(positions: np.ndarray):
    # Create 3D plot
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    # Plot the path
    ax.plot(
        positions[:, 0],
        positions[:, 1],
        positions[:, 2],
        "b-",
        linewidth=2,
        label="Flight Path",
    )

    # Mark start and end points
    ax.plot(
        [positions[0, 0]],
        [positions[0, 1]],
        [positions[0, 2]],
        "go",
        markersize=10,
        label="Start",
    )
    ax.plot(
        [positions[-1, 0]],
        [positions[-1, 1]],
        [positions[-1, 2]],
        "rs",
        markersize=10,
        label="End",
    )

    # Set labels and title
    ax.set_xlabel("ECEF X (m)")
    ax.set_ylabel("ECEF Y (m)")
    ax.set_zlabel("ECEF Z (m)")
    ax.set_title("3D Flight Path Visualization")
    ax.legend()

    plt.show()


_BOISE_ECEF = np.array([-2042359.37, -4150317.47, 4377856.4])
_BOISE_LLA = np.array([43.6116, -116.2034, 824.0])


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Generate a smooth flight path.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility (default: random, for a new path)")
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
        help="Origin of the flight in LLA (default Boise, ID)",
    )
    return parser.parse_args()


# Example usage
if __name__ == "__main__":
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
        if t % 10 == 0:  # Print every 10 seconds
            print(f"t={t:6.1f}s: ECEF {pos}")

    # Optional: visualize the path
    positions = np.array(positions)
    print(f"\nGenerated {len(positions)} points with seed {waypoints.seed}")
    print(f"Distance traveled: {np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1)):.1f} m")

    plot_positions(positions)
