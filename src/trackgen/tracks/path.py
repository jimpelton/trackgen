#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

from typing import Callable

import numpy as np
from scipy.interpolate import CubicSpline


def create_smooth_path(
    s_waypoints: np.ndarray, waypoints: np.ndarray
) -> Callable[[float], np.ndarray]:
    """
    Create a smooth 3D path function that maps t ∈ [0,1] to positions ∈ [0,1]³.

    :param t_waypoints: Array of spline independent variable values (normalized to [0,1])
    :param waypoints: Array of dependent variable values (positions) (normalized to [0,1]³)
    :return: Smooth path function that maps s ∈ [0,1] to positions ∈ [0,1]³
    """

    # Create cubic splines for each dimension
    splines = [
        CubicSpline(s_waypoints, waypoints[:, i], bc_type="natural") for i in range(3)
    ]

    def path(s: float) -> np.ndarray:
        """Evaluate path at s ∈ [0,1]"""
        s_clamped = np.clip(s, 0, 1)
        return np.array([spline(s_clamped) for spline in splines])

    return path


def create_circular_path(
    radius: float = 0.4, height: float = 0.5, revolutions: float = 1.0
) -> Callable[[float], np.ndarray]:
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
        return np.array(
            [0.5 + radius * np.cos(theta), 0.5 + radius * np.sin(theta), height]
        )

    return path


def create_grid_path(
    num_lines: int = 5, height: float = 0.5, margin: float = 0.1
) -> Callable[[float], np.ndarray]:
    """
    Create a lawnmower (boustrophedon) 3D path that sweeps back and forth across
    the [0,1]² plane at a fixed altitude, like a grid survey pattern. Short
    connector legs join the end of each pass to the start of the next, and u is
    parameterized by arc length so samples land on every leg. The path retraces
    itself on the way back, so it ends where it started and can be looped
    seamlessly (e.g. in headless mode).

    :param num_lines: Number of back-and-forth passes across the grid
    :param height: Fixed normalized altitude ∈ [0,1]
    :param margin: Inset from the [0,1] bounds so the sweep stays within the volume
    :return: Path function that maps s ∈ [0,1] to positions ∈ [0,1]³
    """

    low = margin
    high = 1.0 - margin

    # Explicit waypoints for the one-way sweep: num_lines passes joined by
    # num_lines - 1 short connectors at alternating ends (boustrophedon).
    ys = np.linspace(low, high, num_lines)
    leg_waypoints: list[np.ndarray] = []
    for i, y in enumerate(ys):
        x_start = low if i % 2 == 0 else high
        x_end = high if i % 2 == 0 else low
        # x_start coincides with the previous pass's end: this is the connector
        leg_waypoints.append(np.array([x_start, y, height]))
        leg_waypoints.append(np.array([x_end, y, height]))

    # Cumulative arc length for constant-speed parameterization
    diffs = np.diff(np.array(leg_waypoints), axis=0)
    cumulative = np.concatenate(([0.0], np.cumsum(np.linalg.norm(diffs, axis=1))))
    total_length = cumulative[-1]

    def sweep(u: float) -> np.ndarray:
        """Evaluate the one-way grid sweep at u ∈ [0,1] (arc-length parameterized)"""
        target = np.clip(u, 0.0, 1.0) * total_length
        # Piecewise-linear interpolation across the legs
        for i in range(len(cumulative) - 1):
            if target <= cumulative[i + 1] or i == len(cumulative) - 2:
                leg_t = (target - cumulative[i]) / (cumulative[i + 1] - cumulative[i])
                leg_t = np.clip(leg_t, 0.0, 1.0)
                return leg_waypoints[i] + leg_t * (
                    leg_waypoints[i + 1] - leg_waypoints[i]
                )
        return leg_waypoints[-1]

    def path(s: float) -> np.ndarray:
        """Evaluate path at s ∈ [0,1]; retraces the sweep on the second half"""
        s_clamped = np.clip(s, 0, 1)
        # sweep out over [0,0.5], then back over [0.5,1] (triangular wave shaped).
        u = 2.0 * s_clamped if s_clamped <= 0.5 else 2.0 * (1.0 - s_clamped)
        return sweep(u)

    return path
