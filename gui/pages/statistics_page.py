from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.pages.base_page import BasePage
from slotmodel.runtime_tools import ReelProfile


class StatisticsPage(BasePage):
    """Display the saved optimizer/simulation report for the active profile."""

    def __init__(self, profile: ReelProfile) -> None:
        super().__init__(
            title="Statistics",
            description=(
                "Inspect the saved validation statistics for the reel profile "
                "currently selected in the sidebar."
            ),
            expand_body=True,
        )
        self._profile = profile

        if not profile.has_report:
            self.add_placeholder(
                title=f"{profile.label} has no saved report",
                description=(
                    "This reel set can be played, but there is no matching "
                    "optimizer report to display. Candidate reports are expected "
                    "beside the reel JSON as '<profile>_report.json'."
                ),
            )
            return

        try:
            payload = self._read_report(profile.report_path)
            evaluation = self._require_mapping(payload, "evaluation")
            report = self._require_mapping(evaluation, "report")
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            self.add_placeholder(
                title="Unable to load profile statistics",
                description=str(error),
            )
            return

        self.body_layout.addWidget(
            self._create_report_view(payload, evaluation, report),
            stretch=1,
        )

    @staticmethod
    def _read_report(path: Path | None) -> dict[str, Any]:
        if path is None:
            raise ValueError("The active profile has no report path.")

        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, dict):
            raise ValueError("The report JSON must contain an object.")

        return payload

    @staticmethod
    def _require_mapping(
        mapping: Mapping[str, Any],
        key: str,
    ) -> Mapping[str, Any]:
        value = mapping.get(key)
        if not isinstance(value, Mapping):
            raise ValueError(f"Report field {key!r} must contain an object.")
        return value

    def _create_report_view(
        self,
        payload: Mapping[str, Any],
        evaluation: Mapping[str, Any],
        report: Mapping[str, Any],
    ) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("statisticsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("statisticsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(14)

        layout.addWidget(self._create_summary_card(payload, evaluation, report))

        payout_bands = self._require_mapping(report, "payout_bands")
        bonus_bands = self._require_mapping(report, "bonus_payout_bands")
        base_tail = self._require_mapping(report, "base_tail")
        bonus_tail = self._require_mapping(report, "bonus_tail")

        layout.addWidget(
            self._create_table_card(
                "Base-game payout distribution",
                "Probability of each base-game payout band in the final validation simulation.",
                self._probability_rows(payout_bands, bonus=False),
            )
        )
        layout.addWidget(
            self._create_table_card(
                "Bonus payout distribution",
                "Probability of each full bonus-game payout band in the final validation simulation.",
                self._probability_rows(bonus_bands, bonus=True),
            )
        )

        tail_rows = [
            ("Base p95", self._format_multiplier(base_tail.get("p95"))),
            ("Base p99", self._format_multiplier(base_tail.get("p99"))),
            ("Base p99.9", self._format_multiplier(base_tail.get("p999"))),
            ("Base max observed", self._format_multiplier(base_tail.get("max_observed"))),
            ("Base max-win frequency", self._format_percent(base_tail.get("max_win_freq"))),
            ("Bonus p95", self._format_multiplier(bonus_tail.get("p95"))),
            ("Bonus p99", self._format_multiplier(bonus_tail.get("p99"))),
            ("Bonus p99.9", self._format_multiplier(bonus_tail.get("p999"))),
            ("Bonus max observed", self._format_multiplier(bonus_tail.get("max_observed"))),
            ("Bonus max-win frequency", self._format_percent(bonus_tail.get("max_win_freq"))),
            ("Base std. dev.", self._format_multiplier(report.get("std_base"))),
            ("Bonus std. dev.", self._format_multiplier(report.get("std_bonus"))),
            ("Total std. dev.", self._format_multiplier(report.get("std_total"))),
        ]
        layout.addWidget(
            self._create_table_card(
                "Volatility and tails",
                "Observed payout dispersion and upper-tail statistics.",
                tail_rows,
            )
        )

        precision_rows = [
            ("Bonus frequency SE", self._format_number(report.get("bonus_freq_se"), 6)),
            ("Mean bonus payout SE", self._format_number(report.get("mean_bonus_payout_se"), 6)),
            ("Base RTP SE", self._format_number(report.get("rtp_base_se"), 6)),
            ("Bonus RTP SE", self._format_number(report.get("rtp_bonus_se"), 6)),
            ("Total RTP SE", self._format_number(report.get("rtp_total_se"), 6)),
            ("Base spins", self._format_integer(report.get("total_base_spins"))),
            ("Bonus entries", self._format_integer(report.get("bonus_entries"))),
            ("Bonus games simulated", self._format_integer(report.get("total_bonus_games"))),
        ]
        layout.addWidget(
            self._create_table_card(
                "Precision and sample counts",
                "Monte Carlo standard errors and final validation sample sizes.",
                precision_rows,
            )
        )

        target_rows = self._target_rows(evaluation)
        if target_rows:
            layout.addWidget(
                self._create_table_card(
                    "Optimization target fit",
                    "Final validation value compared with the configured target and tolerance.",
                    target_rows,
                    headers=(
                        "Metric",
                        "Observed",
                        "Target",
                        "Tolerance",
                        "Weight",
                        "Z-error",
                    ),
                )
            )

        simulation = payload.get("simulation")
        if isinstance(simulation, Mapping):
            layout.addWidget(
                self._create_table_card(
                    "Simulation settings",
                    "Simulation configuration stored with this candidate report.",
                    self._mapping_rows(simulation),
                )
            )

        optimizer = payload.get("optimizer")
        if isinstance(optimizer, Mapping):
            layout.addWidget(
                self._create_table_card(
                    "Optimizer settings",
                    "Genetic-algorithm settings used to produce this reel set.",
                    self._mapping_rows(optimizer),
                )
            )

        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _create_summary_card(
        self,
        payload: Mapping[str, Any],
        evaluation: Mapping[str, Any],
        report: Mapping[str, Any],
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("contentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel(f"{self._profile.label} · final validation")
        title.setObjectName("cardTitle")
        description = QLabel(
            "These values come from the saved candidate report; changing the "
            "active reel profile changes both the game reels and this report."
        )
        description.setObjectName("cardDescription")
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(12)
        metrics.setVerticalSpacing(12)

        rtp_base = self._as_float(report.get("rtp_base"))
        rtp_bonus = self._as_float(report.get("rtp_bonus"))
        rtp_total = (
            None if rtp_base is None or rtp_bonus is None else rtp_base + rtp_bonus
        )

        payout_bands = report.get("payout_bands")
        base_win_prob = (
            payout_bands.get("p_win")
            if isinstance(payout_bands, Mapping)
            else None
        )

        values = (
            ("Total RTP", self._format_percent(rtp_total)),
            ("Base RTP", self._format_percent(rtp_base)),
            ("Bonus RTP", self._format_percent(rtp_bonus)),
            ("Base win probability", self._format_percent(base_win_prob)),
            ("Bonus frequency", self._format_frequency(report.get("bonus_freq"))),
            ("Mean bonus payout", self._format_multiplier(report.get("mean_bonus_payout"))),
            ("Mean free spins", self._format_number(report.get("mean_free_spins"), 2)),
            ("Fitness score", self._format_number(evaluation.get("score"), 3)),
        )

        for index, (label, value) in enumerate(values):
            metrics.addWidget(
                self._create_metric_card(label, value),
                index // 4,
                index % 4,
            )

        layout.addLayout(metrics)

        paytable_name = payload.get(
            "paytable",
            report.get("paytable_name"),
        )
        metadata = QLabel(
            "Paytable: "
            f"{self._format_scalar(paytable_name)}  ·  "
            "Best generation: "
            f"{self._format_scalar(payload.get('best_generation'))}  ·  "
            "Validation seed: "
            f"{self._format_scalar(report.get('seed'))}  ·  "
            "Base spins: "
            f"{self._format_integer(report.get('total_base_spins'))}  ·  "
            "Bonus games: "
            f"{self._format_integer(report.get('total_bonus_games'))}"
        )
        metadata.setObjectName("cardDescription")
        metadata.setWordWrap(True)
        layout.addWidget(metadata)

        return card

    @staticmethod
    def _create_metric_card(label: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("metricCard")
        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        label_widget = QLabel(label)
        label_widget.setObjectName("metricLabel")
        label_widget.setWordWrap(True)

        layout.addWidget(value_label)
        layout.addWidget(label_widget)
        return frame

    def _create_table_card(
        self,
        title_text: str,
        description_text: str,
        rows: Sequence[Sequence[str]],
        *,
        headers: Sequence[str] = ("Statistic", "Value"),
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("contentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("cardTitle")
        description = QLabel(description_text)
        description.setObjectName("cardDescription")
        description.setWordWrap(True)

        table = QTableWidget(len(rows), len(headers))
        table.setObjectName("statisticsTable")
        table.setHorizontalHeaderLabels(tuple(headers))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(34)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        table.setMinimumHeight(min(430, 44 + max(1, len(rows)) * 34))

        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                if column_index > 0:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                table.setItem(row_index, column_index, item)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(table)
        return card

    def _probability_rows(
        self,
        bands: Mapping[str, Any],
        *,
        bonus: bool,
    ) -> list[tuple[str, str]]:
        if bonus:
            labels = (
                ("p_0", "No payout"),
                ("p_win", "Any payout"),
                ("p_0_to_10", "0x to <10x"),
                ("p_10_to_25", "10x to <25x"),
                ("p_25_to_50", "25x to <50x"),
                ("p_50_to_100", "50x to <100x"),
                ("p_100_to_250", "100x to <250x"),
                ("p_250_to_500", "250x to <500x"),
                ("p_500_to_1000", "500x to <1000x"),
                ("p_over_1000", "1000x or more"),
            )
        else:
            labels = (
                ("p_0", "No payout"),
                ("p_win", "Any payout"),
                ("p_0_to_1", "0x to <1x"),
                ("p_1_to_2", "1x to <2x"),
                ("p_2_to_5", "2x to <5x"),
                ("p_5_to_10", "5x to <10x"),
                ("p_10_to_20", "10x to <20x"),
                ("p_20_to_30", "20x to <30x"),
                ("p_30_to_50", "30x to <50x"),
                ("p_over_50", "50x or more"),
            )

        return [
            (label, self._format_percent(bands.get(key)))
            for key, label in labels
            if key in bands
        ]

    def _target_rows(
        self,
        evaluation: Mapping[str, Any],
    ) -> list[tuple[str, str, str, str, str, str]]:
        metrics = evaluation.get("metrics")
        targets = evaluation.get("targets")
        errors = evaluation.get("normalized_errors")
        if (
            not isinstance(metrics, Mapping)
            or not isinstance(targets, Mapping)
            or not isinstance(errors, Mapping)
        ):
            return []

        rows: list[tuple[str, str, str, str, str, str]] = []
        for name, target_config in targets.items():
            if not isinstance(target_config, Mapping) or name not in metrics:
                continue
            rows.append(
                (
                    self._pretty_name(str(name)),
                    self._format_metric(str(name), metrics.get(name)),
                    self._format_metric(str(name), target_config.get("value")),
                    self._format_metric(str(name), target_config.get("tolerance")),
                    self._format_number(target_config.get("weight"), 2),
                    self._format_number(errors.get(name), 3),
                )
            )
        return rows

    def _mapping_rows(
        self,
        mapping: Mapping[str, Any],
    ) -> list[tuple[str, str]]:
        return [
            (self._pretty_name(str(key)), self._format_scalar(value))
            for key, value in mapping.items()
        ]

    def _format_metric(self, name: str, value: Any) -> str:
        if name.startswith("rtp_") or name.endswith("_prob") or name == "bonus_freq":
            return self._format_percent(value)
        if "payout" in name:
            return self._format_multiplier(value)
        return self._format_number(value, 4)

    @staticmethod
    def _pretty_name(name: str) -> str:
        replacements = {"rtp": "RTP", "se": "SE"}
        words = name.split("_")
        return " ".join(replacements.get(word, word.title()) for word in words)

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return None

    @classmethod
    def _format_percent(cls, value: Any) -> str:
        number = cls._as_float(value)
        return "—" if number is None else f"{number * 100:.3f}%"

    @classmethod
    def _format_frequency(cls, value: Any) -> str:
        number = cls._as_float(value)
        if number is None:
            return "—"
        if number <= 0:
            return f"{number * 100:.3f}%"
        return f"{number * 100:.3f}% ~ 1 in {round(1.0 / number):.1f}"

    @classmethod
    def _format_multiplier(cls, value: Any) -> str:
        number = cls._as_float(value)
        return "—" if number is None else f"{number:,.3f}x"

    @classmethod
    def _format_number(cls, value: Any, decimals: int) -> str:
        number = cls._as_float(value)
        return "—" if number is None else f"{number:,.{decimals}f}"

    @staticmethod
    def _format_integer(value: Any) -> str:
        if isinstance(value, int) and not isinstance(value, bool):
            return f"{value:,}"
        return "—"

    @staticmethod
    def _format_scalar(value: Any) -> str:
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, int):
            return f"{value:,}"
        if isinstance(value, float):
            return f"{value:,.6g}"
        if value is None:
            return "—"
        return str(value)