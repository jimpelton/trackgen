# Sinusoidal path (smooth figure-8 style)
from typing import Tuple

import numpy as np


def sinusoidal_path(t: float) -> np.ndarray:
    return np.array([
        0.5 + 0.3 * np.sin(2 * np.pi * t),
        0.5 + 0.3 * np.sin(4 * np.pi * t),
        0.5 + 0.2 * np.sin(3 * np.pi * t)
    ])

# Circular climbing path
def spiral_path(t: float) -> np.ndarray:
    angle = 4 * np.pi * t
    return np.array([
        0.5 + 0.4 * np.cos(angle),
        0.5 + 0.4 * np.sin(angle),
        t  # Linear climb
    ])




RANDOM_SEED = None
def create_waypoints(num_waypoints: int, seed: int | None = RANDOM_SEED) -> Tuple[np.ndarray, np.ndarray]:
    if seed is not None:
        np.random.seed(seed)

    # Create random waypoints in normalized space
    t_waypoints = np.linspace(0, 1, num_waypoints)
    waypoints = np.random.rand(num_waypoints, 3)

    # Ensure start and end are within bounds
    waypoints[0] = np.array([0.1, 0.1, 0.9])
    waypoints[-1] = np.array([0.9, 0.9, 0.9])

    return t_waypoints, waypoints
