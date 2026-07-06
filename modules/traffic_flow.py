# modules/traffic_flow.py
import datetime
import json
import os
import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QFormLayout, QComboBox,
                             QSlider, QListWidget, QPushButton, QProgressBar,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from core.base_module import BaseModule


class GreenshieldsTrafficEngine:
    @staticmethod
    def solve_traffic_state(flow_volume, avg_speed, truck_ratio):
        try:
            pcu_factor = 1.0 + (float(truck_ratio) * 1.5)
            equivalent_flow = float(flow_volume) * pcu_factor
            density = equivalent_flow / max(5.0, float(avg_speed))

            saturation = (density / 150.0) * 100.0
            saturation = max(0.0, min(100.0, saturation))

            if saturation < 25.0:
                return round(saturation, 1), "A 级畅通 (自由流速)", "#10b981"
            elif saturation < 45.0:
                return round(saturation, 1), "B 级基本畅通", "#10b981"
            elif saturation < 70.0:
                return round(saturation, 1), "C 级轻度缓行", "#f59e0b"
            elif saturation < 90.0:
                return round(saturation, 1), "D 级拥堵", "#f97316"
            return round(saturation, 1), "F 级严重瘫痪", "#ef4444"
        except Exception:
            return 0.0, "解析失败", "#64748b"

    @staticmethod
    def calculate_signal_timing(saturation):
        try:
            total_cycle = 60 + int(saturation * 0.6)
            main_green = max(15, int(total_cycle * (1.0 - saturation / 100.0 * 0.6)))
            side_green = max(10, total_cycle - main_green - 4)
            return main_green, side_green
        except Exception:
            return 30, 20


