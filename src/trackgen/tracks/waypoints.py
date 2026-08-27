#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

# Sinusoidal path (smooth figure-8 style)
from dataclasses import dataclass
from typing import Tuple, Final

import numpy as np


def sinusoidal_path(t: float) -> np.ndarray:
    return np.array(
        [
            0.5 + 0.3 * np.sin(2 * np.pi * t),
            0.5 + 0.3 * np.sin(4 * np.pi * t),
            0.5 + 0.2 * np.sin(3 * np.pi * t),
        ]
    )


# Circular climbing path
def spiral_path(t: float) -> np.ndarray:
    angle = 4 * np.pi * t
    return np.array(
        [0.5 + 0.4 * np.cos(angle), 0.5 + 0.4 * np.sin(angle), t]  # Linear climb
    )


_RANDOM_SEED: Final[None] = None


@dataclass
class Waypoints:
    seed: int
    t_waypoints: np.ndarray
    waypoints: np.ndarray


def create_waypoints(num_waypoints: int, seed: int | None = _RANDOM_SEED) -> Waypoints:
    """Create random waypoints in normalized space"""
    if seed is None:
        seed = np.random.randint(0, 2**32 - 1)

    rng = np.random.default_rng(seed)

    # Create random sample points
    t_waypoints = np.linspace(0, 1, num_waypoints)

    # Create the waypoints themselves
    waypoints = rng.random((num_waypoints, 3))

    return Waypoints(seed, t_waypoints, waypoints)
