def track_generator(
        origin_ecef: np.ndarray,
        scale_meters: float,
        duration_seconds: float,
        time_delta: float,
        path_func: Callable[[float], np.ndarray] = None,
        t_waypoints: np.ndarray,
        waypoints: np.ndarray,
        # num_waypoints: int = 5,
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
        path_func = create_smooth_path(t_waypoints, waypoints, seed)

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

