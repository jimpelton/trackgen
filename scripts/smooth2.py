#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

import numpy as np
from typing import Generator, Tuple, Callable, Optional, TypeAlias, Dict, List
from scipy.interpolate import CubicSpline
from dataclasses import dataclass
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


@dataclass
class FlightConstraints:
    """Physical constraints for realistic flight."""
    max_velocity: float = 100.0  # m/s (e.g., ~220 mph for small aircraft)
    max_acceleration: float = 20.0  # m/s² (e.g., ~2g for maneuvering)
    max_jerk: float = 50.0  # m/s³ (rate of change of acceleration)

@dataclass
class PathPoint:
    position: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray


def create_constrained_path(
        waypoints_normalized: np.ndarray,
        constraints: FlightConstraints
) -> Callable[[float], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """
    Create a smooth path with velocity/acceleration constraints.

    Returns a function that maps t ∈ [0,1] to (position, velocity, acceleration).
    """
    num_points = waypoints_normalized.shape[0]
    t_waypoints = np.linspace(0, 1, num_points)

    # Create position splines for each dimension
    pos_splines = [CubicSpline(t_waypoints, waypoints_normalized[:, i], bc_type='natural')
                   for i in range(3)]

    def evaluate(t: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Returns (position, velocity, acceleration) in normalized space."""
        t_clamped = np.clip(t, 0, 1)

        position = np.array([s(t_clamped) for s in pos_splines])
        velocity = np.array([s(t_clamped, 1) for s in pos_splines])  # First derivative
        acceleration = np.array([s(t_clamped, 2) for s in pos_splines])  # Second derivative

        # 3d vectors
        return position, velocity, acceleration
        # return PathPoint(position, velocity, acceleration)

    return evaluate




Time: TypeAlias = float
ECEFPositions_M: TypeAlias = np.ndarray
ECEFVelocities_MPS: TypeAlias = np.ndarray
Acceleration: TypeAlias = np.ndarray


def track_generator_constrained(
        origin_ecef: np.ndarray,
        scale_meters: float,
        constraints: FlightConstraints,
        time_delta: float,
        num_waypoints: int = 6,
        seed: Optional[int] = None
) -> Generator[Tuple[Time, ECEFPositions_M, ECEFVelocities_MPS, Acceleration], None, None]:
    """
    Generate ECEF track with velocity and acceleration constraints.

    Args:
        origin_ecef: Starting position in ECEF (x, y, z) meters
        scale_meters: Size of the flight volume in meters
        constraints: FlightConstraints object with limits
        time_delta: Time step between points in seconds
        num_waypoints: Number of waypoints for the path
        seed: Random seed for reproducibility

    Yields:
        Tuple of (time, position_ecef, velocity_ecef, acceleration_ecef)
    """
    if seed is not None:
        np.random.seed(seed)

    # Generate random waypoints in normalized space
    # waypoints is num_waypoints number of 3D arrays of random numbers.
    waypoints = np.random.rand(num_waypoints, 3)
    # initial point
    waypoints[0] = np.array([0.2, 0.2, 0.2])
    # destination point
    waypoints[-1] = np.array([0.8, 0.8, 0.8])

    # Smooth out middle waypoints to avoid sharp turns
    if num_waypoints > 2:
        for i in range(1, num_waypoints - 1):
            waypoints[i] = (waypoints[i - 1] + waypoints[i] + waypoints[i + 1]) / 3

    # Create path function
    path_func = create_constrained_path(waypoints, constraints)

    # Estimate required duration based on constraints
    # Compute path length in normalized space
    samples = np.linspace(0, 1, 100)
    positions = np.array([path_func(t)[0] for t in samples])
    # measure length of path (break it into tiny lines and measure each length)
    path_length_norm = np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1))
    path_length_ecef = path_length_norm * scale_meters

    # Duration needed to traverse path at max velocity
    min_duration = path_length_ecef / constraints.max_velocity
    # Add margin for acceleration/deceleration
    duration = min_duration * 1.5

    print(f"Path length: {path_length_ecef:.1f} m")
    print(f"Duration: {duration:.1f} s")
    print(f"Average speed: {path_length_ecef / duration:.1f} m/s")

    # Generate track
    t = 0.0
    prev_velocity = None

    while t <= duration:
        t_norm = t / duration

        # Get position, velocity, and acceleration in normalized space
        pos_norm, vel_norm, acc_norm = path_func(t_norm)

        # Transform to ECEF space
        pos_centered = (pos_norm - 0.5) * scale_meters
        pos_ecef = origin_ecef + pos_centered

        # Scale derivatives
        vel_ecef = vel_norm * scale_meters / duration
        acc_ecef = acc_norm * scale_meters / (duration ** 2)

        # Apply velocity constraint (simple clipping)
        speed = np.linalg.norm(vel_ecef)
        if speed > constraints.max_velocity:
            vel_ecef = vel_ecef * (constraints.max_velocity / speed)

        # Apply acceleration constraint
        if prev_velocity is not None:
            actual_accel = (vel_ecef - prev_velocity) / time_delta
            accel_mag = np.linalg.norm(actual_accel)

            if accel_mag > constraints.max_acceleration:
                # Limit acceleration
                actual_accel = actual_accel * (constraints.max_acceleration / accel_mag)
                vel_ecef = prev_velocity + actual_accel * time_delta
                acc_ecef = actual_accel

        yield t, pos_ecef, vel_ecef, acc_ecef

        prev_velocity = vel_ecef.copy()
        t += time_delta


def plot_track(data: list, constraints: FlightConstraints):
    """
    Plot the 3D track with velocity-based coloring.

    Args:
        data: List of dictionaries with 'position', 'speed', etc.
        constraints: FlightConstraints for reference in title
    """
    positions = np.array([d['position'] for d in data])
    speeds = np.array([d['speed'] for d in data])

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')

    # Create scatter plot with velocity-based colors
    scatter = ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2],
                         c=speeds, cmap='jet', s=20, alpha=0.8)

    # Plot the path as a line
    ax.plot(positions[:, 0], positions[:, 1], positions[:, 2],
            'k-', linewidth=0.5, alpha=0.3)

    # Mark start and end points
    ax.scatter([positions[0, 0]], [positions[0, 1]], [positions[0, 2]],
               c='green', s=200, marker='o', edgecolors='black', linewidths=2,
               label='Start', zorder=5)
    ax.scatter([positions[-1, 0]], [positions[-1, 1]], [positions[-1, 2]],
               c='red', s=200, marker='s', edgecolors='black', linewidths=2,
               label='End', zorder=5)

    # Add colorbar for velocity
    cbar = plt.colorbar(scatter, ax=ax, pad=0.1, shrink=0.8)
    cbar.set_label('Speed (m/s)', rotation=270, labelpad=20)

    # Set labels and title
    ax.set_xlabel('ECEF X (m)')
    ax.set_ylabel('ECEF Y (m)')
    ax.set_zlabel('ECEF Z (m)')
    ax.set_title(f'3D Flight Path (Max Velocity: {constraints.max_velocity} m/s)')
    ax.legend()

    plt.tight_layout()
    plt.show()


def print_sample_points(data: List[Dict]):
    print("\nSample points:")


    for i in [0, len(data) // 4, len(data) // 2, 3 * len(data) // 4, -1]:
        d = data[i]
    print(f"t={d['time']:6.1f}s: speed={d['speed']:6.2f} m/s, "
          f"accel={d['accel_mag']:6.2f} m/s²")

    # Validate constraints
    print("\n" + "=" * 60)
    print("Constraint Validation:")
    print("=" * 60)
    speeds = [d['speed'] for d in data]
    accels = [d['accel_mag'] for d in data]

    print(f"Max speed:        {max(speeds):6.2f} m/s (limit: {drone_constraints.max_velocity} m/s)")
    print(f"Max acceleration: {max(accels):6.2f} m/s² (limit: {drone_constraints.max_acceleration} m/s²)")
    print(f"Avg speed:        {np.mean(speeds):6.2f} m/s")

    if max(speeds) > drone_constraints.max_velocity * 1.01:
        print("⚠️  VELOCITY CONSTRAINT VIOLATED!")
    else:
        print("✓ Velocity constraint satisfied")

    if max(accels) > drone_constraints.max_acceleration * 1.01:
        print("⚠️  ACCELERATION CONSTRAINT VIOLATED!")
    else:
        print("✓ Acceleration constraint satisfied")

    # Plot the track
    print("\nGenerating 3D visualization...")




# Example usage with constraint validation
if __name__ == "__main__":
    # Define realistic constraints for a small drone
    drone_constraints = FlightConstraints(
        max_velocity=30.0,  # 30 m/s (~67 mph)
        max_acceleration=15.0,  # 15 m/s² (~1.5g)
        max_jerk=30.0  # Smooth changes
    )

    # Origin point
    # origin = np.array([6378137.0, 0.0, 0.0])
    boise_ecef = np.array([-2042359.37, -4150317.47, 4377856.4])

    print("Generating constrained track...")
    print(f"Max velocity: {drone_constraints.max_velocity} m/s")
    print(f"Max acceleration: {drone_constraints.max_acceleration} m/s²")
    print()

    gen = track_generator_constrained(
        origin_ecef=boise_ecef,
        scale_meters=5000.0,
        constraints=drone_constraints,
        time_delta=0.5,  # 0.5 second samples
        num_waypoints=8,
        # seed=43
    )

    # Collect and analyze track
    data = []
    for t, pos, vel, acc in gen:
        data.append({
            'time': t,
            'position': pos,
            'velocity': vel,
            'acceleration': acc,
            'speed': np.linalg.norm(vel),
            'accel_mag': np.linalg.norm(acc)
        })

    print_sample_points(data)
    plot_track(data, drone_constraints)




# def compute_velocity_profile(
#         path_func: Callable,
#         duration: float,
#         scale: float,
#         constraints: FlightConstraints,
#         num_samples: int = 1000
# ) -> Tuple[np.ndarray, np.ndarray]:
#     """
#     Compute a velocity profile that respects constraints.
#
#     Returns (times, velocities) where velocities are speed limits at each time.
#     """
#     times = np.linspace(0, duration, num_samples)
#     velocities = np.zeros(num_samples)
#
#     for i, t in enumerate(times):
#         t_norm = t / duration
#         _, vel_norm, acc_norm = path_func(t_norm)
#
#         # Scale to ECEF space
#         vel_ecef = vel_norm * scale / duration
#         acc_ecef = acc_norm * scale / (duration ** 2)
#
#         # Compute speeds
#         speed = np.linalg.norm(vel_ecef)
#         acc_mag = np.linalg.norm(acc_ecef)
#
#         # Limit based on constraints
#         max_speed_from_accel = np.sqrt(constraints.max_acceleration * scale)
#         velocities[i] = min(speed, constraints.max_velocity, max_speed_from_accel)
#
#     return times, velocities
