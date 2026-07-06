# modules/traffic_flow.py
import datetime
import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QFormLayout, QComboBox,
                             QSlider, QListWidget, QPushButton, QProgressBar,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QBrush
from core.base_module import BaseModule


# --- 1. 交通流动力学核心算法引擎 ---
class GreenshieldsTrafficEngine:
    """基于 Greenshields 理论的流量、速度与密度解算模型"""

    @staticmethod
    def solve_traffic_state(flow_volume, avg_speed, truck_ratio):
        """
        核心数学模型：
        1. 修正大车折算系数(pcu): 真实当量流量 = 基础流量 * (1 + truck_ratio * 1.5)
        2. 计算车流密度 K = Q / V
        3. 根据密度与饱和度评估路网服务水平 (LOS - Level of Service, A-F等级)
        """
        try:
            # 1. 车辆折算 (Passenger Car Unit)
            pcu_factor = 1.0 + (float(truck_ratio) * 1.5)
            equivalent_flow = float(flow_volume) * pcu_factor

            # 2. 求解车流密度 (辆/公里)
            density = equivalent_flow / max(5.0, float(avg_speed))

            # 3. 阻塞密度设定为 150 辆/km，计算饱和度 (Saturation)
            saturation = (density / 150.0) * 100.0
            saturation = max(0.0, min(100.0, saturation))

            # 4. 根据交通部标准评估服务水平 LOS
            if saturation < 25.0:
                return round(saturation, 1), "A 级畅通 (自由流速运行)", "#10b981"
            elif saturation < 45.0:
                return round(saturation, 1), "B 级基本畅通 (微量波动)", "#10b981"
            elif saturation < 70.0:
                return round(saturation, 1), "C 级轻度缓行 (出现车流交织)", "#f59e0b"
            elif saturation < 90.0:
                return round(saturation, 1), "D 级拥堵 (通行能力接近极限)", "#f97316"
            return round(saturation, 1), "F 级严重瘫痪 (路网陷入锁死状态)", "#ef4444"

        except Exception as e:
            return 0.0, f"引擎解析失败: {str(e)}", "#64748b"


# --- 2. 车流统计控制台 ---
class TrafficFlow(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_gate_id = None
        self.init_ui()
        self.load_monitoring_gates()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # 头部标题
        header = QLabel("车路协同路网多维车流量智能监控与拥堵预测系统")
        header.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        self.layout.addWidget(header)

        # 左右切分布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左侧：卡口监控台账 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 15, 0)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["卡口ID", "监控道口", "实时流量(pcu)", "拥堵指数(DPCI)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background: #111827; gridline-color: #1f2937; color: #fff; border-radius: 6px; }
        """)
        self.table.clicked.connect(self.on_gate_selected)

        left_layout.addWidget(QLabel("车路协同实时卡口流:"))
        left_layout.addWidget(self.table)

        # --- 右侧：Greenshields 解析器 ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(25, 25, 25, 25)

        self.detail_title = QLabel("路网宏观流量解算")
        self.detail_title.setObjectName("detailTitle")
        self.detail_title.setStyleSheet("color: #00d2ff; font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.detail_title)

        # 拥堵密度条
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
        self.diagnostic_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.6;")
        right_layout.addWidget(self.diagnostic_lbl)

        # 分割线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #1f2937; height: 1px; border: none;")
        right_layout.addWidget(sep)

        # 交互控制区
        right_layout.addWidget(QLabel("动力学模型环境控制参数 (实时演算):"))
        form = QFormLayout()

        # 1. 实时平均车速滑块
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(5, 120)  # 5 - 120 km/h
        self.speed_slider.setValue(60)
        self.speed_slider.valueChanged.connect(self.run_greenshields_simulation)
        self.speed_lbl = QLabel("60 km/h")
        self.speed_lbl.setStyleSheet("color: #00d2ff;")

        # 2. 货车占比滑块
        self.truck_slider = QSlider(Qt.Orientation.Horizontal)
        self.truck_slider.setRange(0, 80)  # 0% - 80%
        self.truck_slider.setValue(15)
        self.truck_slider.valueChanged.connect(self.run_greenshields_simulation)
        self.truck_lbl = QLabel("15 %")
        self.truck_lbl.setStyleSheet("color: #00d2ff;")

        form.addRow("道口实时平均车速:", self.speed_slider)
        form.addRow("实时速度读取值:", self.speed_lbl)
        form.addRow("重载大货车混入率:", self.truck_slider)
        form.addRow("实时混入率系数:", self.truck_lbl)

        right_layout.addLayout(form)

        # 下发指令按钮
        self.optimize_btn = QPushButton("下发绿波协调控制指令")
        self.optimize_btn.setStyleSheet("""
            QPushButton { background: #10b981; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #059669; }
        """)
        self.optimize_btn.clicked.connect(self.execute_signal_coordination)
        right_layout.addWidget(self.optimize_btn)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([480, 440])
        self.layout.addWidget(splitter)

    def load_monitoring_gates(self):
        """载入路网核心采集设备流数据"""
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

            # 算法求解初始指数
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
        """核心交互：实时重算速度-密度抛物线模型"""
        if not self.active_gate_id:
            return

        info = self.gates_db[self.active_gate_id]
        current_speed = self.speed_slider.value()
        current_truck = self.truck_slider.value() / 100.0

        # 刷新UI滑块文本
        self.speed_lbl.setText(f"{current_speed} km/h")
        self.truck_lbl.setText(f"{int(current_truck * 100)} %")

        # 运行动力学引擎重算
        saturation, los, color = GreenshieldsTrafficEngine.solve_traffic_state(
            info["flow"], current_speed, current_truck
        )

        # 动态反馈UI渲染
        self.detail_title.setText(f"宏观流向解算: {info['name']}")
        self.progress_bar.setValue(int(saturation))
        self.progress_bar.setStyleSheet(f"""
            QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}
            QProgressBar {{ background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }}
        """)

        self.diagnostic_lbl.setText(
            f"【Greenshields 模型动力学参数】\n"
            f"服务水平评估 (LOS): {los}\n"
            f"估计等效拥堵密度比 (K/Kj): {saturation}%\n\n"
            f"优化依据数据:\n"
            f"折算当量车流量 (pcu): {int(info['flow'] * (1.0 + current_truck * 1.5))}\n"
            f"预测空间波速度传播损耗: {(current_speed * (1 - saturation / 100.0)):.1f} km/h"
        )

    def execute_signal_coordination(self):
        if not self.active_gate_id:
            QMessageBox.warning(self, "指令失败", "未选择任何需要下发控制的道口！")
            return
        QMessageBox.information(self, "绿波协调指令下发", "干线信号灯动态配时调整参数已成功同步到现场信号控制器。")

    def refresh_data(self):
        pass

    def save_changes(self):
        pass