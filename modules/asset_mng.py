# modules/asset_mng.py
import math
import random
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QFormLayout, QComboBox,
                             QSlider, QListWidget, QPushButton, QProgressBar,
                             QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QBrush
from core.base_module import BaseModule


# --- 1. 核心算法层：威布尔可靠性衰变预测引擎 ---
class WeibullReliabilityEngine:
    """基于威布尔分布与浴盆曲线特征的设施退化预测算法"""

    @staticmethod
    def predict_failure_metrics(operating_hours, env_stress=1.1, maint_count=2, temp=35):
        """
        核心物理算法：
        1. 耗损系数 beta 随着役龄增加而增大 (beta > 1 意味着设备进入耗损故障期)
        2. 尺度特征参数 eta 受环境温度与外部应力双重惩罚耦合
        3. F(t) = 1 - e^(-(t/eta)^beta)
        """
        try:
            # 形状参数 (Shape Parameter) - 随累计运行时间非线性增加
            beta = 1.0 + (float(operating_hours) / 10000.0)

            # 温度惩罚因子 (Arrhenius 化学反应速率公式简化版)
            temp_penalty = math.exp((float(temp) - 25.0) / 40.0)

            # 尺度参数 (Scale Parameter) - 受应力和温度双重抑制
            eta = 12000.0 / (float(env_stress) * temp_penalty)

            # 维保补偿计算
            effective_hours = max(100.0, float(operating_hours) - (float(maint_count) * 900.0))

            # 计算可靠度 R(t) = e^(-(t/eta)^beta)
            reliability = math.exp(- math.pow(effective_hours / eta, beta))
            failure_probability = 1.0 - reliability

            # 评估所属浴盆曲线阶段
            if beta < 1.1:
                phase = "早期故障期 (磨合阶段)"
                color = "#0ea5e9"
            elif beta < 1.8:
                phase = "偶然故障期 (稳定运行)"
                color = "#10b981"
            else:
                phase = "耗损故障期 (急需报废)"
                color = "#ef4444"

            # 估算 MTBF
            mtbf = int(eta * math.gamma(1.0 + 1.0 / beta))

            return round(failure_probability * 100, 1), mtbf, phase, color

        except Exception:
            return 0.0, 1000, "状态未知", "#64748b"


