
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

