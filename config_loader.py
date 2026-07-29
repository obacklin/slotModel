from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from game_config import GameConfig, Payline


class ConfigError(ValueError):
    """Raised when a game configuration cannot be loaded."""


@dataclass(frozen=True, slots=True)
class PaylineStyle:
    color: str = "#FF0000"
    width: float = 4.0


@dataclass(frozen=True, slots=True)
class UiConfig:
    payline_styles: dict[str, PaylineStyle]


@dataclass(frozen=True, slots=True)
class LoadedGame:
    game: GameConfig
    ui: UiConfig


def _read_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(
            f"Could not read configuration file: {path}"
        ) from error

    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"Invalid JSON in {path} at "
            f"line {error.lineno}, column {error.colno}: "
            f"{error.msg}"
        ) from error

    if not isinstance(value, dict):
        raise ConfigError(
            "The top-level JSON value must be an object."
        )

    return value


def _format_validation_error(error: ValidationError) -> str:
    location = ".".join(
        str(part)
        for part in error.absolute_path
    )

    if not location:
        location = "<root>"

    return f"{location}: {error.message}"


def _validate_schema(
    document: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        messages = "\n".join(
            f"- {_format_validation_error(error)}"
            for error in errors
        )

        raise ConfigError(
            f"Configuration schema validation failed:\n{messages}"
        )


def _validate_semantics(document: dict[str, Any]) -> None:
    game_data = document["game"]

    reel_count = game_data["reel_count"]
    rows = game_data["rows"]
    offsets = game_data["window_offsets"]

    if len(offsets) != rows:
        raise ConfigError(
            "game.window_offsets must contain exactly "
            f"{rows} entries."
        )

    reel_data = document["reels"]
    active_set_id = reel_data["active_set"]
    reel_sets = reel_data["sets"]

    if active_set_id not in reel_sets:
        raise ConfigError(
            f"Active reel set {active_set_id!r} does not exist."
        )

    active_set = reel_sets[active_set_id]
    strips = active_set["strips"]

    if len(strips) != reel_count:
        raise ConfigError(
            f"Active reel set contains {len(strips)} reels; "
            f"expected {reel_count}."
        )

    symbol_ids = {
        symbol["id"]
        for symbol in document["symbols"]
    }

    for reel_index, strip in enumerate(strips):
        for position, symbol_id in enumerate(strip):
            if symbol_id not in symbol_ids:
                raise ConfigError(
                    f"Unknown symbol {symbol_id!r} at "
                    f"reel {reel_index + 1}, "
                    f"position {position}."
                )

    payline_ids: set[str] = set()

    for payline in document["paylines"]:
        payline_id = payline["id"]

        if payline_id in payline_ids:
            raise ConfigError(
                f"Duplicate payline ID: {payline_id!r}."
            )

        payline_ids.add(payline_id)

        payline_rows = payline["rows"]

        if len(payline_rows) != reel_count:
            raise ConfigError(
                f"Payline {payline_id!r} contains "
                f"{len(payline_rows)} rows; "
                f"expected {reel_count}."
            )

        for row in payline_rows:
            if not 0 <= row < rows:
                raise ConfigError(
                    f"Payline {payline_id!r} contains "
                    f"invalid row {row}."
                )

    styles = document.get("ui", {}).get("paylines", {})

    unknown_style_ids = set(styles) - payline_ids

    if unknown_style_ids:
        unknown = ", ".join(sorted(unknown_style_ids))
        raise ConfigError(
            "UI styles reference unknown paylines: "
            f"{unknown}."
        )


def load_game(
    config_path: str | Path,
    *,
    schema_path: str | Path | None = None,
) -> LoadedGame:
    config_path = Path(config_path)

    if schema_path is None:
        schema_path = (
            Path(__file__).parent
            / "schemas"
            / "game-config.schema.json"
        )

    schema_path = Path(schema_path)

    document = _read_json(config_path)
    schema = _read_json(schema_path)

    _validate_schema(document, schema)
    _validate_semantics(document)

    game_data = document["game"]
    reel_data = document["reels"]

    active_set_id = reel_data["active_set"]
    strips = reel_data["sets"][active_set_id]["strips"]

    paylines = tuple(
        Payline(
            id=item["id"],
            name=item["name"],
            rows=tuple(item["rows"]),
        )
        for item in document["paylines"]
    )

    game = GameConfig(
        name=game_data["name"],
        reels=tuple(
            tuple(strip)
            for strip in strips
        ),
        paylines=paylines,
        visible_rows=game_data["rows"],
        window_offsets=tuple(
            game_data["window_offsets"]
        ),
    )

    raw_styles = (
        document
        .get("ui", {})
        .get("paylines", {})
    )

    styles = {
        payline_id: PaylineStyle(
            color=style.get("color", "#FF0000"),
            width=float(style.get("width", 4.0)),
        )
        for payline_id, style in raw_styles.items()
    }

    return LoadedGame(
        game=game,
        ui=UiConfig(payline_styles=styles),
    )