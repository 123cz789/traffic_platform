# modules/dashboard.py
import random
import math
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                             QFrame, QSplitter, QFormLayout, QSlider, QListWidget, QPushButton, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from core.base_module import BaseModule


# --- 1. 核心算法层：时序异常检测与香农熵计算引擎 ---
class AdvancedTelemetryEngine(QObject):
    """
    高级遥测计算内核：
    1. 实现基于滑动窗口的实时 Z-Score 时序异常检测算法
    2. 实现基于信息论的香农信息熵(Shannon Entropy)路网混沌度计算算法
    """
    telemetry_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.window_size = 20
        self.traffic_history = []
        self.base_traffic = 1500
        self.noise_multiplier = 1.0
        self.z_threshold = 2.0

    def calculate_shannon_entropy(self, traffic_val):
        """核心物理算法：计算路网流量分布的香农信息熵"""
        try:
            # 模拟三个路区的子流量分配比例
            p1 = min(0.9, max(0.1, 0.4 + random.uniform(-0.05, 0.05)))
            p2 = min(0.9, max(0.1, 0.35 + random.uniform(-0.03, 0.03)))
            p3 = max(0.02, 1.0 - p1 - p2)

            # 计算熵值 H = -sum(pi * log2(pi))
            entropy = - (p1 * math.log2(p1) + p2 * math.log2(p2) + p3 * math.log2(p3))
            return round(entropy, 3)
        except Exception:
            return 1.0

    def process_sensors(self, force_anomaly=False):
        # 1. 模拟产生包含高斯随机噪声的流量数据
        noise = random.gauss(0, 120) * self.noise_multiplier
        raw_traffic = int(self.base_traffic + noise)
        if force_anomaly:
            raw_traffic = int(raw_traffic * 2.3)  # 强行注入异常流量

        self.traffic_history.append(raw_traffic)
        if len(self.traffic_history) > self.window_size:
            self.traffic_history.pop(0)

        # 2. 求解滑动窗口的 Z-Score
        z_score = 0.0
        std_dev = 0.0
        if len(self.traffic_history) >= 5:
            mean = sum(self.traffic_history) / len(self.traffic_history)
            variance = sum((x - mean) ** 2 for x in self.traffic_history) / len(self.traffic_history)
            std_dev = math.sqrt(variance)
            if std_dev > 0:
                z_score = (raw_traffic - mean) / std_dev

        # 3. 计算香农信息熵
        entropy = self.calculate_shannon_entropy(raw_traffic)

        # 4. 判断异常阈值
        is_anomaly = abs(z_score) > self.z_threshold

        # 估算负荷比率
        load = min(100.0, max(5.0, (raw_traffic / 3200.0) * 100))
        temp = int(35 + (load / 100.0) * 20 + random.randint(-1, 1))

        self.telemetry_ready.emit({
            "traffic": raw_traffic,
            "traffic_z": round(z_score, 2),
            "std_dev": round(std_dev, 1),
            "load": round(load, 1),
            "temp": temp,
            "entropy": entropy,
            "is_anomaly": is_anomaly,
            "health": max(10, int(100 - abs(z_score) * 12 - (entropy - 1.2) * 25))
        })


# --- 2. 视觉组件：卡口数据卡 ---
class TelemetryCard(QFrame):
    def __init__(self, title, unit, color="#00d2ff"):
        super().__init__()
        self.normal_color = color
        self.setMinimumSize(180, 110)
        self.setObjectName("telCard")
        self.setStyleSheet(f"""
            QFrame#telCard {{ background: #111827; border-radius: 6px; border: 1px solid #1f2937; }}
            QLabel#title {{ color: #64748b; font-size: 12px; }}
            QLabel#value {{ color: {color}; font-size: 28px; font-weight: bold; font-family: 'Consolas'; }}
            QLabel#unit {{ color: #475569; font-size: 11px; }}
        """)
        layout = QVBoxLayout(self)
        self.lbl_title = QLabel(title);
        self.lbl_title.setObjectName("title")
        self.lbl_value = QLabel("0");
        self.lbl_value.setObjectName("value")
        self.lbl_unit = QLabel(unit);
        self.lbl_unit.setObjectName("unit")
        layout.addWidget(self.lbl_title)
        layout.addStretch()
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_unit)

    def set_val(self, val, alert=False):
        self.lbl_value.setText(str(val))
        if alert:
            self.lbl_value.setStyleSheet("color: #ef4444; font-size: 28px; font-weight: bold;")
        else:
            self.lbl_value.setStyleSheet(f"color: {self.normal_color}; font-size: 28px; font-weight: bold;")


