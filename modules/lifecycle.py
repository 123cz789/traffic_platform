# modules/lifecycle.py
import datetime
import math
import os
import json
import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QFormLayout, QComboBox,
                             QSlider, QListWidget, QPushButton, QProgressBar, QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt
from core.base_module import BaseModule


class LifetimeSimulationEngine:
    @staticmethod
    def simulate_degradation(age, design_life, traffic_amplitude, material_damping, corrosion_index):
        try:
            cyclic_stress = math.pow(float(traffic_amplitude), 1.3)
            accumulated_wear = float(age) * 0.015 * float(material_damping) * cyclic_stress
            corrosion_modifier = 1.0 + (float(corrosion_index) * 0.05)
            effective_wear = accumulated_wear * corrosion_modifier

            reliability = math.exp(-math.pow(effective_wear / 1.5, 1.8))
            remaining_life = float(design_life) * reliability
            remaining_life = max(0.0, min(float(design_life), remaining_life))
            crack_expansion = min(100.0, (effective_wear * 100) / 1.2)

            return round(remaining_life, 1), round(effective_wear * 100, 1), round(crack_expansion, 1)
        except Exception:
            return 0.0, 0.0, 0.0


class Lifecycle(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rul = 0.0
        self.wear_rate = 0.0
        self.fatigue_threshold = 0.0
        self.init_ui()
        self.run_realtime_simulation()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        header = QLabel("设施全生命周期退化模拟与疲劳预测终端")
        header.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        self.layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左侧：物理参数面板 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 15, 0)
        left_layout.setSpacing(15)

        slider_frame = QFrame()
        slider_frame.setObjectName("sliderFrame")
        slider_frame.setStyleSheet(
            "QFrame#sliderFrame { background: #111827; border-radius: 8px; border: 1px solid #1f2937; padding: 15px; }")
        slider_layout = QVBoxLayout(slider_frame)

        slider_layout.addWidget(QLabel("物理及运营应力参数矩阵输入:"))
        form = QFormLayout()

        self.age_slider = QSlider(Qt.Orientation.Horizontal)
        self.age_slider.setRange(0, 30);
        self.age_slider.setValue(6)
        self.age_slider.valueChanged.connect(self.run_realtime_simulation)
        self.age_lbl = QLabel("6 年")
        self.age_lbl.setStyleSheet("color: #00d2ff;")

        self.design_slider = QSlider(Qt.Orientation.Horizontal)
        self.design_slider.setRange(15, 100);
        self.design_slider.setValue(25)
        self.design_slider.valueChanged.connect(self.run_realtime_simulation)
        self.design_lbl = QLabel("25 年")
        self.design_lbl.setStyleSheet("color: #00d2ff;")

        self.traffic_slider = QSlider(Qt.Orientation.Horizontal)
        self.traffic_slider.setRange(10, 300);
        self.traffic_slider.setValue(115)
        self.traffic_slider.valueChanged.connect(self.run_realtime_simulation)
        self.traffic_lbl = QLabel("1.15x (正常负荷)")
        self.traffic_lbl.setStyleSheet("color: #00d2ff;")

        self.corrosion_slider = QSlider(Qt.Orientation.Horizontal)
        self.corrosion_slider.setRange(0, 10)
        self.corrosion_slider.setValue(2)
        self.corrosion_slider.valueChanged.connect(self.run_realtime_simulation)
        self.corrosion_lbl = QLabel("0.2x (轻度盐雾)")
        self.corrosion_lbl.setStyleSheet("color: #00d2ff;")

        self.material_combo = QComboBox()
        self.material_combo.addItems(
            ["高性能硅酸盐混凝土 [阻尼: 0.8x]", "标准合金结构钢 [阻尼: 1.1x]", "碳纤维复合补强材料 [阻尼: 0.5x]"])
        self.material_combo.currentIndexChanged.connect(self.run_realtime_simulation)

        form.addRow("设施已服役役龄:", self.age_slider)
        form.addRow("实时显示值:", self.age_lbl)
        form.addRow("标准设计使用年限:", self.design_slider)
        form.addRow("实时显示值:", self.design_lbl)
        form.addRow("交通流剪切疲劳幅值:", self.traffic_slider)
        form.addRow("实时显示值:", self.traffic_lbl)
        form.addRow("电化学侵蚀系数:", self.corrosion_slider)
        form.addRow("环境腐蚀值:", self.corrosion_lbl)
        form.addRow("基础骨料材质工艺:", self.material_combo)
        slider_layout.addLayout(form)

        left_layout.addWidget(slider_frame, stretch=4)

        # 左下：数字孪生应变传感器分析舱
        self.sensor_frame = QFrame()
        self.sensor_frame.setObjectName("sensorFrame")
        self.sensor_frame.setStyleSheet("""
            QFrame#sensorFrame { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; padding: 15px; }
            QLabel { color: #64748b; font-size: 11px; font-family: 'Microsoft YaHei'; }
            QLabel#sensorTitle { color: #00d2ff; font-weight: bold; font-size: 12px; }
        """)
        sensor_layout = QVBoxLayout(self.sensor_frame)
        sensor_title = QLabel("数字孪生应变传感器监测舱")
        sensor_title.setObjectName("sensorTitle")

        self.sensor_metrics = QLabel(
            "晶格微观拉应变: 142.5 με\n"
            "Paris 裂纹增长级数: dN/da = 1.25e-6\n"
            "构件局部微裂缝状态: [ 正常 ]"
        )
        self.sensor_progress = QProgressBar()
        self.sensor_progress.setRange(0, 100)
        self.sensor_progress.setValue(0)
        self.sensor_progress.setFormat("结构位移应变冗余度: -- %")
        self.sensor_progress.setStyleSheet("""
            QProgressBar { background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 18px; font-size: 10px; }
            QProgressBar::chunk { background: #0ea5e9; border-radius: 4px; }
        """)

        sensor_layout.addWidget(sensor_title)
        sensor_layout.addWidget(self.sensor_metrics)
        sensor_layout.addWidget(self.sensor_progress)
        left_layout.addWidget(self.sensor_frame, stretch=2)

        # --- 右侧：寿命分析仪表看板 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(15, 0, 0, 0)
        right_layout.setSpacing(10)

        right_layout.addWidget(QLabel("全役期仿真分析指标预测:"))

        self.wear_lbl = QLabel("结构总体累积耗损率: 0%")
        right_layout.addWidget(self.wear_lbl)
        self.wear_bar = QProgressBar()
        self.wear_bar.setStyleSheet("QProgressBar::chunk { background: #f59e0b; }")
        right_layout.addWidget(self.wear_bar)

        self.fatigue_lbl = QLabel("Paris-Erdogan 疲劳临界阈值: 0%")
        right_layout.addWidget(self.fatigue_lbl)
        self.fatigue_bar = QProgressBar()
        self.fatigue_bar.setStyleSheet("QProgressBar::chunk { background: #ef4444; }")
        right_layout.addWidget(self.fatigue_bar)

        right_layout.addSpacing(15)
        right_layout.addWidget(QLabel("寿命退化实时仿真分析终端:"))
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 4px; color: #00d2ff; font-family: 'Consolas'; font-size: 12px; }
        """)
        # 修正点：使用原生的 QSizePolicy 属性，彻底消除 type object 'QTableWidget' has no attribute 'SizePolicy' 崩溃
        self.console.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.console)

        self.simulate_btn = QPushButton("生成全周期资产寿命演变白皮书 并 归档")
        self.simulate_btn.setStyleSheet("""
            QPushButton { background: #00d2ff; color: #000; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #00b4d8; }
        """)
        self.simulate_btn.clicked.connect(self.generate_and_archive_whitepaper)
        right_layout.addWidget(self.simulate_btn)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([450, 470])
        self.layout.addWidget(splitter)

    def run_realtime_simulation(self):
        current_age = self.age_slider.value()
        design_life = self.design_slider.value()
        traffic_growth = self.traffic_slider.value() / 100.0
        corrosion_idx = self.corrosion_slider.value() / 10.0

        mat_idx = self.material_combo.currentIndex()
        material_factor = 0.8 if mat_idx == 0 else (1.1 if mat_idx == 1 else 0.5)

        self.age_lbl.setText(f"{current_age} 年")
        self.design_lbl.setText(f"{design_life} 年")
        self.traffic_lbl.setText(f"{traffic_growth:.2f}x" + (" (重载过载)" if traffic_growth > 1.8 else " (正常负荷)"))
        self.corrosion_lbl.setText(
            f"{corrosion_idx:.1f}x" + (" (严重酸雨腐蚀)" if corrosion_idx > 0.6 else " (轻度盐雾)"))

        self.rul, self.wear_rate, self.fatigue_threshold = LifetimeSimulationEngine.simulate_degradation(
            current_age, design_life, traffic_growth, material_factor, corrosion_idx
        )

        self.wear_lbl.setText(f"结构总体累积耗损率: {self.wear_rate}%")
        self.wear_bar.setValue(int(min(100, self.wear_rate)))
        self.fatigue_lbl.setText(f"Paris-Erdogan 疲劳临界阈值: {self.fatigue_threshold}%")
        self.fatigue_bar.setValue(int(min(100, self.fatigue_threshold)))

        strain_margin = int(max(15, 100 - self.wear_rate))
        self.sensor_progress.setValue(strain_margin)
        self.sensor_progress.setFormat(f"结构位应变冗余度: {strain_margin}%")
        self.sensor_metrics.setText(
            f"晶格微观拉应变: {round(self.wear_rate * 4.2, 1)} με\n"
            f"Paris 裂纹增长级数: dN/da = {round(self.fatigue_threshold * 0.12, 2)}e-6\n"
            f"构件局部微裂缝状态: [ {'⚠️ 处于疲劳耗损期' if self.rul < 5 else '正常运转'} ]"
        )

        self.console.clear()
        self.console.addItem(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 载入 Paris 裂纹扩展微分方程...")
        self.console.addItem(f"材料阻尼矩阵: λ={material_factor} | 疲劳循环应力幅: {traffic_growth:.2f}")
        self.console.addItem(f"--------------------------------------------")
        self.console.addItem(f"剩余有用寿命 (RUL) 预测结果: {self.rul} 年")
        self.console.addItem(f"--------------------------------------------")

    def generate_and_archive_whitepaper(self):
        if self.age_slider.value() > self.design_slider.value():
            QMessageBox.warning(self, "仿真失败", "严重错误：已服役年限不可大于设计寿命极限！")
            return

        doc_id = f"ARC-{random.randint(810, 999)}"
        title = f"G105立交桥安全预测白皮书_{datetime.datetime.now().strftime('%Y%m%d%H%M')}.doc"
        file_size = round(random.uniform(5.5, 18.2), 1)
        sec_level = 4 if self.fatigue_threshold > 50 else 2

        report_text = (
                f"【交通设施全役期寿命预测报告】\n"
                f"报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"分析对象: G105立交桥主承重系统\n"
                f"已服役役龄: {self.age_slider.value()} 年\n"
                f"设计寿命极限: {self.design_slider.value()} 年\n"
                f"交通载荷放大应力系数: {self.traffic_slider.value() / 100.0}x\n"
                f"----------------------------------------\n"
                f"【算法引擎预测数值】\n"
                f"剩余有用役龄预测 (RUL): {self.rul} 年\n"
                f"疲劳裂纹萌生率 (Paris Law): {self.fatigue_threshold}%\n"
                f"累计损耗风险指数: {self.wear_rate}%\n"
                f"建议策略: " + (
                    "[红色警告] 结构逼近断裂临界点，即刻限制交通并调遣重装维护。" if self.rul < 5.0 else "[绿色受控] 结构力学稳健。")
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
            "weight": 8.5,
            "size": file_size,
            "detail_text": report_text
        }

        os.makedirs("data", exist_ok=True)
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)

        QMessageBox.information(self, "系统决策引擎",
                                f"寿命衰退仿真分析白皮书生成成功！\n\n已成功同步归档至文献档案库。\n归档流水号: {doc_id}")

    def refresh_data(self):
        pass

    def save_changes(self):
        pass