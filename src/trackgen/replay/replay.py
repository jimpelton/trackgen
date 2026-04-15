from typing import Tuple, Collection

import zmq
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from ..io import Publisher


class ReplayPlotterSender:
    def __init__(
        self,
        positions: Collection[Tuple[float, float, float]],
        times: Collection[float],
        publisher: Publisher | None = None,
        interval_ms: float = 50,
    ):
        self._curr_pos_marker = None
        self._fig = None  # keep a reference for redraws
        self._publisher = publisher
        self._positions = positions
        self._times = times
        self._interval = interval_ms

    def _animate(self, frame_idx):
        pos = self._positions[frame_idx]
        t = self._times[frame_idx]

        # print(f"t={t:6.1f}s: ECEF {pos}")
        self._curr_pos_marker.set_data_3d([pos[0]], [pos[1]], [pos[2]])

        if self._publisher is not None:
            try:
                self._publisher.publish_nowait(pos_ecef=pos)
            except zmq.Again:
                pass  # skip, no publisher ready yet

        return (self._curr_pos_marker,)

    def plot_positions(self):
        self._fig = plt.figure(figsize=(10, 8))
        ax = self._fig.add_subplot(111, projection="3d")

        # flight path
        ax.plot(
            self._positions[:, 0],
            self._positions[:, 1],
            self._positions[:, 2],
            "b-",
            linewidth=2,
            label="Flight Path",
        )
        # start marker
        ax.plot(
            [self._positions[0, 0]],
            [self._positions[0, 1]],
            [self._positions[0, 2]],
            "go",
            markersize=10,
            label="Start",
        )
        # end marker
        ax.plot(
            [self._positions[-1, 0]],
            [self._positions[-1, 1]],
            [self._positions[-1, 2]],
            "rs",
            markersize=10,
            label="End",
        )

        (self._curr_pos_marker,) = ax.plot(
            [self._positions[0, 0]],
            [self._positions[0, 1]],
            [self._positions[0, 2]],
            "r*",
            markersize=10,
            label="Current Position",
        )

        ax.set_xlabel("ECEF X (m)")
        ax.set_ylabel("ECEF Y (m)")
        ax.set_zlabel("ECEF Z (m)")
        ax.set_title("3D Flight Path Visualization")
        ax.legend()

        self._animation = FuncAnimation(
            self._fig,
            self._animate,
            frames=len(self._positions),
            interval=self._interval,  # ~20fps, adjust to match your data rate
            blit=True,
            repeat=False,
        )

        plt.show()