# --- 3. Dashboard 主监控大屏 ---
class Dashboard(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = AdvancedTelemetryEngine()
        self.manual_anomaly = False
        self.init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick_pipeline)
        self.timer.start(1000)  # 1Hz 采样频率

    def init_ui(self):
        # 整体横向三栏式排版
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)

        # --- 独特排版：左栏 (参数控制面板) ---
        self.left_panel = QFrame()
        self.left_panel.setObjectName("leftPanel")
        self.left_panel.setFixedWidth(240)
        self.left_panel.setStyleSheet("""
            QFrame#leftPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }
            QLabel { color: #94a3b8; font-size: 11px; }
        """)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)

        left_layout.addWidget(QLabel("物理层仿真参数调节:"), alignment=Qt.AlignmentFlag.AlignTop)

        form = QFormLayout()
        # 1. 基准流量调节
        self.base_slider = QSlider(Qt.Orientation.Horizontal)
        self.base_slider.setRange(500, 2500)
        self.base_slider.setValue(1500)
        self.base_slider.valueChanged.connect(self.sync_sliders)
        self.base_lbl = QLabel("1500 pcu")
        self.base_lbl.setStyleSheet("color: #00d2ff;")

        # 2. 噪声强度调节
        self.noise_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_slider.setRange(0, 30)  # 0.0x - 3.0x
        self.noise_slider.setValue(10)
        self.noise_slider.valueChanged.connect(self.sync_sliders)
        self.noise_lbl = QLabel("1.0x (高斯标准)")
        self.noise_lbl.setStyleSheet("color: #00d2ff;")

        form.addRow("基准车流量:", self.base_slider)
        form.addRow("显示数值:", self.base_lbl)
        form.addRow("环境随机噪声:", self.noise_slider)
        form.addRow("显示倍率:", self.noise_lbl)
        left_layout.addLayout(form)

        left_layout.addStretch()
        # 一键注入故障
        self.inject_btn = QPushButton("强行注入冲击波流量")
        self.inject_btn.setStyleSheet("""
            QPushButton { background: #ef4444; color: white; padding: 10px; border-radius: 4px; font-weight: bold; border: none; }
            QPushButton:hover { background: #dc2626; }
        """)
        self.inject_btn.clicked.connect(self.inject_traffic_spike)
        left_layout.addWidget(self.inject_btn)

        # --- 独特排版：中栏 (实时指标矩阵) ---
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)

        middle_layout.addWidget(QLabel("多维传感器遥测状态矩阵:"))

        grid = QGridLayout()
        self.cards = {
            "traffic": TelemetryCard("干线流量", "pcu / h", "#00d2ff"),
            "load": TelemetryCard("空间饱和度", "%", "#f59e0b"),
            "temp": TelemetryCard("核心温升", "℃", "#06b6d4"),
            "health": TelemetryCard("健康评分", "Score", "#10b981")
        }
        grid.addWidget(self.cards["traffic"], 0, 0)
        grid.addWidget(self.cards["load"], 0, 1)
        grid.addWidget(self.cards["temp"], 1, 0)
        grid.addWidget(self.cards["health"], 1, 1)
        middle_layout.addLayout(grid)

        # 下方横向集成：香农信息熵混沌度表
        middle_layout.addSpacing(15)
        middle_layout.addWidget(QLabel("路网时序信息熵 (香农混沌度测算仪):"))
        self.entropy_bar = QProgressBar()
        self.entropy_bar.setRange(0, 200)  # 0.0 - 2.0 bits
        self.entropy_bar.setValue(110)
        self.entropy_bar.setStyleSheet("""
            QProgressBar { background: #111827; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 22px; }
            QProgressBar::chunk { background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #ef4444); border-radius: 4px; }
        """)
        middle_layout.addWidget(self.entropy_bar)

        # --- 独特排版：右栏 (时序演算控制台) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("时序特征解算终端 (1Hz 实时分析流):"))
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 6px; color: #10b981; font-family: 'Consolas'; font-size: 11px; }
        """)
        right_layout.addWidget(self.console)

        # 组装三栏
        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(middle_widget, stretch=2)
        self.main_layout.addWidget(right_widget, stretch=1)

        self.engine.telemetry_ready.connect(self.on_telemetry_synced)

    def sync_sliders(self):
        self.engine.base_traffic = self.base_slider.value()
        self.engine.noise_multiplier = self.noise_slider.value() / 10.0

        self.base_lbl.setText(f"{self.engine.base_traffic} pcu")
        self.noise_lbl.setText(f"{self.engine.noise_multiplier:.1f}x")

    def inject_traffic_spike(self):
        self.manual_anomaly = True
        self.console.addItem(f"[{datetime.now().strftime('%H:%M:%S')}] 外部干预: 强制注入交通流冲击波...")

    def tick_pipeline(self):
        self.engine.process_sensors(self.manual_anomaly)
        self.manual_anomaly = False

    def on_telemetry_synced(self, data):
        # 刷新四个核心卡片
        self.cards["traffic"].set_val(data["traffic"], data["is_anomaly"])
        self.cards["load"].set_val(data["load"])
        self.cards["temp"].set_val(data["temp"], data["temp"] > 52)
        self.cards["health"].set_val(data["health"])

        # 刷新信息熵进度条
        self.entropy_bar.setValue(int(data["entropy"] * 100))
        self.entropy_bar.setFormat(f"熵值: {data['entropy']} bits (混沌度)")

        # 写入右侧时序分析终端
        time_str = datetime.now().strftime('%H:%M:%S')
        self.console.addItem(f"[{time_str}] 时序采样特征集:")
        self.console.addItem(f" ├ 滚动标准差 (Std_Dev): {data['std_dev']} pcu")
        self.console.addItem(f" ├ 瞬时 Z-Score 偏离值: {data['traffic_z']}")
        self.console.addItem(f" └ 香农信息熵混沌度: {data['entropy']} bits")
        if data["is_anomaly"]:
            self.console.addItem(f" ⚠️ [警报] 瞬时Z-Score偏离越界! 检测到突发拥堵.")
        self.console.addItem(f"----------------------------------------")

        if self.console.count() > 40:
            self.console.takeItem(0)
        self.console.scrollToBottom()

    def refresh_data(self):
        pass

    def save_changes(self):
        pass