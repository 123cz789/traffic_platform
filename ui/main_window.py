# ui/main_window.py
from PyQt6.QtWidgets import (QMainWindow, QStackedWidget, QListWidget, QHBoxLayout,
                             QVBoxLayout, QWidget, QLabel, QPushButton, QFrame, QSizeGrip, QApplication)
from PyQt6.QtCore import Qt, QPoint
from core.plugin_loader import PluginLoader


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. 显式声明所有属性，消除 PyCharm 静态分析警告
        self.main_container = None
        self.title_bar = None
        self.status_bar = None
        self.min_btn = None
        self.max_btn = None
        self.close_btn = None
        self.menu_list = None
        self.pages = None
        self._drag_pos = QPoint()

        # 2. 启用无边框和半透明属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 3. 稳健修复：自适应屏幕大小 (绝对不超出任务栏，无 NoneType 警告)
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            screen_geometry = primary_screen.availableGeometry()
            default_width = min(1200, int(screen_geometry.width() * 0.8))
            default_height = min(720, int(screen_geometry.height() * 0.85))
        else:
            default_width = 1100
            default_height = 700

        self.resize(default_width, default_height)

        # 4. 构造界面与样式
        self.init_global_ui()
        self.apply_theme_styles()

    def init_global_ui(self):
        # 全局主容器
        self.main_container = QFrame()
        self.main_container.setObjectName("mainContainer")

        # 纵向主布局：顶部标题栏 -> 中部工作区 -> 底部状态栏(带缩放手柄)
        global_layout = QVBoxLayout(self.main_container)
        global_layout.setContentsMargins(0, 0, 0, 0)
        global_layout.setSpacing(0)

        # --- 顶部自定义标题栏 ---
        self.title_bar = QFrame()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(50)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(20, 0, 20, 0)

        system_title = QLabel("交通工程设施全生命周期运维平台")
        system_title.setObjectName("systemTitle")
        title_layout.addWidget(system_title)
        title_layout.addStretch()

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

        # --- 中部工作区 ---
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

        # --- 底部：系统状态与缩放栏 (解决无边框缩放问题) ---
        self.status_bar = QFrame()
        self.status_bar.setObjectName("statusBar")
        self.status_bar.setFixedHeight(22)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(15, 0, 5, 0)

        status_info = QLabel("系统内核: 正常 | 区域网关: 连通")
        status_info.setObjectName("statusInfo")
        status_layout.addWidget(status_info)
        status_layout.addStretch()

        # 核心部件：右下角无缝放置缩放手柄
        size_grip = QSizeGrip(self)
        status_layout.addWidget(size_grip)

        # 组装至全局纵向布局
        global_layout.addWidget(self.status_bar)

        self.setCentralWidget(self.main_container)

        # 载入业务子模块
        self.init_modules()

        # 槽函数绑定
        self.menu_list.currentRowChanged.connect(self.pages.setCurrentIndex)

    def init_modules(self):
        modules_config = [
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

        for m_file, m_name in modules_config:
            self.menu_list.addItem(m_name)
            try:
                instance = PluginLoader.load_module(m_file)
                self.pages.addWidget(instance)
            except Exception as e:
                fallback = QLabel(f"模块 [{m_name}] 正在进行数据重构...\n\n错误分析: {e}")
                fallback.setStyleSheet("color: #ef4444; font-size: 15px; font-family: 'Consolas';")
                fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.pages.addWidget(fallback)

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