import numpy as np
from typing import Generator, Tuple, Callable
from scipy.interpolate import CubicSpline
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

RANDOM_SEED = None
def generate_waypoints(num_waypoints: int, seed: int|None = RANDOM_SEED) -> Tuple[np.ndarray, np.ndarray]:
    if seed is not None:
        np.random.seed(seed)

    # Create random waypoints in normalized space
    t_waypoints = np.linspace(0, 1, num_waypoints)
    waypoints = np.random.rand(num_waypoints, 3)

    # Ensure start and end are within bounds
    waypoints[0] = np.array([0.1, 0.1, 0.9])
    waypoints[-1] = np.array([0.9, 0.9, 0.9])

    return t_waypoints, waypoints


def create_smooth_path(num_waypoints: int = 5, seed: int = None) -> Callable[[float], np.ndarray]:
    """
    Create a smooth 3D path function that maps t ∈ [0,1] to positions ∈ [0,1]³.

    Uses random waypoints with cubic spline interpolation for smooth, organic motion.
    """
    t_waypoints, waypoints = generate_waypoints(num_waypoints, seed)

    # Create cubic splines for each dimension
    splines = [CubicSpline(t_waypoints, waypoints[:, i], bc_type='natural')
               for i in range(3)]

    def path(s: float) -> np.ndarray:
        """Evaluate path at s ∈ [0,1]"""
        s_clamped = np.clip(s, 0, 1)
        return np.array([spline(s_clamped) for spline in splines])

    return path


def track_generator(
        origin_ecef: np.ndarray,
        scale_meters: float,
        duration_seconds: float,
        time_delta: float,
        path_func: Callable[[float], np.ndarray] = None,
        num_waypoints: int = 5,
        seed: int = None
) -> Generator[Tuple[float, np.ndarray], None, None]:
    """
    Generate smooth ECEF track coordinates following a curved path.

    Args:
        origin_ecef: Starting position in ECEF (x, y, z) meters
        scale_meters: Size of the flight volume in meters (normalized space scaled to this)
        duration_seconds: Total duration of the track
        time_delta: Time step between points in seconds
        path_func: Optional custom path function(t) that maps [0,1] → [0,1]³
        num_waypoints: Number of waypoints for default path (if path_func is None)
        seed: Random seed for reproducible paths

    Yields:
        Tuple of (time, position_ecef)
    """
    if path_func is None:
        path_func = create_smooth_path(num_waypoints, seed)

    t = 0.0
    while t <= duration_seconds:
        # Normalize time to [0, 1]
        t_norm = t / duration_seconds

        # Get position in normalized space [0,1]³
        pos_normalized = path_func(t_norm)

        # Transform to ECEF: scale and translate
        # Center the normalized space around origin (subtract 0.5 to go from [0,1] to [-0.5,0.5])
        pos_centered = (pos_normalized - 0.5) * scale_meters
        pos_ecef = origin_ecef + pos_centered

        yield t, pos_ecef
        t += time_delta


def plot_positions(positions: np.ndarray):
    # Create 3D plot
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot the path
    ax.plot(positions[:, 0], positions[:, 1], positions[:, 2],
            'b-', linewidth=2, label='Flight Path')
    ax.plot(positions[:, 0], positions[:, 1], positions[:, 2],
            'ro', markersize=4, label='Sample Points')

    # Mark start and end points
    ax.plot([positions[0, 0]], [positions[0, 1]], [positions[0, 2]],
            'go', markersize=10, label='Start')
    ax.plot([positions[-1, 0]], [positions[-1, 1]], [positions[-1, 2]],
            'rs', markersize=10, label='End')

    # Set labels and title
    ax.set_xlabel('ECEF X (m)')
    ax.set_ylabel('ECEF Y (m)')
    ax.set_zlabel('ECEF Z (m)')
    ax.set_title('3D Flight Path Visualization')
    ax.legend()

    plt.show()



# Example usage
if __name__ == "__main__":
    # origin = np.array([6378137.0, 0.0, 0.0])  # On equator at prime meridian
    # boise_lla = np.array([43.6116, -116.2034, 824.0])
    boise_ecef = np.array([-2042359.37, -4150317.47, 4377856.4])

    # Generate a smooth track
    gen = track_generator(
        origin_ecef=boise_ecef,
        scale_meters=10000.0,  # 10km flight volume
        duration_seconds=60.0,  # 1 minute flight
        time_delta=1.0,  # 1 second samples
        num_waypoints=6,  # 6 waypoints for smooth curves
        # seed=42  # Reproducible
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
    print(f"\nGenerated {len(positions)} points")
    print(f"Distance traveled: {np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1)):.1f} m")

    plot_positions(positions)