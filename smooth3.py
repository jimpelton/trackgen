import numpy as np
from typing import Generator, Tuple, Callable, Optional, List, Dict
from scipy.interpolate import CubicSpline
from dataclasses import dataclass
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable


@dataclass
class FlightConstraints:
    """Physical constraints for realistic flight."""
    max_velocity: float = 100.0  # m/s
    max_acceleration: float = 20.0  # m/s²
    max_jerk: float = 50.0  # m/s³


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
        velocity = np.array([s(t_clamped, 1) for s in pos_splines])
        acceleration = np.array([s(t_clamped, 2) for s in pos_splines])

        return position, velocity, acceleration

    return evaluate


def track_generator_constrained(
        origin_ecef: np.ndarray,
        scale_meters: float,
        constraints: FlightConstraints,
        time_delta: float,
        num_waypoints: int = 6,
        seed: Optional[int] = None
) -> Generator[Tuple[float, np.ndarray, np.ndarray, np.ndarray], None, None]:
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
    waypoints = np.random.rand(num_waypoints, 3)
    waypoints[0] = np.array([0.2, 0.2, 0.2])
    waypoints[-1] = np.array([0.8, 0.8, 0.8])

    # Smooth out middle waypoints to avoid sharp turns
    if num_waypoints > 2:
        for i in range(1, num_waypoints - 1):
            waypoints[i] = (waypoints[i - 1] + waypoints[i] + waypoints[i + 1]) / 3

    # Create path function
    path_func = create_constrained_path(waypoints, constraints)

    # Estimate required duration based on constraints
    samples = np.linspace(0, 1, 100)
    positions = np.array([path_func(t)[0] for t in samples])
    path_length_norm = np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1))
    path_length_ecef = path_length_norm * scale_meters

    min_duration = path_length_ecef / constraints.max_velocity
    duration = min_duration * 1.5

    print(f"Path length: {path_length_ecef:.1f} m")
    print(f"Duration: {duration:.1f} s")
    print(f"Average speed: {path_length_ecef / duration:.1f} m/s")

    # Generate track
    t = 0.0
    prev_velocity = None

    while t <= duration:
        t_norm = t / duration

        pos_norm, vel_norm, acc_norm = path_func(t_norm)

        # Transform to ECEF space
        pos_centered = (pos_norm - 0.5) * scale_meters
        pos_ecef = origin_ecef + pos_centered

        vel_ecef = vel_norm * scale_meters / duration
        acc_ecef = acc_norm * scale_meters / (duration ** 2)

        # Apply velocity constraint
        speed = np.linalg.norm(vel_ecef)
        if speed > constraints.max_velocity:
            vel_ecef = vel_ecef * (constraints.max_velocity / speed)

        # Apply acceleration constraint
        if prev_velocity is not None:
            actual_accel = (vel_ecef - prev_velocity) / time_delta
            accel_mag = np.linalg.norm(actual_accel)

            if accel_mag > constraints.max_acceleration:
                actual_accel = actual_accel * (constraints.max_acceleration / accel_mag)
                vel_ecef = prev_velocity + actual_accel * time_delta
                acc_ecef = actual_accel

        yield (t, pos_ecef, vel_ecef, acc_ecef)

        prev_velocity = vel_ecef.copy()
        t += time_delta


