# Sinusoidal path (smooth figure-8 style)
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


# Racing drone
racing_drone = FlightConstraints(
    max_velocity=50.0,       # 180 km/h
    max_acceleration=30.0,   # ~3g
    max_jerk=100.0
)

# Commercial airliner
airliner = FlightConstraints(
    max_velocity=250.0,      # 900 km/h cruise
    max_acceleration=5.0,    # Gentle maneuvers
    max_jerk=2.0
)

# Bird (peregrine falcon)
falcon = FlightConstraints(
    max_velocity=90.0,       # Diving speed ~320 km/h
    max_acceleration=25.0,
    max_jerk=50.0
)