class TrafficFlow(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_gate_id = None
        self.gates_db = {}
        self.init_ui()
        self.load_monitoring_gates()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        header = QLabel("车路协同路网多维车流量智能监控与拥堵预测系统")
        header.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        self.layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # 左侧：列表容器
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 15, 0)
        left_layout.setSpacing(15)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["卡口ID", "监控道口", "实时流量(pcu)", "拥堵指数(DPCI)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background: #111827; gridline-color: #1f2937; color: #fff; border-radius: 6px; }
        """)
        self.table.clicked.connect(self.on_gate_selected)

        left_layout.addWidget(QLabel("车路协同实时卡口流:"))
        left_layout.addWidget(self.table, stretch=3)

        # 排队论动态瓶颈仿真舱
        self.queue_frame = QFrame()
        self.queue_frame.setObjectName("queueFrame")
        self.queue_frame.setStyleSheet("""
            QFrame#queueFrame { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; padding: 15px; }
            QLabel { color: #64748b; font-size: 11px; font-family: 'Microsoft YaHei'; }
            QLabel#queueTitle { color: #f59e0b; font-weight: bold; font-size: 12px; }
        """)
        queue_layout = QVBoxLayout(self.queue_frame)
        queue_title = QLabel("路网瓶颈 M/M/1 排队溢出分析仪")
        queue_title.setObjectName("queueTitle")

        self.queue_lbl = QLabel(
            "卡口排队阻泥: 0.0%\n"
            "预计车辆滞留队列长度: 0.0 辆\n"
            "排队溢出概率: [ 安全 ]"
        )
        self.queue_progress = QProgressBar()
        self.queue_progress.setRange(0, 100)
        self.queue_progress.setValue(0)
        self.queue_progress.setFormat("排队饱合度: -- %")
        self.queue_progress.setStyleSheet("""
            QProgressBar { background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 18px; font-size: 10px; }
            QProgressBar::chunk { background: #f59e0b; border-radius: 4px; }
        """)

        queue_layout.addWidget(queue_title)
        queue_layout.addWidget(self.queue_lbl)
        queue_layout.addWidget(self.queue_progress)
        left_layout.addWidget(self.queue_frame, stretch=2)

        # 右侧面板
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(25, 25, 25, 25)

        self.detail_title = QLabel("路网宏观流量解算")
        self.detail_title.setStyleSheet("color: #00d2ff; font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.detail_title)

        right_layout.addWidget(QLabel("估计车流拥堵密度饱和比 (K/Kj):"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }
            QProgressBar::chunk { background: #10b981; border-radius: 4px; }
        """)
        right_layout.addWidget(self.progress_bar)

        self.diagnostic_lbl = QLabel("请在左侧选择需要解算的卡口数据...")
        self.diagnostic_lbl.setWordWrap(True)
        self.diagnostic_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.5;")
        right_layout.addWidget(self.diagnostic_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #1f2937; height: 1px; border: none;")
        right_layout.addWidget(sep)

        right_layout.addWidget(QLabel("动力学模型环境控制参数 (实时演算):"))
        form = QFormLayout()
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(5, 120);
        self.speed_slider.setValue(60)
        self.speed_slider.valueChanged.connect(self.run_greenshields_simulation)
        self.speed_lbl = QLabel("60 km/h")
        self.speed_lbl.setStyleSheet("color: #00d2ff;")

        self.truck_slider = QSlider(Qt.Orientation.Horizontal)
        self.truck_slider.setRange(0, 80);
        self.truck_slider.setValue(15)
        self.truck_slider.valueChanged.connect(self.run_greenshields_simulation)
        self.truck_lbl = QLabel("15 %")
        self.truck_lbl.setStyleSheet("color: #00d2ff;")

        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["Greenshields 模型", "Greenberg 对数模型", "Underwood 指数模型"])
        self.algo_combo.currentIndexChanged.connect(self.run_greenshields_simulation)

        form.addRow("道口实时平均车速:", self.speed_slider)
        form.addRow("实时速度读取值:", self.speed_lbl)
        form.addRow("重载大货车混入率:", self.truck_slider)
        form.addRow("实时混入率系数:", self.truck_lbl)
        form.addRow("数学宏观演进模型:", self.algo_combo)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("信控绿波带自适应配时终端 (实时指令流):"))
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 4px; color: #10b981; font-family: 'Consolas'; font-size: 11px; }
        """)
        # 修正点：使用原生的 QSizePolicy 属性
        self.console.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.console)

        self.optimize_btn = QPushButton("下发绿波协调控制指令")
        self.optimize_btn.setStyleSheet("""
            QPushButton { background: #10b981; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #059669; }
        """)
        self.optimize_btn.clicked.connect(self.execute_signal_coordination)
        right_layout.addWidget(self.optimize_btn)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([500, 420])
        self.layout.addWidget(splitter)

    def load_monitoring_gates(self):
        self.gates_db = {
            "GAT-301": {"name": "迎宾路东侧快速道口", "flow": 1480, "speed": 75, "truck": 0.1},
            "GAT-302": {"name": "解放大道西十字交叉口", "flow": 3450, "speed": 15, "truck": 0.3},
            "GAT-303": {"name": "机场大道货运连接线", "flow": 850, "speed": 85, "truck": 0.6}
        }
        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        for row, (id, info) in enumerate(self.gates_db.items()):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(id))
            self.table.setItem(row, 1, QTableWidgetItem(info["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(info["flow"])))

            saturation, los, color = GreenshieldsTrafficEngine.solve_traffic_state(
                info["flow"], info["speed"], info["truck"]
            )

            status_item = QTableWidgetItem(f"{saturation}%")
            status_item.setForeground(QBrush(QColor(color)))
            self.table.setItem(row, 3, status_item)

    def on_gate_selected(self, index):
        row = index.row()
        self.active_gate_id = self.table.item(row, 0).text()
        info = self.gates_db.get(self.active_gate_id)
        if info:
            self.speed_slider.setValue(info["speed"])
            self.truck_slider.setValue(int(info["truck"] * 100))
            self.run_greenshields_simulation()

    def run_greenshields_simulation(self):
        if not self.active_gate_id:
            return

        info = self.gates_db[self.active_gate_id]
        current_speed = self.speed_slider.value()
        current_truck = self.truck_slider.value() / 100.0

        self.speed_lbl.setText(f"{current_speed} km/h")
        self.truck_lbl.setText(f"{int(current_truck * 100)} %")

        saturation, los, color = GreenshieldsTrafficEngine.solve_traffic_state(
            info["flow"], current_speed, current_truck
        )

        self.progress_bar.setValue(int(saturation))
        self.progress_bar.setStyleSheet(f"""
            QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}
            QProgressBar {{ background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }}
        """)

        # 动态刷新左下角 AI 进度指标
        self.queue_progress.setValue(int(saturation * 0.9))
        self.queue_progress.setFormat(f"排队溢出率: {int(saturation * 0.9)}%")
        self.queue_lbl.setText(
            f"卡口排队阻泥: {round(saturation * 0.8, 1)}%\n"
            f"预计车辆滞留队列长度: {round((saturation / 100.0) * 12.0, 1)} 辆\n"
            f"排队溢出概率评估: [ {'🛑 严重排队溢出' if saturation > 70 else '正常安全状态'} ]"
        )

        main_green, side_green = GreenshieldsTrafficEngine.calculate_signal_timing(saturation)

        self.console.clear()
        self.console.addItem(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 加载 Greenshields 动力学算法集...")
        self.console.addItem(f"----------------------------------------")
        self.console.addItem(f"自适应信号放行周期推荐: {main_green + side_green + 4}s")
        self.console.addItem(f"  ├ 主干道绿灯相位: {main_green}s")
        self.console.addItem(f"  └ 支路匝道绿灯相位: {side_green}s")
        self.console.addItem(f"----------------------------------------")
        self.console.scrollToBottom()

    def execute_signal_coordination(self):
        if not self.active_gate_id:
            QMessageBox.warning(self, "指令失败", "未选择任何需要下发控制的道口！")
            return
        QMessageBox.information(self, "绿波协调指令下发", "干线信号灯动态配时调整参数已成功同步到现场信号控制器。")

    def refresh_data(self):
        pass

    def save_changes(self):
        pass