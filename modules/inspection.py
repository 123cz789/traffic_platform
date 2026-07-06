# modules/inspection.py
import datetime
import json
import os
import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QFormLayout,
                             QSlider, QPushButton, QProgressBar, QMessageBox,
                             QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from core.base_module import BaseModule


# --- 1. 核心工程学算法类 ---
class StructuralSafetyEngine:
    """交通设施结构安全度多因子退化模型 (DSSI)"""

    @staticmethod
    def calculate_dssi(crack_width, tilt_angle, environment_stress, carbonation_depth):
        """
        DSSI = 100 - (裂缝系数 * 12 + 倾斜系数 * 8 + 碳化系数 * 1.5) * 环境因子
        """
        try:
            crack_factor = float(crack_width) * 12.0
            tilt_factor = float(tilt_angle) * 8.0
            carbon_factor = float(carbonation_depth) * 1.5
            total_damage = (crack_factor + tilt_factor + carbon_factor) * float(environment_stress)
            dssi = max(0.0, min(100.0, 100.0 - total_damage))
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
        self.dssi = 100.0
        self.advice_text = "正常"
        self.db = {}
        self.init_ui()
        self.load_inspection_tasks()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        header = QLabel("智能道路设施结构安全诊断终端")
        header.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        self.layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左侧：主任务流 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 15, 0)
        left_layout.setSpacing(15)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["工单号", "巡检部件", "结构状态", "复核时间"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background: #111827; gridline-color: #1f2937; color: #fff; border-radius: 6px; }
        """)
        self.table.clicked.connect(self.on_row_selected)

        left_layout.addWidget(QLabel("待复核高维缺陷队列:"))
        left_layout.addWidget(self.table, stretch=3)

        # AI 视觉特征分析仪
        self.ai_scan_frame = QFrame()
        self.ai_scan_frame.setObjectName("aiScanFrame")
        self.ai_scan_frame.setStyleSheet("""
            QFrame#aiScanFrame { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; padding: 15px; }
            QLabel { color: #64748b; font-size: 11px; font-family: 'Microsoft YaHei'; }
            QLabel#aiTitle { color: #00d2ff; font-weight: bold; font-size: 13px; }
        """)
        ai_layout = QVBoxLayout(self.ai_scan_frame)
        ai_title = QLabel("AI 视觉识别裂缝边缘检测仪")
        ai_title.setObjectName("aiTitle")

        self.ai_metric_lbl = QLabel(
            "边缘重叠匹配度: 0.0%\n"
            "裂缝几何特征提取: 未载入数据\n"
            "结构位移特征点对: 0对"
        )

        self.ai_progress = QProgressBar()
        self.ai_progress.setRange(0, 100)
        self.ai_progress.setValue(0)
        self.ai_progress.setFormat("AI置信度: -- %")
        self.ai_progress.setStyleSheet("""
            QProgressBar { background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 18px; font-size: 10px; }
            QProgressBar::chunk { background: #10b981; border-radius: 4px; }
        """)

        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(self.ai_metric_lbl)
        ai_layout.addWidget(self.ai_progress)
        left_layout.addWidget(self.ai_scan_frame, stretch=2)

        # --- 右侧：控制台 ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(25, 20, 25, 20)

        top_bar = QHBoxLayout()
        self.detail_title = QLabel("专家诊断分析")
        self.detail_title.setStyleSheet("color: #00d2ff; font-size: 16px; font-weight: bold;")
        self.interlock_status_lbl = QLabel("● 安全联锁: 正常")
        self.interlock_status_lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 12px;")
        top_bar.addWidget(self.detail_title)
        top_bar.addStretch()
        top_bar.addWidget(self.interlock_status_lbl)
        right_layout.addLayout(top_bar)

        right_layout.addWidget(QLabel("计算所得结构安全度指数 (DSSI):"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }
            QProgressBar::chunk { background: #10b981; border-radius: 4px; }
        """)
        right_layout.addWidget(self.progress_bar)

        self.interlock_lbl = QLabel("设备物理应力限制：[ 安全合规 ]")
        self.interlock_lbl.setStyleSheet(
            "color: #10b981; font-weight: bold; font-family: 'Microsoft YaHei'; font-size: 11px;")
        right_layout.addWidget(self.interlock_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #1f2937; height: 1px; border: none;")
        right_layout.addWidget(sep)

        right_layout.addWidget(QLabel("实地物理数据校准 (DSSI 多维数学预测):"))
        form = QFormLayout()

        self.crack_slider = QSlider(Qt.Orientation.Horizontal)
        self.crack_slider.setRange(0, 50)
        self.crack_slider.setValue(12)
        self.crack_slider.valueChanged.connect(self.run_realtime_simulation)
        self.crack_lbl = QLabel("1.2 mm")
        self.crack_lbl.setStyleSheet("color: #00d2ff;")

        self.tilt_slider = QSlider(Qt.Orientation.Horizontal)
        self.tilt_slider.setRange(0, 15)
        self.tilt_slider.setValue(2)
        self.tilt_slider.valueChanged.connect(self.run_realtime_simulation)
        self.tilt_lbl = QLabel("2.0 度")
        self.tilt_lbl.setStyleSheet("color: #00d2ff;")

        self.carbon_slider = QSlider(Qt.Orientation.Horizontal)
        self.carbon_slider.setRange(0, 30)
        self.carbon_slider.setValue(4)
        self.carbon_slider.valueChanged.connect(self.run_realtime_simulation)
        self.carbon_lbl = QLabel("4.0 mm")
        self.carbon_lbl.setStyleSheet("color: #00d2ff;")

        self.stress_slider = QSlider(Qt.Orientation.Horizontal)
        self.stress_slider.setRange(10, 30)
        self.stress_slider.setValue(13)
        self.stress_slider.valueChanged.connect(self.run_realtime_simulation)
        self.stress_lbl = QLabel("1.3 x")
        self.stress_lbl.setStyleSheet("color: #00d2ff;")

        form.addRow("结构裂缝宽度 (Max 3.0mm):", self.crack_slider)
        form.addRow("实时显示值:", self.crack_lbl)
        form.addRow("桥墩整体倾斜 (Max 8.0°):", self.tilt_slider)
        form.addRow("实时显示值:", self.tilt_lbl)
        form.addRow("骨料碳化深度:", self.carbon_slider)
        form.addRow("实时显示值:", self.carbon_lbl)
        form.addRow("荷载应力系数:", self.stress_slider)
        form.addRow("实时显示值:", self.stress_lbl)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("力学矩阵迭代演算终端 (仿真流):"))
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 4px; color: #10b981; font-family: 'Consolas'; font-size: 11px; }
        """)
        # 修正点：使用原生的 QSizePolicy 属性，消除 type object 'QTableWidget' has no attribute 'SizePolicy' 崩溃
        self.console.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.console)

        self.override_lock_cb = QCheckBox("解锁极端数据保护锁 (需专家特级密钥)")
        self.override_lock_cb.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.override_lock_cb.stateChanged.connect(self.run_realtime_simulation)
        right_layout.addWidget(self.override_lock_cb)

        right_layout.addStretch()

        self.save_btn = QPushButton("提交专家评审报告 并 归档")
        self.save_btn.setStyleSheet("""
            QPushButton { background: #10b981; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #059669; }
            QPushButton:disabled { background: #1f2937; color: #4b5563; border: 1px solid #374151; }
        """)
        self.save_btn.clicked.connect(self.commit_report)
        right_layout.addWidget(self.save_btn)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([500, 420])
        self.layout.addWidget(splitter)

    def load_inspection_tasks(self):
        self.db = {
            "TSK-4001": {"name": "G105立交桥2号墩", "crack": 1.2, "tilt": 2.0, "carbon": 4.0, "stress": 1.3},
            "TSK-4002": {"name": "滨江隧道明挖段侧墙", "crack": 4.2, "tilt": 8.0, "carbon": 12.0, "stress": 1.5},
            "TSK-4003": {"name": "迎宾大道高架跨线悬臂", "crack": 0.4, "tilt": 0.0, "carbon": 1.0, "stress": 1.0}
        }
        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        for row, (id, info) in enumerate(self.db.items()):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(id))
            self.table.setItem(row, 1, QTableWidgetItem(info["name"]))

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
            self.crack_slider.setValue(int(info["crack"] * 10))
            self.tilt_slider.setValue(int(info["tilt"]))
            self.carbon_slider.setValue(int(info["carbon"]))
            self.stress_slider.setValue(int(info["stress"] * 10))
            self.run_realtime_simulation()

    def run_realtime_simulation(self):
        if not self.active_asset_id:
            return

        info = self.db[self.active_asset_id]
        current_crack = self.crack_slider.value() / 10.0
        current_tilt = self.tilt_slider.value()
        current_carbon = float(self.carbon_slider.value())
        current_stress = self.stress_slider.value() / 10.0

        self.crack_lbl.setText(f"{current_crack:.1f} mm")
        self.tilt_lbl.setText(f"{current_tilt:.1f} 度")
        self.stress_lbl.setText(f"{current_stress:.1f}x")

        self.dssi, self.advice_text, color = StructuralSafetyEngine.calculate_dssi(
            current_crack, current_tilt, current_stress, current_carbon
        )

        is_locked = (current_crack > 3.0 or current_tilt > 8)
        override_unlocked = self.override_lock_cb.isChecked()

        if is_locked:
            self.interlock_status_lbl.setText("● 安全联锁保护: 已阻断")
            self.interlock_status_lbl.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 12px;")
            self.interlock_lbl.setText("设备物理应力限制：[ 警告：参数严重超限！ ]")
            self.interlock_lbl.setStyleSheet("color: #ef4444; font-weight: bold;")
            if not override_unlocked:
                self.save_btn.setEnabled(False)
                self.save_btn.setText("提交已锁死 (请开启专家解锁)")
            else:
                self.save_btn.setEnabled(True)
                self.save_btn.setText("专家特许授权提交")
        else:
            self.interlock_status_lbl.setText("● 安全联锁保护: 正常")
            self.interlock_status_lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 12px;")
            self.interlock_lbl.setText("设备物理应力限制：[ 安全合规 ]")
            self.interlock_lbl.setStyleSheet("color: #10b981; font-weight: bold;")
            self.save_btn.setEnabled(True)
            self.save_btn.setText("提交专家评审报告 并 归档")

        self.progress_bar.setValue(int(self.dssi))
        self.progress_bar.setStyleSheet(f"""
            QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}
            QProgressBar {{ background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }}
        """)

        confidence = int(max(30, self.dssi + random.randint(-5, 5)))
        self.ai_progress.setValue(confidence)
        self.ai_progress.setFormat(f"AI置信度评级: {confidence}%")
        self.ai_metric_lbl.setText(
            f"边缘重叠匹配度: {round(max(40, self.dssi * 0.95), 1)}%\n"
            f"裂缝几何特征提取: [ 自动标定 {current_crack}mm ]\n"
            f"结构位移特征点对: {int((15 - current_tilt) * 4)} 对"
        )

        self.console.clear()
        self.console.addItem(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 载入 DSSI 损伤分析矩阵...")
        self.console.addItem(f"应力阻泥: {current_stress}x | 碳化损伤: {current_carbon}mm")
        self.console.addItem(f"----------------------------------------")
        self.console.addItem(f"实时安全评分: {self.dssi} / 100")
        self.console.addItem(f"力学损伤开销: {round(100 - self.dssi, 1)} pts")
        if is_locked:
            self.console.addItem(f"⚠️ [警告] 数据突破 3.0mm 安全红线！已锁死通道。")
        self.console.scrollToBottom()

    def commit_report(self):
        if not self.active_asset_id:
            QMessageBox.warning(self, "警报", "未选择任何需要评审的资产！")
            return

        info = self.db[self.active_asset_id]
        current_crack = self.crack_slider.value() / 10.0
        current_tilt = self.tilt_slider.value()

        doc_id = f"ARC-{random.randint(700, 809)}"
        title = f"智能巡检诊断报告_{self.active_asset_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M')}.doc"
        file_size = round(random.uniform(2.1, 5.8), 1)
        sec_level = 5 if self.dssi < 40 else 2

        report_text = (
            f"【智能交通设施结构安全巡检复核报告】\n"
            f"复核上报时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"巡检对象名称: {info['name']} (流转ID: {self.active_asset_id})\n"
            f"结构实测数据:\n"
            f" ├ 现场测定裂缝宽度: {current_crack} mm\n"
            f" └ 现场测定倾斜角度: {current_tilt} 度\n"
            f"模型诊断健康指数: {self.dssi} / 100 分\n"
            f"专家终审决策建议: {self.advice_text}\n"
            f"上报权限签发: admin (系统特级管理员授权)"
        )

        db_path = "data/archives_db.json"
        db = {}

        if os.path.exists(db_path):
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    db = json.load(f)
            except Exception:
                db = {}

        db[doc_id] = {
            "title": title,
            "cat": "竣工验收报告",
            "sec": sec_level,
            "weight": 9.0,
            "size": file_size,
            "detail_text": report_text
        }

        os.makedirs("data", exist_ok=True)
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)

        QMessageBox.information(
            self,
            "专家决策确认",
            f"结构判定报告已成功上报并同步至设施管理档案库！\n\n生成文献编号: {doc_id}\n类别：竣工验收报告"
        )

    def refresh_data(self):
        pass

    def save_changes(self):
        pass