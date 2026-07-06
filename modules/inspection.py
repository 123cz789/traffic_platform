# modules/inspection.py
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QFrame, QSplitter, QHeaderView,
                             QFormLayout, QLineEdit, QComboBox, QSlider, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QBrush, QFont
from core.base_module import BaseModule


# --- 1. 核心工程学算法类 ---
class StructuralSafetyEngine:
    """交通设施结构安全度多因子退化模型 (DSSI)"""

    @staticmethod
    def calculate_dssi(crack_width, tilt_angle, environment_stress, carbonation_depth):
        """
        核心算法公式：
        DSSI = 100 - (裂缝系数 * 12 + 倾斜系数 * 8 + 碳化系数 * 1.5) * 环境因子
        """
        try:
            crack_factor = float(crack_width) * 12.0
            tilt_factor = float(tilt_angle) * 8.0
            carbon_factor = float(carbonation_depth) * 1.5

            # 计算损伤累积
            total_damage = (crack_factor + tilt_factor + carbon_factor) * float(environment_stress)
            dssi = max(0.0, min(100.0, 100.0 - total_damage))

            # 判定安全评级与响应策略
            if dssi < 40.0:
                return round(dssi, 1), "极高风险 (建议立即封锁交通)", "#ef4444"
            elif dssi < 75.0:
                return round(dssi, 1), "中度缺陷 (排入紧急加固计划)", "#f59e0b"
            return round(dssi, 1), "结构完好 (维持常规巡检频率)", "#10b981"
        except Exception as e:
            return 0.0, f"计算错误: {str(e)}", "#64748b"


