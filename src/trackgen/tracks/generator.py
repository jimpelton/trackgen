from typing import Generator, Tuple, Callable

import numpy as np


def track_generator(
        origin_lla: np.ndarray,
        scale_meters: float,
        duration_seconds: float,
        time_delta: float,
        path_func: Callable[[float], np.ndarray],
) -> Generator[Tuple[float, np.ndarray], None, None]:
    """
    Generate smooth ECEF track coordinates following a curved path.

    Args:
        origin_lla: Origin on the ground in (lat_deg, lon_deg, alt_meters)
        scale_meters: Size of the flight volume in meters (normalized space scaled to this)
        duration_seconds: Total duration of the track
        time_delta: Time step between points in seconds
        path_func: Callable path function(t) that maps [0,1] → [0,1]³

    Yields:
        Tuple of (time, position_enu) where position is always above origin altitude
    """

    t = 0.0
    while t <= duration_seconds:
        # Normalize time to [0, 1]
        t_norm = t / duration_seconds

        # Get position in normalized space [0,1]³
        pos_normalized = path_func(t_norm)

        # Map normalized space to ENU offsets:
        #   East/North centered on origin: [-scale/2, +scale/2]
        #   Up above ground: [0, scale_meters]
        east  = (pos_normalized[0] - 0.5) * scale_meters
        north = (pos_normalized[1] - 0.5) * scale_meters
        up    =  pos_normalized[2]         * scale_meters

        yield t, np.array([east, north, up])
        t += time_delta


# class Track:
#     def __init__(self, path_func: Callable[[float], np.ndarray]):
#         self._path_func = path_func
#
#         self._s0 = 0.0
#         self._v0 = 0.0