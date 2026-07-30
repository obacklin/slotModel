from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray

from slotmodel.sim.reels.reel_def import (
    ReelMatrix,
    ReelSet,
    compile_reels,
)


StopBatch: TypeAlias = NDArray[np.int32]
ScreenBatchArray: TypeAlias = NDArray[np.int16]
WindowOffsets: TypeAlias = NDArray[np.int32]


@dataclass(frozen=True, slots=True)
class ScreenModel:
    """
    Simulation-ready reel strips and visible-window geometry.

    ``reels`` has shape ``(reel_count, reel_length)``.
    ``window_offsets`` has shape ``(row_count,)``.

    A stop position identifies offset zero. With offsets ``[0, 1, 2]``,
    the stop is the symbol displayed in the top row and the next two
    strip positions appear below it.
    """

    reels: ReelMatrix
    window_offsets: WindowOffsets

    @classmethod
    def from_reels(
        cls,
        reels: ReelSet,
        window_offsets: ArrayLike,
    ) -> ScreenModel:
        reel_matrix = compile_reels(reels)
        offsets = _validate_window_offsets(window_offsets)
        return cls(reels=reel_matrix, window_offsets=offsets)

    @property
    def reel_count(self) -> int:
        return int(self.reels.shape[0])

    @property
    def reel_length(self) -> int:
        return int(self.reels.shape[1])

    @property
    def row_count(self) -> int:
        return int(self.window_offsets.size)


@dataclass(frozen=True, slots=True)
class SpinBatch:
    """
    A batch of base-game outcomes.

    ``stops`` has shape ``(batch_size, reel_count)``.
    ``screens`` has shape ``(batch_size, row_count, reel_count)``.
    """

    stops: StopBatch
    screens: ScreenBatchArray

    def __post_init__(self) -> None:
        if self.stops.ndim != 2:
            raise ValueError("stops must be a two-dimensional array.")

        if self.screens.ndim != 3:
            raise ValueError("screens must be a three-dimensional array.")

        if self.stops.shape[0] != self.screens.shape[0]:
            raise ValueError(
                "stops and screens must contain the same number of spins."
            )

        if self.stops.shape[1] != self.screens.shape[2]:
            raise ValueError(
                "The stop reel count must match the screen reel count."
            )

    @property
    def size(self) -> int:
        return int(self.stops.shape[0])

    @property
    def reel_count(self) -> int:
        return int(self.stops.shape[1])

    @property
    def row_count(self) -> int:
        return int(self.screens.shape[1])


def _validate_window_offsets(
    window_offsets: ArrayLike,
) -> WindowOffsets:
    raw_offsets = np.asarray(window_offsets)

    if raw_offsets.ndim != 1 or raw_offsets.size == 0:
        raise ValueError(
            "window_offsets must be a non-empty one-dimensional array."
        )

    if not np.issubdtype(raw_offsets.dtype, np.integer):
        raise TypeError("window_offsets must contain integers.")

    offsets = raw_offsets.astype(np.int32, copy=True)
    offsets.flags.writeable = False

    return offsets


def sample_stops(
    model: ScreenModel,
    batch_size: int,
    rng: np.random.Generator,
) -> StopBatch:
    """Sample independent, uniformly distributed stops for each reel."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")

    return rng.integers(
        low=0,
        high=model.reel_length,
        size=(batch_size, model.reel_count),
        dtype=np.int32,
    )


def build_screens(
    model: ScreenModel,
    stops: ArrayLike,
) -> ScreenBatchArray:
    """
    Build a batch of screens from predetermined stop positions.

    The output layout is ``(spin, row, reel)``. Reel strips wrap around
    with modular indexing.
    """

    raw_stops = np.asarray(stops)

    if raw_stops.ndim != 2:
        raise ValueError(
            "stops must have shape (batch_size, reel_count)."
        )

    if not np.issubdtype(raw_stops.dtype, np.integer):
        raise TypeError("stops must contain integers.")

    if raw_stops.shape[1] != model.reel_count:
        raise ValueError(
            f"Expected {model.reel_count} stop columns, "
            f"received {raw_stops.shape[1]}."
        )

    stop_array = raw_stops.astype(np.int32, copy=False)

    if np.any(stop_array < 0):
        raise ValueError("Stop positions cannot be negative.")

    if np.any(stop_array >= model.reel_length):
        raise ValueError(
            "A stop position is outside the reel strip. "
            f"Valid positions are 0 through {model.reel_length - 1}."
        )

    batch_size = stop_array.shape[0]

    screens = np.empty(
        (batch_size, model.row_count, model.reel_count),
        dtype=np.int16,
    )

    reel_indices = np.arange(model.reel_count)

    # Looping over the small number of visible rows avoids allocating one
    # large (batch, row, reel) int32 index tensor.
    for row_index, offset in enumerate(model.window_offsets):
        strip_indices = (
            stop_array + int(offset)
        ) % model.reel_length

        screens[:, row_index, :] = model.reels[
            reel_indices,
            strip_indices,
        ]

    return screens


def spin_batch(
    model: ScreenModel,
    batch_size: int,
    rng: np.random.Generator,
) -> SpinBatch:
    """Sample reel stops and construct the corresponding screen batch."""

    stops = sample_stops(
        model=model,
        batch_size=batch_size,
        rng=rng,
    )

    screens = build_screens(
        model=model,
        stops=stops,
    )

    return SpinBatch(stops=stops, screens=screens)


def iter_spin_batches(
    model: ScreenModel,
    total_spins: int,
    batch_size: int,
    rng: np.random.Generator,
) -> Iterator[SpinBatch]:
    """Yield a large simulation as bounded-memory batches."""

    if total_spins < 0:
        raise ValueError("total_spins cannot be negative.")

    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")

    completed_spins = 0

    while completed_spins < total_spins:
        current_batch_size = min(
            batch_size,
            total_spins - completed_spins,
        )

        yield spin_batch(
            model=model,
            batch_size=current_batch_size,
            rng=rng,
        )

        completed_spins += current_batch_size
