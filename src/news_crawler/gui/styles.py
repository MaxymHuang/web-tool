"""Shared Qt styles for visual hierarchy and readability."""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

# Palette
TEXT_PRIMARY = "#1a1a1a"
TEXT_SECONDARY = "#5a5a5a"
TEXT_MUTED = "#757575"
BORDER = "#e0e0e0"
SURFACE = "#fafafa"
SURFACE_ALT = "#f0f0f0"
ACCENT = "#1565c0"
ACCENT_HOVER = "#0d47a1"
QUEUED_BG = "#e8f5e9"
QUEUED_BORDER = "#43a047"
SELECTED_BG = "#e3f2fd"

APP_STYLESHEET = f"""
QMainWindow, QWidget {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QGroupBox {{
    font-weight: 600;
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 10px;
    padding: 12px 10px 10px 10px;
    background: {SURFACE};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}}
QPlainTextEdit, QLineEdit, QComboBox, QSpinBox {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    background: white;
}}
QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {ACCENT};
}}
QPushButton {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 14px;
    background: white;
}}
QPushButton:hover {{
    background: {SURFACE_ALT};
}}
QPushButton:default {{
    background: {ACCENT};
    color: white;
    border-color: {ACCENT};
    font-weight: 600;
}}
QPushButton:default:hover {{
    background: {ACCENT_HOVER};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    background: {SURFACE_ALT};
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    top: -1px;
    background: white;
}}
QTabBar::tab {{
    padding: 8px 16px;
    margin-right: 2px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background: {SURFACE_ALT};
}}
QTabBar::tab:selected {{
    background: white;
    font-weight: 600;
    border-bottom: 2px solid {ACCENT};
}}
QListWidget {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: white;
    outline: none;
}}
QListWidget::item {{
    border-bottom: 1px solid {BORDER};
    padding: 0px;
}}
QListWidget::item:selected {{
    background: {SELECTED_BG};
}}
QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    height: 18px;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 3px;
}}
"""


def apply_app_style(app: QApplication) -> None:
    app.setStyleSheet(APP_STYLESHEET)


def title_font() -> QFont:
    font = QFont()
    font.setPointSize(11)
    font.setWeight(QFont.Weight.DemiBold)
    return font


def meta_font() -> QFont:
    font = QFont()
    font.setPointSize(9)
    return font


def snippet_font() -> QFont:
    font = QFont()
    font.setPointSize(9)
    return font
