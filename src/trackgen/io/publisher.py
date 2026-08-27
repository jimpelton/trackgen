#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

import logging
import time

import zmq
import uuid

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BaseTelemetryMessage(BaseModel):
    version: str
    timestamp_us: int = Field(default_factory=lambda: int(time.time_ns() / 1_000))
    name: str
    msg_id: uuid.UUID = Field(default_factory=uuid.uuid4)


class AircraftTelemetryV1(BaseTelemetryMessage):
    version: str = "v1"
    name: str = "aircraft_telemetry"
    lat_deg: float  # WGS-84 degrees
    lon_deg: float  # WGS-84 degrees
    alt_hae_m: float  # HAE meters


class Publisher:
    def __init__(self, ip: str, port: int = 5557, topic: str = "telemetry"):
        self._context = zmq.Context()
        self._pub = self._context.socket(zmq.PUB)
        self._topic: bytes = topic.encode()

        endpoint = f"tcp://{ip}:{port}"
        self._pub.bind(endpoint)

    def publish_nowait(self, lat, lon, alt):
        message = AircraftTelemetryV1(
            lat_deg=round(float(lat), 7),
            lon_deg=round(float(lon), 7),
            alt_hae_m=round(float(alt), 3),
        )
        self._pub.send_multipart(
            [self._topic, message.model_dump_json().encode()], flags=zmq.NOBLOCK
        )

    def close(self):
        logger.info("Closing publisher")
        self._pub.close()
        self._context.term()
        logger.info("Publisher closed")
