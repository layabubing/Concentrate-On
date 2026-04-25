from __future__ import annotations

try:
    from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
    from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
except ImportError:
    from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
    from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

    ALIGN_CENTER = Qt.AlignCenter


class FocusPage(QWidget):
    def __init__(self, scale) -> None:
        super().__init__()
        self._scale = scale
        self._is_focusing = False

        self._button_base_size = self._scale(200)
        self._button_pressed_size = self._scale(184)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(scale(32), scale(24), scale(32), scale(24))
        layout.setSpacing(scale(8))

        title_label = QLabel("专注", self)
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel("点击按钮开始你的专注时间", self)
        subtitle_label.setObjectName("pageSubtitle")

        holder_size = self._scale(220)
        self.button_holder = QWidget(self)
        self.button_holder.setFixedSize(holder_size, holder_size)

        self.focus_button = QPushButton("开始专注", self.button_holder)
        self.focus_button.setCheckable(True)
        self.focus_button.setFlat(True)
        self.focus_button.clicked.connect(self._toggle_focus)
        self.focus_button.pressed.connect(self._on_button_pressed)
        self.focus_button.released.connect(self._on_button_released)

        self.focus_button.setGeometry(self._button_rect(self._button_base_size))
        self.focus_button.setStyleSheet(self._button_style())

        self._press_anim = QPropertyAnimation(self.focus_button, b"geometry", self)
        self._press_anim.setDuration(120)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic if hasattr(QEasingCurve, "Type") else QEasingCurve.OutCubic)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addStretch(1)
        layout.addWidget(self.button_holder, 0, ALIGN_CENTER)
        layout.addStretch(1)

    def _button_rect(self, size: int) -> QRect:
        holder_w = self.button_holder.width()
        holder_h = self.button_holder.height()
        x = (holder_w - size) // 2
        y = (holder_h - size) // 2
        return QRect(x, y, size, size)

    def _animate_button(self, target_size: int) -> None:
        self._press_anim.stop()
        self._press_anim.setStartValue(self.focus_button.geometry())
        self._press_anim.setEndValue(self._button_rect(target_size))
        self._press_anim.start()

    def _on_button_pressed(self) -> None:
        self._animate_button(self._button_pressed_size)

    def _on_button_released(self) -> None:
        self._animate_button(self._button_base_size)

    def _toggle_focus(self) -> None:
        self._is_focusing = not self._is_focusing
        self.focus_button.setText("结束专注" if self._is_focusing else "开始专注")
        self.focus_button.setStyleSheet(self._button_style())

    def _button_style(self) -> str:
        font_size = self._scale(24)
        radius = 9999

        if self._is_focusing:
            bg_color = "#2fbf71"
            hover_color = "#25a962"
            pressed_color = "#1f914f"
        else:
            bg_color = "#3f7cf7"
            hover_color = "#3569d1"
            pressed_color = "#2e5fb8"

        return (
            "QPushButton {"
            f"background-color: {bg_color};"
            "color: white;"
            "border: none;"
            f"border-radius: {radius}px;"
            f"font-size: {font_size}px;"
            "font-weight: 600;"
            "}"
            f"QPushButton:hover {{ background-color: {hover_color}; border-radius: {radius}px; border: none; }}"
            f"QPushButton:pressed {{ background-color: {pressed_color}; border-radius: {radius}px; border: none; }}"
            f"QPushButton:checked {{ background-color: {bg_color}; border-radius: {radius}px; border: none; }}"
            f"QPushButton:checked:hover {{ background-color: {hover_color}; border-radius: {radius}px; border: none; }}"
            f"QPushButton:checked:pressed {{ background-color: {pressed_color}; border-radius: {radius}px; border: none; }}"
        )
