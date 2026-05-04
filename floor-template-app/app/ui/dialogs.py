from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QInputDialog, QWidget


def show_error(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)


def show_warning(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.warning(parent, title, message)


def show_info(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


def ask_distance_mm(parent: QWidget, title: str, label: str) -> float | None:
    value, ok = QInputDialog.getDouble(parent, title, label, 100.0, 1.0, 100000.0, 2)
    if not ok:
        return None
    return float(value)
