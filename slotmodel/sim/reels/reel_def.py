from __future__ import annotations

from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray


Reel: TypeAlias = NDArray[np.int16]
ReelSet: TypeAlias = tuple[Reel, ...]
ReelMatrix: TypeAlias = NDArray[np.int16]


def compile_reels(reels: ReelSet) -> ReelMatrix:
    """
    Stack a validated reel set into one numpy array.

    The returned array has shape ``(reel_count, reel_length)``.
    The current reel JSON format requires all reels to have equal length.
    """

    if not reels:
        raise ValueError("At least one reel is required.")

    reel_length = reels[0].size

    if reel_length == 0:
        raise ValueError("Reels cannot be empty.")

    for reel_index, reel in enumerate(reels):
        if reel.ndim != 1:
            raise ValueError(
                f"Reel {reel_index} must be one-dimensional."
            )

        if reel.dtype != np.int16:
            raise TypeError(
                f"Reel {reel_index} must have dtype int16, "
                f"not {reel.dtype}."
            )

        if reel.size != reel_length:
            raise ValueError(
                "All reels must have the same length. "
                f"Reel 0 has length {reel_length}, but reel "
                f"{reel_index} has length {reel.size}."
            )

    reel_matrix = np.stack(reels, axis=0)

    # The matrix represents game configuration and must not be edited
    # during a simulation.
    reel_matrix.flags.writeable = False

    return reel_matrix
