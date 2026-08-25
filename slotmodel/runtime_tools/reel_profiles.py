from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slotmodel.paths import REELS_CANDIDATES_DIR


@dataclass(frozen=True, slots=True)
class ReelProfile:
    """One selectable reel set and its optional optimizer report."""

    name: str
    label: str
    reels_path: Path
    report_path: Path | None = None

    @property
    def has_report(self) -> bool:
        return self.report_path is not None and self.report_path.is_file()


def _profile_label(name: str) -> str:

    if name.endswith("_vol"):
        prefix = name.removesuffix("_vol").replace("_", " ").title()
        return f"{prefix} Volatility"

    return name.replace("_", " ").title()


def discover_reel_profiles(
    *,
    candidates_dir: Path = REELS_CANDIDATES_DIR,
) -> tuple[ReelProfile, ...]:
    """Discover reel sets that can be selected by the GUI.

    The normal ``reels.json`` configuration is always exposed as ``Default``
    when it exists. Optimizer outputs are discovered from
    ``config/reels/candidates``. Files ending in ``_report.json`` are metadata,
    not reel sets, and are paired with the candidate that has the same stem.
    """

    profiles: list[ReelProfile] = []

    if candidates_dir.is_dir():
        for reels_path in sorted(candidates_dir.glob("*.json")):
            if reels_path.stem.endswith("_report"):
                continue

            name = reels_path.stem
            report_path = reels_path.with_name(f"{name}_report.json")

            profiles.append(
                ReelProfile(
                    name=name,
                    label=_profile_label(name),
                    reels_path=reels_path,
                    report_path=(
                        report_path if report_path.is_file() else None
                    ),
                )
            )

    if not profiles:
        raise FileNotFoundError(
            "No reel sets were found in config/reels or "
            "config/reels/candidates."
        )

    return tuple(profiles)
