# main.py
import sys

# =========================================================================
# [CRITICAL FOR PYINSTALLER]
# Force PyInstaller's static analyzer to collect standard libraries
# that are dynamically imported inside our sub-modules in the runtime.
# =========================================================================
import json
import math
import hashlib
import random
import datetime

from PyQt6.QtWidgets import QApplication
from ui.login import LoginDialog
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # 调起高阶登录认证窗口
    login = LoginDialog()
    if login.exec():
        # 认证通过，实例化平台主视窗
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    else:
        # 用户取消或关闭，安全关闭进程
        sys.exit(0)


if __name__ == "__main__":
    main()