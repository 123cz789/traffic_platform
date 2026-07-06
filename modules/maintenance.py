# modules/maintenance.py
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QFrame, QSplitter, QHeaderView,
                             QFormLayout, QComboBox, QSlider, QListWidget, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QBrush
from core.base_module import BaseModule


# --- 1. 核心算法层：最优派单路径优化引擎 ---
class MaintenanceSchedulerEngine:
    """基于多属性决策矩阵(MADM)与启发式成本估计的派单路径优化模型"""

    @staticmethod
    def calculate_priority_score(distance, traffic_congestion, urgency_level, weather_factor):
        """
        核心数学模型：
        调度响应成本 = (物理距离 * 拥堵比率 * 气象阻尼) / 设备紧急度权重
        分值越低，代表该路径越优，越应该被优先派单调度。
        """
        try:
            # 基础阻泥计算
            road_resistance = float(distance) * float(traffic_congestion) * float(weather_factor)
            # 加权计算优先级成本
            dispatch_cost = road_resistance / float(urgency_level)
            # 估算抵达时间 (ETA) = 距离 * 2.5 * 拥堵系数 * 天气恶劣度
            estimated_eta = int(float(distance) * 2.5 * float(traffic_congestion) * float(weather_factor))
            return round(dispatch_cost, 2), max(5, estimated_eta)
        except ZeroDivisionError:
            return 999.0, 999


# --- 2. 主业务控制界面 ---
class Maintenance(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_row = -1
        self.init_ui()
        self.load_active_fault_data()

    def init_ui(self):
        # 纵向主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # 模块大标题
        header = QLabel("智能交通维保工单与资源协同调优控制台")
        header.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        self.layout.addWidget(header)

        # 分割布局 (工单列表 vs 派单控制器)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左侧：待派单工单列表 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 15, 0)

        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(["工单ID", "故障设备", "距离中队 (km)", "路网拥堵率"])
        # 修正崩溃：使用正确的 horizontalHeader() 方法
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.setStyleSheet("""
            QTableWidget { background: #111827; gridline-color: #1f2937; color: #fff; border-radius: 6px; }
        """)
        self.task_table.clicked.connect(self.on_job_selected)

        left_layout.addWidget(QLabel("待指派紧急抢修任务流:"))
        left_layout.addWidget(self.task_table)

        # --- 右侧：智能路径控制台 ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(25, 25, 25, 25)

        right_layout.addWidget(QLabel("多约束决策中心"), alignment=Qt.AlignmentFlag.AlignTop)

        # 模拟调节控制面板
        form = QFormLayout()

        # 1. 天气阻尼系数滑动条
        self.weather_slider = QSlider(Qt.Orientation.Horizontal)
        self.weather_slider.setRange(10, 250)  # 1.0 - 2.5 倍天气恶劣度
        self.weather_slider.setValue(100)
        self.weather_slider.valueChanged.connect(self.run_realtime_routing)
        self.weather_lbl = QLabel("1.0x (气象晴朗)")
        self.weather_lbl.setStyleSheet("color: #00d2ff;")

        # 2. 维保战队选择
        self.squad_combo = QComboBox()
        self.squad_combo.addItems(["抢修一分队 (重装设备组)", "运维二分队 (轻量巡检组)", "特勤保障队 (直属突击队)"])
        self.squad_combo.currentIndexChanged.connect(self.run_realtime_routing)

        form.addRow("气象环境损耗系数:", self.weather_slider)
        form.addRow("实时损耗计算值:", self.weather_lbl)
        form.addRow("指定出勤突击车队:", self.squad_combo)
        right_layout.addLayout(form)

        # 算法输出黑框终端
        right_layout.addWidget(QLabel("最优化调度路径指令生成 (实时重算):"))
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 4px; color: #10b981; font-family: 'Consolas'; font-size: 12px; }
        """)
        right_layout.addWidget(self.console)

        # 一键下发指令
        self.dispatch_btn = QPushButton("下达最优路径调度令")
        self.dispatch_btn.setStyleSheet("""
            QPushButton { background: #10b981; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #059669; }
        """)
        self.dispatch_btn.clicked.connect(self.trigger_dispatch)
        right_layout.addWidget(self.dispatch_btn)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([500, 420])
        self.layout.addWidget(splitter)

    def load_active_fault_data(self):
        """加载当前活跃的道路突发事件清单"""
        self.jobs_db = {
            "JOB-901": {"name": "G105立交桥应力异常", "dist": 4.2, "cong": 1.1, "urgency": 5},
            "JOB-902": {"name": "滨江隧道机柜温度过载", "dist": 8.5, "cong": 2.1, "urgency": 4},
            "JOB-903": {"name": "迎宾路主干线红绿灯失联", "dist": 2.1, "cong": 1.0, "urgency": 3}
        }
        self.populate_jobs_table()

    def populate_task_table(self):
        pass  # 占位，符合框架

    def populate_jobs_table(self):
        self.task_table.setRowCount(0)
        for row, (id, info) in enumerate(self.jobs_db.items()):
            self.task_table.insertRow(row)
            self.task_table.setItem(row, 0, QTableWidgetItem(id))
            self.task_table.setItem(row, 1, QTableWidgetItem(info["name"]))
            self.task_table.setItem(row, 2, QTableWidgetItem(f"{info['dist']} km"))
            self.task_table.setItem(row, 3, QTableWidgetItem(f"{info['cong']}x"))

    def on_job_selected(self, index):
        self.active_row = index.row()
        self.run_realtime_routing()

    def run_realtime_routing(self):
        """核心交互：实时重算多维决策派单矩阵"""
        if self.active_row < 0:
            self.console.addItem("等待选择具体派单条目...")
            return

        id = self.task_table.item(self.active_row, 0).text()
        info = self.jobs_db.get(id)
        if not info: return

        # 获取当前 UI 滑动参数
        weather_factor = self.weather_slider.value() / 100.0
        self.weather_lbl.setText(f"{weather_factor:.2f}x" + (" (暴雨大雾)" if weather_factor > 1.5 else " (气候良好)"))

        # 核心决策算法重算
        cost, eta = MaintenanceSchedulerEngine.calculate_priority_score(
            info["dist"], info["cong"], info["urgency"], weather_factor
        )

        # 终端文字输出
        self.console.clear()
        self.console.addItem(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 载入决策对象: {info['name']}")
        self.console.addItem(f"调度策略: {self.squad_combo.currentText()}")
        self.console.addItem(f"----------------------------------------")
        self.console.addItem(f"路网阻尼计算开销: {cost} pts")
        self.console.addItem(f"设备预估抵达时间 (ETA): {eta} 分钟")
        self.console.addItem(f"----------------------------------------")
        if cost < 2.5:
            self.console.addItem("算法建议: 该任务处于最优路径节点，推荐立即派遣！")
        else:
            self.console.addItem("算法建议: 路径损耗较大，建议等待协同调度或更换近处车队。")

    def trigger_dispatch(self):
        if self.active_row < 0:
            QMessageBox.warning(self, "指令失败", "请先在左侧选择需要派单的故障工单！")
            return
        QMessageBox.information(self, "调度指令已下发", "智能最优化路径包已成功推送到出勤车辆终端！")

    def refresh_data(self):
        pass

    def save_changes(self):
        pass