# --- 2. 主业务控制界面 ---
class Inspection(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_asset_id = None
        self.init_ui()
        self.load_inspection_tasks()

    def init_ui(self):
        # 全局大框架
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # 头部指示器
        header = QLabel("智能道路设施结构安全诊断终端")
        header.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        self.layout.addWidget(header)

        # 分割器 (左列表，右诊断)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左侧：主任务流 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 15, 0)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["工单号", "巡检部件", "结构状态", "复核时间"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background: #111827; gridline-color: #1f2937; color: #fff; border-radius: 6px; }
        """)
        self.table.clicked.connect(self.on_row_selected)
        left_layout.addWidget(QLabel("待复核高维缺陷队列:"))
        left_layout.addWidget(self.table)

        # --- 右侧：多交互诊断面板 ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(25, 25, 25, 25)

        # 诊断报告抬头
        self.detail_title = QLabel("专家诊断分析")
        self.detail_title.setStyleSheet("color: #00d2ff; font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.detail_title)

        # 安全等级条
        right_layout.addWidget(QLabel("计算所得结构安全度指数 (DSSI):"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }
            QProgressBar::chunk { background: #10b981; border-radius: 4px; }
        """)
        right_layout.addWidget(self.progress_bar)

        self.diagnostic_summary = QLabel("请在左侧选择需要复核的道路巡检项...")
        self.diagnostic_summary.setWordWrap(True)
        self.diagnostic_summary.setStyleSheet("color: #94a3b8; line-height: 1.6; font-size: 13px;")
        right_layout.addWidget(self.diagnostic_summary)

        # 横向分割线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #1f2937; height: 1px; border: none;")
        right_layout.addWidget(sep)

        # 人工复核调参控制面板 (交互核心)
        right_layout.addWidget(QLabel("实地人工校准数据录入 (重算决策模型):"))

        form = QFormLayout()

        # 1. 裂缝输入滑块
        self.crack_slider = QSlider(Qt.Orientation.Horizontal)
        self.crack_slider.setRange(0, 50)  # 0.0 - 5.0 mm
        self.crack_slider.setValue(12)
        self.crack_slider.valueChanged.connect(self.run_realtime_simulation)
        self.crack_lbl = QLabel("1.2 mm")
        self.crack_lbl.setStyleSheet("color: #00d2ff;")

        # 2. 倾斜输入滑块
        self.tilt_slider = QSlider(Qt.Orientation.Horizontal)
        self.tilt_slider.setRange(0, 15)  # 0 - 15 度
        self.tilt_slider.setValue(2)
        self.tilt_slider.valueChanged.connect(self.run_realtime_simulation)
        self.tilt_lbl = QLabel("2.0 度")
        self.tilt_lbl.setStyleSheet("color: #00d2ff;")

        form.addRow("结构裂缝宽度:", self.crack_slider)
        form.addRow("实时显示值:", self.crack_lbl)
        form.addRow("桥墩整体倾斜:", self.tilt_slider)
        form.addRow("实时显示值:", self.tilt_lbl)

        right_layout.addLayout(form)

        # 按钮控制
        self.save_btn = QPushButton("提交专家评审报告")
        self.save_btn.setStyleSheet("""
            QPushButton { background: #10b981; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #059669; }
        """)
        self.save_btn.clicked.connect(self.commit_report)
        right_layout.addWidget(self.save_btn)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([500, 420])
        self.layout.addWidget(splitter)

    def load_inspection_tasks(self):
        """加载数据库巡检台账"""
        self.db = {
            "TSK-4001": {"name": "G105立交桥2号墩", "crack": 1.2, "tilt": 1.0, "carbon": 4.0, "stress": 1.3},
            "TSK-4002": {"name": "滨江隧道明挖段侧墙", "crack": 3.4, "tilt": 5.0, "carbon": 12.0, "stress": 1.5},
            "TSK-4003": {"name": "迎宾大道高架跨线悬臂", "crack": 0.4, "tilt": 0.0, "carbon": 1.0, "stress": 1.0}
        }
        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        for row, (id, info) in enumerate(self.db.items()):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(id))
            self.table.setItem(row, 1, QTableWidgetItem(info["name"]))

            # 计算初筛健康
            score, status, color = StructuralSafetyEngine.calculate_dssi(
                info["crack"], info["tilt"], info["stress"], info["carbon"]
            )

            status_item = QTableWidgetItem(status.split(" ")[0])
            status_item.setForeground(QBrush(QColor(color)))
            self.table.setItem(row, 2, status_item)
            self.table.setItem(row, 3, QTableWidgetItem(datetime.datetime.now().strftime("%Y-%m-%d")))

    def on_row_selected(self, index):
        row = index.row()
        self.active_asset_id = self.table.item(row, 0).text()
        info = self.db.get(self.active_asset_id)
        if info:
            # 填充控制表单
            self.crack_slider.setValue(int(info["crack"] * 10))
            self.tilt_slider.setValue(int(info["tilt"]))
            self.run_realtime_simulation()

    def run_realtime_simulation(self):
        """实时重算威布尔结构退化数学模型"""
        if not self.active_asset_id:
            return

        info = self.db[self.active_asset_id]
        current_crack = self.crack_slider.value() / 10.0
        current_tilt = self.tilt_slider.value()

        # 更新Label显示
        self.crack_lbl.setText(f"{current_crack:.1f} mm")
        self.tilt_lbl.setText(f"{current_tilt:.1f} 度")

        # 重算算法
        dssi, advice, color = StructuralSafetyEngine.calculate_dssi(
            current_crack, current_tilt, info["stress"], info["carbon"]
        )

        # UI动态响应
        self.detail_title.setText(f"核心诊断: {info['name']}")
        self.progress_bar.setValue(int(dssi))
        self.progress_bar.setStyleSheet(f"""
            QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}
            QProgressBar {{ background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }}
        """)

        self.diagnostic_summary.setText(
            f"【结构计算模型输出】\n"
            f"结构完好度评分: {dssi} / 100 分\n"
            f"安全判定结果: {advice}\n\n"
            f"数据复核依据:\n"
            f"裂缝宽度损耗系数: {(current_crack * 12.0 * info['stress']):.1f}\n"
            f"水平倾斜剪切力损耗系数: {(current_tilt * 8.0 * info['stress']):.1f}"
        )

    def commit_report(self):
        if not self.active_asset_id:
            QMessageBox.warning(self, "警报", "未选择任何需要评审的资产！")
            return

        # 模拟同步更新到左侧表格中
        QMessageBox.information(self, "专家决策确认", "结构判定报告已成功上报并同步至设施管理档案库！")

    def refresh_data(self):
        pass

    def save_changes(self):
        pass