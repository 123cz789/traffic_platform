# core/base_module.py
from PyQt6.QtWidgets import QWidget


class BaseModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def refresh_data(self):
        """数据刷新接口存根"""
        pass

    def save_changes(self):
        """数据保存接口存根"""
        pass