def visualize_track(
        data: List[Dict],
        origin_ecef: np.ndarray,
        constraints: FlightConstraints,
        title: str = "Flight Track Visualization"
):
    """
    Visualize a 3D track with velocity color-coding.

    Args:
        data: List of dicts with keys 'time', 'position', 'velocity', 'acceleration', 'speed', 'accel_mag'
        origin_ecef: ECEF origin point (for converting to local coordinates)
        constraints: FlightConstraints for reference lines
        title: Plot title
    """
    # Extract data
    times = np.array([d['time'] for d in data])
    positions = np.array([d['position'] for d in data])
    speeds = np.array([d['speed'] for d in data])
    accels = np.array([d['accel_mag'] for d in data])

    # Convert to local coordinates (relative to origin)
    local_positions = positions - origin_ecef

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))

    # ============ 3D Trajectory Plot ============
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')

    # Create color map based on velocity
    norm = Normalize(vmin=0, vmax=constraints.max_velocity)
    colors = plt.cm.plasma(norm(speeds))

    # Plot trajectory as colored line segments
    for i in range(len(local_positions) - 1):
        ax1.plot(
            local_positions[i:i + 2, 0],
            local_positions[i:i + 2, 1],
            local_positions[i:i + 2, 2],
            color=colors[i],
            linewidth=2
        )

    # Mark start and end points
    ax1.scatter(*local_positions[0], color='green', s=200, marker='o',
                edgecolors='black', linewidths=2, label='Start', zorder=5)
    ax1.scatter(*local_positions[-1], color='red', s=200, marker='s',
                edgecolors='black', linewidths=2, label='End', zorder=5)

    # Add velocity direction arrows at intervals
    arrow_interval = max(1, len(data) // 10)
    for i in range(0, len(data), arrow_interval):
        pos = local_positions[i]
        vel = data[i]['velocity']
        vel_normalized = vel / (np.linalg.norm(vel) + 1e-6) * 200  # Scale for visibility
        ax1.quiver(pos[0], pos[1], pos[2],
                   vel_normalized[0], vel_normalized[1], vel_normalized[2],
                   color='black', alpha=0.3, arrow_length_ratio=0.3, linewidth=1)

    ax1.set_xlabel('X (m)', fontsize=10)
    ax1.set_ylabel('Y (m)', fontsize=10)
    ax1.set_zlabel('Z (m)', fontsize=10)
    ax1.set_title('3D Trajectory (colored by velocity)', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # Add colorbar for velocity
    sm = ScalarMappable(cmap=plt.cm.plasma, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax1, pad=0.1, shrink=0.8)
    cbar.set_label('Velocity (m/s)', fontsize=10)

    # ============ Velocity vs Time ============
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.plot(times, speeds, linewidth=2, label='Speed', color='blue')
    ax2.axhline(y=constraints.max_velocity, color='red', linestyle='--',
                linewidth=2, label=f'Max velocity ({constraints.max_velocity} m/s)')
    ax2.fill_between(times, 0, speeds, alpha=0.3, color='blue')
    ax2.set_xlabel('Time (s)', fontsize=10)
    ax2.set_ylabel('Speed (m/s)', fontsize=10)
    ax2.set_title('Velocity Profile', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_ylim(bottom=0)

    # ============ Acceleration vs Time ============
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.plot(times, accels, linewidth=2, label='Acceleration', color='orange')
    ax3.axhline(y=constraints.max_acceleration, color='red', linestyle='--',
                linewidth=2, label=f'Max acceleration ({constraints.max_acceleration} m/s²)')
    ax3.fill_between(times, 0, accels, alpha=0.3, color='orange')
    ax3.set_xlabel('Time (s)', fontsize=10)
    ax3.set_ylabel('Acceleration (m/s²)', fontsize=10)
    ax3.set_title('Acceleration Profile', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    ax3.set_ylim(bottom=0)

    # ============ Top-down view (X-Y plane) ============
    ax4 = fig.add_subplot(2, 2, 4)

    # Plot trajectory with velocity coloring
    for i in range(len(local_positions) - 1):
        ax4.plot(
            local_positions[i:i + 2, 0],
            local_positions[i:i + 2, 1],
            color=colors[i],
            linewidth=2
        )

    # Mark start and end
    ax4.scatter(local_positions[0, 0], local_positions[0, 1],
                color='green', s=200, marker='o', edgecolors='black',
                linewidths=2, label='Start', zorder=5)
    ax4.scatter(local_positions[-1, 0], local_positions[-1, 1],
                color='red', s=200, marker='s', edgecolors='black',
                linewidths=2, label='End', zorder=5)

    # Add velocity vectors
    for i in range(0, len(data), arrow_interval):
        pos = local_positions[i]
        vel = data[i]['velocity']
        vel_normalized = vel[:2] / (np.linalg.norm(vel[:2]) + 1e-6) * 200
        ax4.arrow(pos[0], pos[1], vel_normalized[0], vel_normalized[1],
                  head_width=100, head_length=150, fc='black', ec='black',
                  alpha=0.3, linewidth=1)

    ax4.set_xlabel('X (m)', fontsize=10)
    ax4.set_ylabel('Y (m)', fontsize=10)
    ax4.set_title('Top-Down View (X-Y plane)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    ax4.axis('equal')

    # Add overall title and statistics
    fig.suptitle(title, fontsize=14, fontweight='bold', y=0.98)

    stats_text = (
        f"Statistics:\n"
        f"Duration: {times[-1]:.1f} s  |  "
        f"Distance: {np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1)):.1f} m  |  "
        f"Avg Speed: {np.mean(speeds):.1f} m/s  |  "
        f"Max Speed: {np.max(speeds):.1f} m/s  |  "
        f"Max Accel: {np.max(accels):.1f} m/s²"
    )
    fig.text(0.5, 0.02, stats_text, ha='center', fontsize=10,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    return fig


# Example usage
if __name__ == "__main__":
    # Define realistic constraints for a racing drone
    drone_constraints = FlightConstraints(
        max_velocity=40.0,  # 40 m/s (~90 mph)
        max_acceleration=20.0,  # 20 m/s² (~2g)
        max_jerk=50.0
    )

    # Origin point
    origin = np.array([6378137.0, 0.0, 0.0])

    print("Generating constrained track...")
    print(f"Max velocity: {drone_constraints.max_velocity} m/s")
    print(f"Max acceleration: {drone_constraints.max_acceleration} m/s²")
    print()

    gen = track_generator_constrained(
        origin_ecef=origin,
        scale_meters=8000.0,
        constraints=drone_constraints,
        time_delta=0.5,
        num_waypoints=8,
        seed=42
    )

    # Collect track data
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

    print(f"\nGenerated {len(data)} track points")

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

    # Visualize the track
    print("\nGenerating visualization...")
    fig = visualize_track(data, origin, drone_constraints,
                          title="Racing Drone Flight Track")
    plt.show()