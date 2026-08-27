#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

import logging
import time
from dataclasses import dataclass
from typing import Callable, Tuple

import numpy as np
import pymap3d as pm

from .io import Publisher
from .tracks import track_generator

logger = logging.getLogger(__name__)


@dataclass
class TrackConfig:
    """Everything a run needs that is not specific to the track shape."""

    origin_lla: np.ndarray
    marker_lla: Tuple[float, float, float] | None
    scale_meters: float
    vert_scale_meters: float
    duration: float
    step_delta: float
    ip: str
    port: int
    plot: bool
    loop: bool | None

    def __post_init__(self):
        # origin_lla arrives as a tuple from click and as an ndarray from the
        # default, and downstream code both indexes and unpacks it. Settle on
        # one type here rather than at every use.
        self.origin_lla = np.asarray(self.origin_lla, dtype=float)

        # --loop is tri-state: unset means "whatever suits the mode", which is
        # loop forever when headless and play once in the plot window.
        if self.loop is None:
            self.loop = not self.plot


def run_track(path_func: Callable[[float], np.ndarray], cfg: TrackConfig) -> None:
    """Sample a path into the flight volume, then publish it (and optionally plot it)."""
    enu_positions = np.array(
        [
            enu
            for _, enu in track_generator(
                origin_lla=cfg.origin_lla,
                scale_meters=cfg.scale_meters,
                vert_scale_meters=cfg.vert_scale_meters,
                duration_seconds=cfg.duration,
                step_delta=cfg.step_delta,
                path_func=path_func,
            )
        ]
    )

    distance_m = np.sum(np.linalg.norm(np.diff(enu_positions, axis=0), axis=1))
    logger.info("Generated %d points", len(enu_positions))
    logger.info("Distance traveled: %.1f m", distance_m)

    publisher = Publisher(ip=cfg.ip, port=cfg.port)
    try:
        if cfg.plot:
            _replay(enu_positions, cfg, publisher)
        else:
            _publish_headless(enu_positions, cfg, publisher)
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        publisher.close()


def _publish_headless(
    enu_positions: np.ndarray, cfg: TrackConfig, publisher: Publisher
) -> None:
    logger.info(
        "Running in headless mode — publishing %d positions (%s)",
        len(enu_positions),
        "looping until stopped" if cfg.loop else "single pass",
    )
    while True:
        for pos in enu_positions:
            lla = pm.enu2geodetic(*pos, *cfg.origin_lla)
            publisher.publish_nowait(*lla)
            time.sleep(cfg.step_delta)
        if not cfg.loop:
            return


def _replay(enu_positions: np.ndarray, cfg: TrackConfig, publisher: Publisher) -> None:
    # Imported here so headless runs never pay for matplotlib.
    from .replay import ReplayPlotterSender

    plot = ReplayPlotterSender(
        enu_positions=enu_positions,
        origin_lla=cfg.origin_lla,
        publisher=publisher,
        interval_ms=cfg.step_delta * 1_000,
        repeat=cfg.loop,
    )
    plot.plot_positions()
