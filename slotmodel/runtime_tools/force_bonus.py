from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

from slotmodel.sim.eval import scatter_bonus_trigger_mask
from slotmodel.sim.reels import Symbol, read_reels
from slotmodel.sim.screens import (
    ScreenModel,
    SpinBatch,
    StopBatch,
    build_screens,
    sample_stops as sample_base_stops,
)


ScatterPositions: TypeAlias = tuple[NDArray[np.int32], ...]


@dataclass(frozen=True, slots=True)
class BonusStopGenerator:
    """
    Generate forced bonus-triggering spins.

    A normal stop is first sampled on every reel. A required number
    of scatter-bearing reels is then selected, and each selected stop
    is moved forward to the next scatter on that reel. The scatter is
    placed at a random visible row.

    This is intended for forced feature entry, not for sampling the
    natural conditional distribution of bonus-triggering spins.
    """

    model: ScreenModel
    minimum_scatter_count: int = 3

    _scatter_positions: ScatterPositions = field(
        init=False,
        repr=False,
    )
    _eligible_reels: NDArray[np.int32] = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.minimum_scatter_count <= 0:
            raise ValueError(
                "minimum_scatter_count must be positive."
            )

        if self.minimum_scatter_count > self.model.reel_count:
            raise ValueError(
                "minimum_scatter_count cannot exceed reel_count."
            )

        scatter_positions = tuple(
            np.flatnonzero(
                reel == int(Symbol.SCATTER)
            ).astype(np.int32)
            for reel in self.model.reels
        )

        for positions in scatter_positions:
            positions.flags.writeable = False

        eligible_reels = np.asarray(
            [
                reel_index
                for reel_index, positions
                in enumerate(scatter_positions)
                if positions.size > 0
            ],
            dtype=np.int32,
        )

        eligible_reels.flags.writeable = False

        if eligible_reels.size < self.minimum_scatter_count:
            raise ValueError(
                "Not enough reels contain scatter symbols to "
                "guarantee the requested bonus trigger."
            )

        object.__setattr__(
            self,
            "_scatter_positions",
            scatter_positions,
        )
        object.__setattr__(
            self,
            "_eligible_reels",
            eligible_reels,
        )

    @classmethod
    def from_current_reels(
        cls,
        window_offsets: tuple[int, ...] = (0, 1, 2),
        minimum_scatter_count: int = 3,
    ) -> BonusStopGenerator:
        """Create a generator from the currently configured reel set."""

        reels = read_reels()

        model = ScreenModel.from_reels(
            reels=reels,
            window_offsets=window_offsets,
        )

        return cls(
            model=model,
            minimum_scatter_count=minimum_scatter_count,
        )

    def sample_stops(
        self,
        rng: np.random.Generator,
    ) -> StopBatch:
        """
        Return one forced bonus-triggering stop set.

        The returned array has the normal StopBatch shape:

            (1, reel_count)
        """

        stops = sample_base_stops(
            model=self.model,
            batch_size=1,
            rng=rng,
        )

        selected_reels = rng.choice(
            self._eligible_reels,
            size=self.minimum_scatter_count,
            replace=False,
        )

        for selected_reel in selected_reels:
            reel_index = int(selected_reel)

            initial_stop = int(
                stops[0, reel_index]
            )

            scatter_positions = (
                self._scatter_positions[reel_index]
            )

            # Distance going forward around the circular reel
            # from the initially sampled stop to each scatter.
            forward_distances = (
                scatter_positions - initial_stop
            ) % self.model.reel_length

            # Select the first scatter encountered when moving
            # forward along the reel strip.
            nearest_index = int(
                np.argmin(forward_distances)
            )

            scatter_position = int(
                scatter_positions[nearest_index]
            )

            # Randomly choose where in the visible window the
            # scatter should appear.
            visible_offset = int(
                rng.choice(self.model.window_offsets)
            )

            # Screen construction uses:
            #
            #     reel[(stop + offset) % reel_length]
            #
            # so the required stop is scatter_position - offset.
            stops[0, reel_index] = (
                scatter_position - visible_offset
            ) % self.model.reel_length

        return stops

    def spin(
        self,
        rng: np.random.Generator,
    ) -> SpinBatch:
        """
        Generate and build one guaranteed bonus-triggering spin.

        Returning SpinBatch makes the forced spin compatible with
        the normal backend spin representation.
        """

        stops = self.sample_stops(rng)

        screens = build_screens(
            model=self.model,
            stops=stops,
        )

        trigger_mask = scatter_bonus_trigger_mask(
            screens=screens,
            min_scatter_count=self.minimum_scatter_count,
        )

        if not bool(trigger_mask[0]):
            raise RuntimeError(
                "Forced bonus generation failed to produce "
                "a valid bonus trigger."
            )

        return SpinBatch(
            stops=stops,
            screens=screens,
        )