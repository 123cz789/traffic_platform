# ui/main_window.py
import datetime
import random
from PyQt6.QtWidgets import (QMainWindow, QStackedWidget, QListWidget, QHBoxLayout,
                             QVBoxLayout, QWidget, QLabel, QPushButton, QFrame, QSizeGrip, QApplication, QScrollArea)
from PyQt6.QtCore import Qt, QPoint, QTimer
from core.plugin_loader import PluginLoader


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Declare all instance attributes to eliminate static analysis warnings
        self.main_container = None
        self.title_bar = None
        self.status_bar = None
        self.min_btn = None
        self.max_btn = None
        self.close_btn = None
        self.menu_list = None
        self.pages = None
        self.clock_lbl = None
        self.user_lbl = None
        self.telemetry_lbl = None
        self.sidebar_toggle_btn = None
        self.sidebar_collapsed = False
        self._drag_pos = QPoint()

        # Mapping table of modules to support Chinese localization and dynamic folding
        self.modules_config = [
            ("dashboard", "📊  监测总览"),
            ("asset_mng", "📋  资产台账"),
            ("inspection", "🔍  智能巡检"),
            ("maintenance", "🛠️  维保调度"),
            ("lifecycle", "⏳  寿命预测"),
            ("traffic_flow", "🚗  车流统计"),
            ("gis_map", "🗺️  空间地图"),
            ("emergency", "🚨  应急处置"),
            ("archives", "📂  文献档案")
        ]

        # Configure frameless window with translucent backdrop
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Adapt window dimensions dynamically based on available screen space
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            screen_geometry = primary_screen.availableGeometry()
            # Constrain window proportions safely to avoid overshooting taskbar
            default_width = min(1000, int(screen_geometry.width() * 0.75))
            default_height = min(600, int(screen_geometry.height() * 0.70))
        else:
            default_width = 960
            default_height = 560

        self.resize(default_width, default_height)

        # Build user interface and apply QSS
        self.init_global_ui()
        self.apply_theme_styles()
        self.start_system_timers()

    def init_global_ui(self):
        self.main_container = QFrame()
        self.main_container.setObjectName("mainContainer")

        # Vertical base layout
        global_layout = QVBoxLayout(self.main_container)
        global_layout.setContentsMargins(0, 0, 0, 0)
        global_layout.setSpacing(0)

        # --- 1. Top Custom Title Bar (Customized with dynamic widgets) ---
        self.title_bar = QFrame()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(50)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(15, 0, 15, 0)
        title_layout.setSpacing(15)

        # Sidebar Collapse Trigger Button ☰
        self.sidebar_toggle_btn = QPushButton("☰")
        self.sidebar_toggle_btn.setObjectName("sidebarToggleBtn")
        self.sidebar_toggle_btn.setFixedSize(30, 30)
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)
        title_layout.addWidget(self.sidebar_toggle_btn)

        # Core Title
        system_title = QLabel("交通工程设施全生命周期运维平台")
        system_title.setObjectName("systemTitle")
        title_layout.addWidget(system_title)

        title_layout.addStretch()

        # Security Authorization Badge
        self.user_lbl = QLabel("🛡️ 授权凭证: admin (特级管理员)")
        self.user_lbl.setObjectName("userBadge")
        title_layout.addWidget(self.user_lbl)

        # Digital Real-Time Clock
        self.clock_lbl = QLabel()
        self.clock_lbl.setObjectName("clockLabel")
        title_layout.addWidget(self.clock_lbl)

        # Windows Controls Group
        self.min_btn = QPushButton("—")
        self.min_btn.setObjectName("windowCtrlBtn")
        self.min_btn.clicked.connect(self.showMinimized)

        self.max_btn = QPushButton("⛶")
        self.max_btn.setObjectName("windowCtrlBtn")
        self.max_btn.clicked.connect(self.toggle_maximize)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeCtrlBtn")
        self.close_btn.clicked.connect(self.close)

        title_layout.addWidget(self.min_btn)
        title_layout.addWidget(self.max_btn)
        title_layout.addWidget(self.close_btn)
        global_layout.addWidget(self.title_bar)

        # --- 2. Central Workspace ---
        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        self.menu_list = QListWidget()
        self.menu_list.setFixedWidth(240)

        self.pages = QStackedWidget()
        self.pages.setObjectName("workspacePages")

        workspace_layout.addWidget(self.menu_list)
        workspace_layout.addWidget(self.pages)
        global_layout.addWidget(workspace)

        # --- 3. Bottom Status Bar with Custom Hardware Telemetry ---
        self.status_bar = QFrame()
        self.status_bar.setObjectName("statusBar")
        self.status_bar.setFixedHeight(22)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(15, 0, 5, 0)

        self.telemetry_lbl = QLabel("内核加载中...")
        self.telemetry_lbl.setObjectName("statusInfo")
        status_layout.addWidget(self.telemetry_lbl)
        status_layout.addStretch()

        # Resizing grip
        size_grip = QSizeGrip(self)
        status_layout.addWidget(size_grip)

        global_layout.addWidget(self.status_bar)

        self.setCentralWidget(self.main_container)
        self.init_modules()

        # Bind signals
        self.menu_list.currentRowChanged.connect(self.on_menu_changed)

    def init_modules(self):
        """Loads submodules, wrap them inside custom scroll containers to prevent window stretching"""
        for m_file, m_name in self.modules_config:
            self.menu_list.addItem(m_name)
            try:
                # Dynamically instantiate the business module
                instance = PluginLoader.load_module(m_file)

                # Create a standardized scroll container for the module
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_area.setWidget(instance)

                # Apply custom dark-themed QSS to the scrollbar of the container
                scroll_area.setStyleSheet("""
                    QScrollArea {
                        border: none;
                        background-color: transparent;
                    }
                    QScrollBar:vertical {
                        border: none;
                        background: #0f1219;
                        width: 8px;
                        margin: 0px;
                    }
                    QScrollBar::handle:vertical {
                        background: #1f2937;
                        min-height: 20px;
                        border-radius: 4px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #00d2ff;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        border: none;
                        background: none;
                    }
                    QScrollBar:horizontal {
                        border: none;
                        background: #0f1219;
                        height: 8px;
                        margin: 0px;
                    }
                    QScrollBar::handle:horizontal {
                        background: #1f2937;
                        min-width: 20px;
                        border-radius: 4px;
                    }
                    QScrollBar::handle:horizontal:hover {
                        background: #00d2ff;
                    }
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                        border: none;
                        background: none;
                    }
                """)

                self.pages.addWidget(scroll_area)
            except Exception as e:
                fallback = QLabel(f"模块 [{m_name}] 正在进行数据重构...\n\n错误分析: {e}")
                fallback.setStyleSheet("color: #ef4444; font-size: 15px; font-family: 'Consolas';")
                fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.pages.addWidget(fallback)

    def start_system_timers(self):
        """Initializes high-frequency polling loops for hardware metrics & clock"""
        # Clock timer (1Hz)
        clock_timer = QTimer(self)
        clock_timer.timeout.connect(self.update_clock)
        clock_timer.start(1000)
        self.update_clock()

        # Telemetry metrics timer (0.5Hz)
        telemetry_timer = QTimer(self)
        telemetry_timer.timeout.connect(self.update_telemetry)
        telemetry_timer.start(2000)
        self.update_telemetry()

    def update_clock(self):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_lbl.setText(current_time)

    def update_telemetry(self):
        """Simulates real-time system performance fluctuations to increase technical aesthetics"""
        cpu = round(random.uniform(5.2, 14.5), 1)
        ram = round(random.uniform(32.4, 34.8), 1)
        self.telemetry_lbl.setText(f"系统内核: 运行正常 | 核心状态: 连通 | CPU 负载: {cpu}% | 内存占用: {ram}%")

    def toggle_sidebar(self):
        """Collapses the navigation list to 60px wide while keeping only Emojis"""
        self.sidebar_collapsed = not self.sidebar_collapsed
        if self.sidebar_collapsed:
            self.menu_list.setFixedWidth(64)
            for i in range(self.menu_list.count()):
                item = self.menu_list.item(i)
                item.setData(Qt.ItemDataRole.UserRole, item.text())
                emoji_only = item.text()[:2].strip()
                item.setText(emoji_only)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.menu_list.setFixedWidth(240)
            for i in range(self.menu_list.count()):
                item = self.menu_list.item(i)
                original_text = item.data(Qt.ItemDataRole.UserRole)
                if original_text:
                    item.setText(original_text)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText("⛶")
        else:
            self.showMaximized()
            self.max_btn.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 50:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and event.position().y() < 50:
            if hasattr(self, '_drag_pos'):
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()

    def on_menu_changed(self, index):
        """Triggered upon switching menu options, safe unwrapping from QScrollArea before data refresh"""
        self.pages.setCurrentIndex(index)
        current_scroll = self.pages.widget(index)

        # Unpack the underlying BaseModule from its QScrollArea wrapper cleanly
        if current_scroll and isinstance(current_scroll, QScrollArea):
            current_widget = current_scroll.widget()
            if current_widget and hasattr(current_widget, "refresh_data"):
                current_widget.refresh_data()

    def apply_theme_styles(self):
        qss = """
        QFrame#mainContainer { 
            background: #090b10; 
            border-radius: 12px; 
            border: 1px solid #2a2e3e; 
        }
        QFrame#titleBar { 
            background: #0f1219; 
            border-top-left-radius: 12px; 
            border-top-right-radius: 12px;
            border-bottom: 1px solid #1f2937;
        }
        QLabel#systemTitle { 
            color: #00d2ff; 
            font-size: 14px; 
            font-weight: bold; 
        }
        QLabel#userBadge {
            color: #10b981;
            font-size: 11px;
            background: #111827;
            padding: 4px 10px;
            border-radius: 4px;
            border: 1px solid #1f2937;
        }
        QLabel#clockLabel {
            color: #94a3b8;
            font-size: 12px;
            font-family: 'Consolas';
        }
        QPushButton#sidebarToggleBtn {
            background: transparent;
            color: #94a3b8;
            border: none;
            font-size: 16px;
        }
        QPushButton#sidebarToggleBtn:hover {
            color: #00d2ff;
        }
        QPushButton#windowCtrlBtn { 
            background: transparent; 
            color: #5a5f73; 
            border: none; 
            font-size: 12px; 
            width: 30px; 
            height: 30px; 
        }
        QPushButton#windowCtrlBtn:hover { color: #00d2ff; }
        QPushButton#closeCtrlBtn { 
            background: transparent; 
            color: #5a5f73; 
            border: none; 
            font-size: 14px; 
            width: 30px; 
            height: 30px; 
        }
        QPushButton#closeCtrlBtn:hover { color: #ff5555; }

        QListWidget { 
            background: #0f1219; 
            border: none; 
            border-right: 1px solid #1f2937; 
            color: #94a3b8; 
            font-size: 14px; 
            font-weight: bold; 
            outline: none;
        }
        QListWidget::item { padding: 15px 20px; border-left: 3px solid transparent; }
        QListWidget::item:selected { 
            background: #111827; 
            color: #00d2ff; 
            border-left: 3px solid #00d2ff; 
            background-color: #111827;
        }
        QListWidget::item:hover { background: #161b22; color: #fff; }

        QFrame#statusBar {
            background: #0f1219;
            border-top: 1px solid #1f2937;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
        }
        QLabel#statusInfo {
            color: #4b5563;
            font-size: 11px;
            font-family: 'Microsoft YaHei';
        }
        """
        self.setStyleSheet(qss)