from __future__ import annotations

try:
    from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
except ImportError:
    from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget


class StatPage(QWidget):
    def __init__(self, scale) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(scale(32), scale(24), scale(32), scale(24))
        layout.setSpacing(scale(8))

        title_label = QLabel("统计", self)
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel("这里是统计页面", self)
        subtitle_label.setObjectName("pageSubtitle")

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addStretch(1)
