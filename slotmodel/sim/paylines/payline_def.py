from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias
import numpy as np
from numpy.typing import NDArray


Payline: TypeAlias = tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PaylineSet:
    reel_count: int
    row_count: int
    lines: tuple[Payline, ...]

    def __post_init__(self) -> None:
        if self.reel_count <= 0:
            raise ValueError("reel_count must be positive")

        if self.row_count <= 0:
            raise ValueError("row_count must be positive")

        if not self.lines:
            raise ValueError("At least one payline is required")

        seen: set[Payline] = set()

        for line_index, line in enumerate(self.lines):
            if len(line) != self.reel_count:
                raise ValueError(
                    f"Payline {line_index} has {len(line)} positions; "
                    f"expected {self.reel_count}"
                )

            for reel_index, row in enumerate(line):
                if not 0 <= row < self.row_count:
                    raise ValueError(
                        f"Payline {line_index}, reel {reel_index}: "
                        f"row {row} is outside [0, {self.row_count})"
                    )

            if line in seen:
                raise ValueError(f"Duplicate payline at index {line_index}")

            seen.add(line)

def compile_paylines(
    paylines: PaylineSet,
)-> NDArray[np.int8]:
    return np.asarray(paylines.lines, dtype = np.int8)