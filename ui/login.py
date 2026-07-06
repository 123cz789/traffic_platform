# ui/login.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QPushButton,
                             QLabel, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve
from core.auth_service import AuthService


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.auth_service = AuthService()

        # Configure window flags for frameless window integration
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(850, 520)

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("container")
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        # Left Panel - Status & Branding
        self.left_panel = QFrame()
        self.left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(50, 50, 50, 50)

        header = QLabel("     交通工程设施\n全生命周期运维平台")
        header.setObjectName("brandHeader")

        # Telemetry logs mockup
        data_block = QLabel(
            "网络节点: 正常激活\n"
            "物理延迟: 12ms\n"
            "系统运行时长: 1420h\n"
            "安全加密: AES-256 位\n\n"
            "--------------------------\n"
            "决策算法引擎: 正常启动"
        )
        data_block.setObjectName("dataBlock")

        left_layout.addStretch()
        left_layout.addWidget(header)
        left_layout.addSpacing(30)
        left_layout.addWidget(data_block)
        left_layout.addStretch()

        # Right Panel - Interaction form
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(60, 40, 60, 40)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.close)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        top_bar.addWidget(close_btn)

        title = QLabel("安全认证控制台")
        title.setObjectName("rightTitle")

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("系统账号 (ID)")
        self.user_input.setText("admin")

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("安全密钥 (PASSWORD)")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setText("123456")

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")

        self.login_btn = QPushButton("验证并建立安全连接")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.clicked.connect(self.handle_login)

        # Quick Bypass Button for easy testing
        self.bypass_btn = QPushButton("开发者极速登录")
        self.bypass_btn.setObjectName("bypassBtn")
        self.bypass_btn.clicked.connect(self.bypass_login)

        right_layout.addLayout(top_bar)
        right_layout.addStretch()
        right_layout.addWidget(title)
        right_layout.addSpacing(25)
        right_layout.addWidget(self.user_input)
        right_layout.addWidget(self.pass_input)
        right_layout.addWidget(self.status_label)
        right_layout.addSpacing(15)
        right_layout.addWidget(self.login_btn)
        right_layout.addWidget(self.bypass_btn)
        right_layout.addStretch()

        self.container_layout.addWidget(self.left_panel)
        self.container_layout.addWidget(self.right_panel)
        self.main_layout.addWidget(self.container)

    def apply_styles(self):
        self.setStyleSheet("""
            QFrame#container { background: #090b10; border-radius: 12px; border: 1px solid #1f2937; }
            QFrame#leftPanel { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111827, stop:1 #0f1219);
                border-top-left-radius: 12px; border-bottom-left-radius: 12px;
                border-right: 1px solid #1f2937;
            }
            QFrame#rightPanel { background: #090b10; }
            QLabel#brandHeader { color: #00d2ff; font-size: 26px; font-weight: 800; }
            QLabel#dataBlock { color: #60a5fa; font-family: 'Microsoft YaHei'; font-size: 13px; line-height: 1.6; }
            QLabel#rightTitle { color: #ffffff; font-size: 22px; font-weight: bold; }

            QLineEdit { 
                background: #111827; border: 1px solid #374151; color: #f3f4f6; 
                padding: 15px; border-radius: 4px; font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid #00d2ff; }

            QPushButton#loginBtn { 
                background: #00d2ff; color: #000; padding: 15px; border-radius: 4px; 
                font-weight: bold; border: none; font-size: 14px;
            }
            QPushButton#loginBtn:hover { background: #00b4d8; }

            QPushButton#bypassBtn {
                background: transparent; color: #64748b; border: 1px dashed #475569;
                padding: 10px; border-radius: 4px; font-size: 12px; margin-top: 10px;
            }
            QPushButton#bypassBtn:hover { color: #00d2ff; border-color: #00d2ff; }

            QPushButton#closeBtn { background: transparent; color: #4b5563; border: none; font-size: 16px; }
            QPushButton#closeBtn:hover { color: #ef4444; }
            QLabel#statusLabel { color: #ef4444; font-size: 12px; }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def shake_animation(self):
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(200)
        start_pos = self.pos()
        anim.setKeyValueAt(0.2, start_pos + QPoint(10, 0))
        anim.setKeyValueAt(0.4, start_pos - QPoint(10, 0))
        anim.setKeyValueAt(0.6, start_pos + QPoint(10, 0))
        anim.setKeyValueAt(0.8, start_pos - QPoint(10, 0))
        anim.setKeyValueAt(1, start_pos)
        anim.start()

    def handle_login(self):
        success, msg = self.auth_service.verify(self.user_input.text(), self.pass_input.text())
        if success:
            self.accept()
        else:
            self.status_label.setText(msg)
            self.shake_animation()

    def bypass_login(self):
        """Bypass check for developer quick launch"""
        self.accept()