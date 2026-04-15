import json
import logging
import pymap3d
import zmq

logger = logging.getLogger(__name__)

class Publisher:
    def __init__(self, ip:str, port:int = 5557, topic:str = "telemetry"):
        self._context = zmq.Context()
        self._pub = self._context.socket(zmq.PUB)
        self._topic: bytes = topic.encode()

        endpoint = f"tcp://{ip}:{port}"
        self._pub.bind(endpoint)

    def publish_nowait(self, pos_ecef:tuple[float, float, float]):
        lat, lon, alt = pymap3d.ecef2geodetic(pos_ecef[0], pos_ecef[1], pos_ecef[2])

        message = json.dumps({
            "lat": round(float(lat), 7),
            "lon": round(float(lon), 7),
            "alt": round(float(alt), 3),
        })

        self._pub.send_multipart([self._topic, message.encode()], flags=zmq.NOBLOCK)

    def close(self):
        logger.info("Closing publisher")
        self._pub.close()
        self._context.term()
        logger.info("Publisher closed")
