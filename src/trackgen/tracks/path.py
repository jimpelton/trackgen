
#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

from typing import Callable

import numpy as np
from scipy.interpolate import CubicSpline

def create_smooth_path(s_waypoints: np.ndarray, waypoints: np.ndarray) -> Callable[[float], np.ndarray]:
    """
    Create a smooth 3D path function that maps t ∈ [0,1] to positions ∈ [0,1]³.

    :param t_waypoints: Array of spline independent variable values (normalized to [0,1])
    :param waypoints: Array of dependent variable values (positions) (normalized to [0,1]³)
    :return: Smooth path function that maps s ∈ [0,1] to positions ∈ [0,1]³
    """

    # Create cubic splines for each dimension
    splines = [CubicSpline(s_waypoints, waypoints[:, i], bc_type='natural')
               for i in range(3)]

    def path(s: float) -> np.ndarray:
        """Evaluate path at s ∈ [0,1]"""
        s_clamped = np.clip(s, 0, 1)
        return np.array([spline(s_clamped) for spline in splines])

    return path


def create_circular_path(radius: float = 0.4, height: float = 0.5,
                          revolutions: float = 1.0) -> Callable[[float], np.ndarray]:
    """
    Create a circular 3D path function centered on the origin at a fixed altitude.

    :param radius: Circle radius in normalized [0,1] space (max 0.5 to stay in bounds)
    :param height: Fixed normalized altitude ∈ [0,1]
    :param revolutions: Number of full loops as s goes 0 → 1
    :return: Path function that maps s ∈ [0,1] to positions ∈ [0,1]³
    """

    def path(s: float) -> np.ndarray:
        """Evaluate path at s ∈ [0,1]"""
        s_clamped = np.clip(s, 0, 1)
        theta = 2 * np.pi * revolutions * s_clamped
        return np.array([0.5 + radius * np.cos(theta),
                          0.5 + radius * np.sin(theta),
                          height])

    return path


def create_grid_path(num_lines: int = 5, height: float = 0.5,
                      margin: float = 0.1) -> Callable[[float], np.ndarray]:
    """
    Create a lawnmower (boustrophedon) 3D path that sweeps back and forth across
    the [0,1]² plane at a fixed altitude, like a grid survey pattern. The path
    retraces itself on the way back, so it ends where it started and can be
    looped seamlessly (e.g. in headless mode).

    :param num_lines: Number of back-and-forth passes across the grid
    :param height: Fixed normalized altitude ∈ [0,1]
    :param margin: Inset from the [0,1] bounds so the sweep stays within the volume
    :return: Path function that maps s ∈ [0,1] to positions ∈ [0,1]³
    """

    low = margin
    high = 1.0 - margin

    def sweep(u: float) -> np.ndarray:
        """Evaluate the one-way grid sweep at u ∈ [0,1]"""
        segment = np.clip(u * num_lines, 0, num_lines - 1e-9)
        line_index = int(np.floor(segment))
        local_t = segment - line_index

        # Alternate sweep direction each line so consecutive passes connect
        s_dir = local_t if line_index % 2 == 0 else 1.0 - local_t
        x = low + s_dir * (high - low)
        y = low + (line_index / max(num_lines - 1, 1)) * (high - low)

        return np.array([x, y, height])

    def path(s: float) -> np.ndarray:
        """Evaluate path at s ∈ [0,1]; retraces the sweep on the second half"""
        s_clamped = np.clip(s, 0, 1)
        # sweep out over [0,0.5], then back over [0.5,1] (triangular wave shaped).
        u = 2.0 * s_clamped if s_clamped <= 0.5 else 2.0 * (1.0 - s_clamped)
        return sweep(u)

    return path