from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


Symbol: TypeAlias = str
ReelStrip: TypeAlias = tuple[Symbol, ...]

@dataclass(frozen=True, slots=True)
class Payline:
    name: str
    rows: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Payline name can not be empty.")

        if not self.rows:
            raise ValueError("Payline must contain row(s).")

@dataclass(frozen=True, slots=True)
class GameConfig:
    """Immutable structural configuration for a slot game.

    For this first version, the configuration contains only the information
    required to construct a visible reel window.
    """

    reels: tuple[ReelStrip, ...]
    paylines: tuple[Payline, ...]
    visible_rows: int = 3
    name: str = "Example Slot"

    def __post_init__(self) -> None:
        if not isinstance(self.visible_rows, int):
            raise TypeError("visible_rows must be an integer")

        if self.visible_rows < 1:
            raise ValueError("visible_rows must be at least 1")

        if not self.reels:
            raise ValueError("The game must contain at least one reel")

        for reel_index, reel in enumerate(self.reels):
            if not reel:
                raise ValueError(f"Reel {reel_index} cannot be empty")

            if len(reel) < self.visible_rows:
                raise ValueError(
                    f"Reel {reel_index} has length {len(reel)}, but "
                    f"visible_rows is {self.visible_rows}"
                )

            for position, symbol in enumerate(reel):
                if not isinstance(symbol, str):
                    raise TypeError(
                        f"Symbol at reel {reel_index}, position {position} "
                        "must be a string"
                    )

                if not symbol.strip():
                    raise ValueError(
                        f"Symbol at reel {reel_index}, position {position} "
                        "cannot be empty"
                    )

        for payline_index, payline in enumerate(self.paylines):
            if len(payline.rows) != self.n_reels:
                raise ValueError(
                    f"Payline {payline_index + 1} contains "
                    f"{len(payline.rows)} rows; expected {self.n_reels}"
                )
            for reel_index, row in enumerate(payline.rows):
                if isinstance(row, bool) or not isinstance(row, int):
                    raise TypeError(
                        f"Row for reel {reel_index + 1} in "
                        f"payline {payline_index + 1} must be an integer"
                    )

                if not 0 <= row < self.visible_rows:
                    raise ValueError(
                        f"Row {row} in payline {payline_index + 1} "
                        f"is invalid; expected 0 to "
                        f"{self.visible_rows - 1}"
                    )

    @property
    def n_reels(self) -> int:
        return len(self.reels)

    @property
    def reel_lengths(self) -> tuple[int, ...]:
        return tuple(len(reel) for reel in self.reels)
