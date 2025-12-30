import numpy as np
import matplotlib.pyplot as plt

from .generator import track_generator
from .path import create_smooth_path
from .waypoints import create_waypoints


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

    s_waypoints, waypoints = create_waypoints(6, seed=42)
    path_func = create_smooth_path(s_waypoints, waypoints)


    # Generate a smooth track
    gen = track_generator(
        origin_ecef=boise_ecef,
        scale_meters=10000.0,  # 10km flight volume
        duration_seconds=60.0,  # 1 minute flight
        time_delta=1.0,  # 1 second samples
        path_func=path_func
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