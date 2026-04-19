from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

try:
    from PyQt6.QtCore import Qt, QSize
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QFrame,
        QHBoxLayout,
        QMainWindow,
        QSizePolicy,
        QStackedWidget,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    IS_QT6 = True
except ImportError:
    from PyQt5.QtCore import Qt, QSize
    from PyQt5.QtGui import QIcon
    from PyQt5.QtWidgets import (
        QApplication,
        QButtonGroup,
        QFrame,
        QHBoxLayout,
        QMainWindow,
        QSizePolicy,
        QStackedWidget,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    IS_QT6 = False

if IS_QT6:
    CURSOR_POINTING = Qt.CursorShape.PointingHandCursor
    TB_TEXT_BESIDE = Qt.ToolButtonStyle.ToolButtonTextBesideIcon
    TB_TEXT_UNDER = Qt.ToolButtonStyle.ToolButtonTextUnderIcon
    POLICY_EXPANDING = QSizePolicy.Policy.Expanding
    POLICY_FIXED = QSizePolicy.Policy.Fixed
else:
    CURSOR_POINTING = Qt.PointingHandCursor
    TB_TEXT_BESIDE = Qt.ToolButtonTextBesideIcon
    TB_TEXT_UNDER = Qt.ToolButtonTextUnderIcon
    POLICY_EXPANDING = QSizePolicy.Expanding
    POLICY_FIXED = QSizePolicy.Fixed


def _load_page_class(filename: str, class_name: str):
    module_path = Path(__file__).resolve().parent / "ui" / filename
    spec = importlib.util.spec_from_file_location(f"concentrateon_{class_name.lower()}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    page_class = getattr(module, class_name, None)
    if page_class is None:
        raise ImportError(f"{class_name} not found in {module_path}")
    return page_class


FocusPage = _load_page_class("focus.py", "FocusPage")
StatPage = _load_page_class("stat.py", "StatPage")
SettingPage = _load_page_class("setting.py", "SettingPage")


def _enable_high_dpi() -> None:
    if not IS_QT6:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class MainScreen(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ConcentrateOn")

        self.project_root = Path(__file__).resolve().parent
        self.current_key = "focus"
        self.ui_scale = self._detect_ui_scale()

        self._left_buttons: dict[str, QToolButton] = {}
        self._bottom_buttons: dict[str, QToolButton] = {}

        self._apply_window_size()
        self._setup_ui()
        self._apply_styles()
        self._sync_nav_selection("focus")
        self._adapt_navigation_mode()

    def _detect_ui_scale(self) -> float:
        app = QApplication.instance()
        if app is None:
            return 1.0

        screen = app.primaryScreen()
        if screen is None:
            return 1.0

        size = screen.availableGeometry().size()
        long_edge = max(size.width(), size.height())
        logical_dpi = screen.logicalDotsPerInch()

        scale_from_resolution = long_edge / 1920.0
        scale_from_dpi = logical_dpi / 96.0
        return min(max(scale_from_resolution, scale_from_dpi, 1.0), 1.5)

    def _scale(self, value: int) -> int:
        return max(1, int(round(value * self.ui_scale)))

    def _apply_window_size(self) -> None:
        app = QApplication.instance()
        if app is None or app.primaryScreen() is None:
            self.resize(1200, 780)
            return

        available = app.primaryScreen().availableGeometry()
        width = min(int(available.width() * 0.72), self._scale(1600))
        height = min(int(available.height() * 0.78), self._scale(980))
        self.resize(max(width, self._scale(1000)), max(height, self._scale(700)))

    def _setup_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        body = QWidget(root)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.left_nav = self._build_nav_container(vertical=True)
        body_layout.addWidget(self.left_nav)

        self.pages = QStackedWidget(body)
        self.pages.addWidget(FocusPage(self._scale))
        self.pages.addWidget(StatPage(self._scale))
        self.pages.addWidget(SettingPage(self._scale))
        body_layout.addWidget(self.pages, 1)

        root_layout.addWidget(body, 1)

        self.bottom_nav = self._build_nav_container(vertical=False)
        root_layout.addWidget(self.bottom_nav)

    def _build_nav_container(self, vertical: bool) -> QFrame:
        nav = QFrame(self)
        nav.setObjectName("navContainer")

        layout = QVBoxLayout(nav) if vertical else QHBoxLayout(nav)
        pad = self._scale(10)
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(self._scale(8))

        button_group = QButtonGroup(nav)
        button_group.setExclusive(True)

        items = [
            ("focus", "专注", "assets/icons/focus.png", 0),
            ("stat", "统计", "assets/icons/stat.png", 1),
            ("setting", "设置", "assets/icons/setting.png", 2),
        ]

        button_store = self._left_buttons if vertical else self._bottom_buttons

        if vertical:
            nav.setFixedWidth(self._scale(132))
        else:
            nav.setFixedHeight(self._scale(88))

        for key, text, icon_rel, index in items:
            btn = QToolButton(nav)
            btn.setCheckable(True)
            btn.setAutoExclusive(False)
            btn.setCursor(CURSOR_POINTING)
            btn.setProperty("selected", False)
            btn.setText(text)
            btn.setIcon(QIcon(str(self.project_root / icon_rel)))
            icon = self._scale(24)
            btn.setIconSize(QSize(icon, icon))
            btn.clicked.connect(lambda _checked, k=key: self.set_current_page(k))

            if vertical:
                btn.setToolButtonStyle(TB_TEXT_BESIDE)
                btn.setMinimumHeight(self._scale(46))
                btn.setSizePolicy(POLICY_EXPANDING, POLICY_FIXED)
            else:
                btn.setToolButtonStyle(TB_TEXT_UNDER)
                btn.setSizePolicy(POLICY_EXPANDING, POLICY_EXPANDING)

            button_group.addButton(btn, index)
            layout.addWidget(btn)
            button_store[key] = btn

        if vertical:
            layout.addStretch(1)

        return nav

    def _apply_styles(self) -> None:
        button_radius = self._scale(10)
        button_py = self._scale(6)
        button_px = self._scale(10)
        button_font = self._scale(14)
        title_font = self._scale(28)
        subtitle_font = self._scale(15)

        self.setStyleSheet(
            f"""
            QMainWindow {{
                background: #f5f7fb;
            }}
            #navContainer {{
                background: #ffffff;
                border: 1px solid #dbe3f0;
            }}
            QToolButton {{
                color: #2f3b52;
                border: 0;
                border-radius: {button_radius}px;
                padding: {button_py}px {button_px}px;
                text-align: left;
                font-size: {button_font}px;
            }}
            QToolButton[selected="true"] {{
                background: #dce9ff;
                color: #17376e;
                font-weight: 600;
            }}
            QToolButton:hover {{
                background: #eef3fb;
            }}
            QLabel#pageTitle {{
                color: #1c2740;
                font-size: {title_font}px;
                font-weight: 600;
            }}
            QLabel#pageSubtitle {{
                color: #4b5877;
                font-size: {subtitle_font}px;
            }}
            """
        )

    def _sync_nav_selection(self, key: str) -> None:
        for btn in list(self._left_buttons.values()) + list(self._bottom_buttons.values()):
            btn.setProperty("selected", False)
            btn.setChecked(False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if key in self._left_buttons:
            self._left_buttons[key].setChecked(True)
            self._left_buttons[key].setProperty("selected", True)
            self._left_buttons[key].style().unpolish(self._left_buttons[key])
            self._left_buttons[key].style().polish(self._left_buttons[key])

        if key in self._bottom_buttons:
            self._bottom_buttons[key].setChecked(True)
            self._bottom_buttons[key].setProperty("selected", True)
            self._bottom_buttons[key].style().unpolish(self._bottom_buttons[key])
            self._bottom_buttons[key].style().polish(self._bottom_buttons[key])

    def _adapt_navigation_mode(self) -> None:
        is_landscape = self.width() > self.height()
        self.left_nav.setVisible(is_landscape)
        self.bottom_nav.setVisible(not is_landscape)

    def set_current_page(self, key: str) -> None:
        page_indices = {"focus": 0, "stat": 1, "setting": 2}
        self.pages.setCurrentIndex(page_indices.get(key, 0))
        self.current_key = key
        self._sync_nav_selection(key)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._adapt_navigation_mode()


def main() -> None:
    _enable_high_dpi()
    app = QApplication(sys.argv)
    window = MainScreen()
    window.show()
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