# --- 2. 资产台账主界面 ---
class AssetMng(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_asset_id = None
        self.db = {}  # 初始化属性
        self.init_ui()
        self.load_sample_database()

    def init_ui(self):
        # 整体布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        header = QLabel("路网设施资产台账与威布尔可靠性深度预测控制台")
        header.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        toolbar.addWidget(header)
        toolbar.addStretch()

        # 快速仿真按钮
        self.sync_btn = QPushButton("整轨应力荷载重算")
        self.sync_btn.setStyleSheet("""
            QPushButton { background: #10b981; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #059669; }
        """)
        self.sync_btn.clicked.connect(self.simulate_stress_growth)
        toolbar.addWidget(self.sync_btn)
        self.layout.addLayout(toolbar)

        # 三栏非对称式空间切分布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左栏：台账主表 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("模糊查找资产名称/流水号...")
        self.search_input.setStyleSheet("""
            QLineEdit { background: #111827; border: 1px solid #1f2937; color: #fff; padding: 10px; border-radius: 4px; }
        """)
        self.search_input.textChanged.connect(self.filter_ledger)
        search_layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "设施名称", "累计时间(h)", "维保频次", "出厂寿命(h)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("QTableWidget { background: #111827; gridline-color: #1f2937; color: #fff; }")
        self.table.clicked.connect(self.on_asset_clicked)

        left_layout.addLayout(search_layout)
        left_layout.addWidget(self.table)

        # --- 中栏：威布尔寿命诊断面板 ---
        self.middle_panel = QFrame()
        self.middle_panel.setObjectName("middlePanel")
        self.middle_panel.setStyleSheet(
            "QFrame#middlePanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        middle_layout = QVBoxLayout(self.middle_panel)
        middle_layout.setContentsMargins(20, 20, 20, 20)

        self.detail_title = QLabel("专家可靠性分析")
        self.detail_title.setStyleSheet("color: #00d2ff; font-size: 16px; font-weight: bold;")
        middle_layout.addWidget(self.detail_title)

        middle_layout.addWidget(QLabel("瞬时失效概率预测 (Failure Rate):"))
        self.fail_progress = QProgressBar()
        self.fail_progress.setRange(0, 100)
        self.fail_progress.setValue(0)
        self.fail_progress.setStyleSheet("""
            QProgressBar { background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }
            QProgressBar::chunk { background: #10b981; border-radius: 4px; }
        """)
        middle_layout.addWidget(self.fail_progress)

        # 参数调整表单
        form = QFormLayout()
        self.stress_slider = QSlider(Qt.Orientation.Horizontal)
        self.stress_slider.setRange(10, 30);
        self.stress_slider.setValue(11)  # 1.0x - 3.0x
        self.stress_slider.valueChanged.connect(self.run_weibull_computation)
        self.stress_lbl = QLabel("1.1x")
        self.stress_lbl.setStyleSheet("color: #00d2ff;")

        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(15, 65);
        self.temp_slider.setValue(35)  # 15C - 65C
        self.temp_slider.valueChanged.connect(self.run_weibull_computation)
        self.temp_lbl = QLabel("35 ℃")
        self.temp_lbl.setStyleSheet("color: #00d2ff;")

        form.addRow("实时环境应力系数:", self.stress_slider)
        form.addRow("当前应力显示:", self.stress_lbl)
        form.addRow("工作机柜内部温度:", self.temp_slider)
        form.addRow("当前温度显示:", self.temp_lbl)
        middle_layout.addLayout(form)
        middle_layout.addStretch()

        # --- 右栏：计算逻辑控制台 ---
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 6px; color: #10b981; font-family: 'Consolas'; font-size: 11px; }
        """)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.middle_panel)
        splitter.addWidget(self.console)
        splitter.setSizes([450, 250, 180])

        self.layout.addWidget(splitter)

    def load_sample_database(self):
        self.db = {
            "DEV-2001": {"name": "G105立交卡口A球机", "hours": 4200, "maint": 1, "life": 8000, "stress": 1.2,
                         "temp": 35},
            "DEV-2002": {"name": "解放路十字信号灯B", "hours": 8500, "maint": 5, "life": 12000, "stress": 1.0,
                         "temp": 38},
            "DEV-2003": {"name": "机场大道地下道传感器", "hours": 1200, "maint": 0, "life": 6000, "stress": 1.5,
                         "temp": 42}
        }
        self.populate_ledger_table()

    def populate_ledger_table(self):
        self.table.setRowCount(0)
        for row, (id, info) in enumerate(self.db.items()):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(info["name"])))
            self.table.setItem(row, 2, QTableWidgetItem(str(info["hours"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(info["maint"])))
            self.table.setItem(row, 4, QTableWidgetItem(str(info["life"])))

    def on_asset_clicked(self, index):
        row = index.row()
        self.active_asset_id = self.table.item(row, 0).text()
        info = self.db.get(self.active_asset_id)
        if info:
            self.stress_slider.setValue(int(info["stress"] * 10))
            self.temp_slider.setValue(int(info["temp"]))
            self.run_weibull_computation()

    def run_weibull_computation(self):
        """核心交互：实时解算威布尔浴盆模型"""
        if not self.active_asset_id:
            return

        info = self.db[self.active_asset_id]
        current_stress = self.stress_slider.value() / 10.0
        current_temp = self.temp_slider.value()

        self.stress_lbl.setText(f"{current_stress}x")
        self.temp_lbl.setText(f"{current_temp} ℃")

        # 运行数学引擎
        prob, mtbf, phase, color = WeibullReliabilityEngine.predict_failure_metrics(
            info["hours"], current_stress, info["maint"], current_temp
        )

        # 动态反馈UI渲染
        self.detail_title.setText(info["name"])
        self.fail_progress.setValue(int(prob))
        self.fail_progress.setStyleSheet(f"""
            QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}
            QProgressBar {{ background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }}
        """)

        # 写入右侧终端
        self.console.clear()
        self.console.addItem(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 载入资产: {self.active_asset_id}")
        self.console.addItem(f"运行阶段: {phase}")
        self.console.addItem(f"----------------------------------------")
        self.console.addItem(f"瞬时失效率 F(t): {prob}%")
        self.console.addItem(f"预测系统 MTBF: {mtbf} h")
        self.console.addItem(f"----------------------------------------")
        if prob > 50.0:
            self.console.addItem("警告: 设备损耗极大，故障一触即发，应即刻派发工单！")
        else:
            self.console.addItem("诊断结论: 可靠性在控。")

    def simulate_stress_growth(self):
        """模拟在恶劣天气或车流暴增下，全路网设备应力系数急剧上升"""
        for k in self.db.keys():
            self.db[k]["stress"] = round(self.db[k]["stress"] * 1.3, 1)
            self.db[k]["temp"] += 5
        self.populate_ledger_table()
        self.console.clear()
        self.console.addItem("警告：全路段遭遇突发恶劣条件，设备应力和温度急剧上升！请重新评估各设备故障率。")

    def filter_ledger(self):
        query = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item:
                self.table.setRowHidden(row, query not in item.text().lower())

    def refresh_data(self):
        pass

    def save_changes(self):
        pass