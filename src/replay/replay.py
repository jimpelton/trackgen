import json
import time
from typing import Iterable, Tuple

import numpy as np
import pymap3d
import zmq


def replay_track(
    track: Iterable[Tuple[float, np.ndarray]],
    endpoint: str = "tcp://*:5556",
    topic: str = "drone",
) -> None:
    """Replay a track over a ZMQ PUB socket at 10Hz, publishing lat/lon/alt as JSON.

    Args:
        track: Iterable of (time, position_ecef) tuples.
        endpoint: ZMQ endpoint to bind the PUB socket to.
        topic: ZMQ topic string for message filtering.
    """
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.bind(endpoint)

    # Allow subscribers time to connect
    time.sleep(0.5)

    tick_interval = 0.1  # 10Hz

    for t, pos_ecef in track:
        lat, lon, alt = pymap3d.ecef2geodetic(pos_ecef[0], pos_ecef[1], pos_ecef[2])

        message = json.dumps({
            "time": round(t, 3),
            "lat": round(float(lat), 7),
            "lon": round(float(lon), 7),
            "alt": round(float(alt), 3),
        })

        pub.send_string(f"{topic} {message}")
        print(f"t={t:6.1f}s  lat={lat:.5f}  lon={lon:.5f}  alt={alt:.1f}m")

        time.sleep(tick_interval)

    pub.close()
    ctx.term()
