from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from slotmodel.paths import REELS_CONFIG_PATH
from slotmodel.sim.reels.reel_def import Reel, ReelSet
from slotmodel.sim.reels.symbols import Symbol


def read_reels(
    path: str | Path = REELS_CONFIG_PATH,
) -> ReelSet:
    """Read and validate a reel set from a JSON configuration file."""

    input_path = Path(path)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Reel file does not exist: {input_path}"
        )

    try:
        with input_path.open("r", encoding="utf-8") as file:
            data: Any = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in reel file {input_path}: {error}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError(
            "The reel configuration must contain a JSON object."
        )

    if data.get("format_version") != 1:
        raise ValueError(
            "Unsupported or missing reel format version."
        )

    stored_reel_count = data.get("number_of_reels")
    stored_reel_length = data.get("reel_length")
    stored_reels = data.get("reels")

    if (
        not isinstance(stored_reel_count, int)
        or isinstance(stored_reel_count, bool)
        or stored_reel_count <= 0
    ):
        raise ValueError(
            "'number_of_reels' must be a positive integer."
        )

    if (
        not isinstance(stored_reel_length, int)
        or isinstance(stored_reel_length, bool)
        or stored_reel_length <= 0
    ):
        raise ValueError(
            "'reel_length' must be a positive integer."
        )

    if not isinstance(stored_reels, list) or not stored_reels:
        raise ValueError(
            "The JSON file must contain a non-empty 'reels' list."
        )

    if len(stored_reels) != stored_reel_count:
        raise ValueError(
            f"The file declares {stored_reel_count} reels, "
            f"but contains {len(stored_reels)}."
        )

    reels: list[Reel] = []

    for reel_index, stored_reel in enumerate(stored_reels):
        if not isinstance(stored_reel, list) or not stored_reel:
            raise ValueError(
                f"Reel {reel_index} must be a non-empty list."
            )

        if len(stored_reel) != stored_reel_length:
            raise ValueError(
                f"Reel {reel_index} has length "
                f"{len(stored_reel)}, but expected "
                f"{stored_reel_length}."
            )

        symbol_ids: list[int] = []

        for stop_index, symbol_name in enumerate(stored_reel):
            if not isinstance(symbol_name, str):
                raise ValueError(
                    f"Symbol at reel {reel_index}, "
                    f"stop {stop_index} must be a string."
                )

            try:
                symbol = Symbol[symbol_name]
            except KeyError as error:
                raise ValueError(
                    f"Unknown symbol {symbol_name!r} at "
                    f"reel {reel_index}, stop {stop_index}."
                ) from error

            symbol_ids.append(int(symbol))

        reel = np.asarray(symbol_ids, dtype=np.int16)

        # Prevent callers from accidentally modifying the loaded
        # configuration in place.
        reel.flags.writeable = False

        reels.append(reel)

    return tuple(reels)


def main() -> None:
    reels = read_reels()

    print(
        f"Loaded {len(reels)} reels from "
        f"{REELS_CONFIG_PATH}"
    )

    for reel_index, reel in enumerate(reels, start=1):
        print(
            f"Reel {reel_index}: "
            f"shape={reel.shape}, dtype={reel.dtype}"
        )
        print(reel)


if __name__ == "__main__":
    main()