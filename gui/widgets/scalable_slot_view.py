from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QSizePolicy,
    QWidget,
)


class ScalableSlotView(QGraphicsView):
    """
    Display a fixed-size slot widget at a uniform responsive scale.

    The embedded widget keeps its native coordinate system. Only the graphics
    view transform changes, so reel animation geometry, sticky overlays and
    payline coordinates do not need to become responsive themselves.

    The view never scales the slot above its native size. When less space is
    available, the same scale factor is applied horizontally and vertically so
    the slot cannot be stretched or clipped.
    """

    def __init__(
        self,
        slot_widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        native_size = slot_widget.size()
        if native_size.width() <= 0 or native_size.height() <= 0:
            native_size = slot_widget.sizeHint()

        if native_size.width() <= 0 or native_size.height() <= 0:
            raise ValueError(
                "slot_widget must have a positive native size."
            )

        self._native_size = QSize(native_size)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._proxy = self._scene.addWidget(slot_widget)
        self._proxy.setPos(0.0, 0.0)
        self._scene.setSceneRect(
            0.0,
            0.0,
            float(self._native_size.width()),
            float(self._native_size.height()),
        )

        self.setObjectName("scalableSlotView")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
        )
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setMinimumSize(1, 1)
        self.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform,
            True,
        )
        self.setInteractive(False)

        # Avoid the QGraphicsView viewport painting its own opaque panel behind
        # the slot when the transformed slot is smaller than the available area.
        self.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)
        self.viewport().setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        self._update_scale()

    @property
    def slot_widget(self) -> QWidget:
        return self._proxy.widget()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(self._native_size)

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(1, 1)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_scale()

    def _update_scale(self) -> None:
        viewport_size = self.viewport().size()
        available_width = max(1, viewport_size.width())
        available_height = max(1, viewport_size.height())

        scale = min(
            available_width / self._native_size.width(),
            available_height / self._native_size.height(),
            1.0,
        )

        transform = QTransform()
        transform.scale(scale, scale)
        self.setTransform(transform)
