# modules/emergency.py
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QFormLayout, QComboBox,
                             QSlider, QListWidget, QPushButton, QMessageBox, QGridLayout)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QBrush
from core.base_module import BaseModule


# --- 1. 核心算法层：应急预案决策状态机与资源配置内核 ---
class EmergencyResponseEngine:
    """
    应急处置状态机 (Finite State Machine) 与联勤开销估算引擎
    """

    def __init__(self):
        # 预案5大流转阶段定义
        self.stages = [
            {"code": 0, "name": "待机监控", "color": "#4b5563"},
            {"code": 1, "name": "警报核实", "color": "#f59e0b"},
            {"code": 2, "name": "资源派遣", "color": "#00d2ff"},
            {"code": 3, "name": "协同管制", "color": "#f97316"},
            {"code": 4, "name": "闭环恢复", "color": "#10b981"}
        ]
        # 联勤队伍基本数据库：距离(km)，能力系数(1-5)
        self.units = {
            "救援一中队 (重型清障)": {"dist": 3.5, "cap": 5},
            "路产巡查班 (前哨侦察)": {"dist": 1.2, "cap": 2},
            "联勤交警组 (秩序管制)": {"dist": 4.8, "cap": 4}
        }

    def calculate_dispatch_cost(self, incident_severity, unit_name):
        """
        核心物理算法：
        分配开销 = (中队距离 * 事故严重级系数) / 中队救护能力系数
        开销越低，代表该中队越适合被派遣。
        """
        unit = self.units.get(unit_name)
        if not unit:
            return 999.0
        try:
            raw_cost = (unit["dist"] * float(incident_severity)) / unit["cap"]
            return round(raw_cost, 2)
        except ZeroDivisionError:
            return 999.0


# --- 2. 应急处置主界面类 ---
class Emergency(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = EmergencyResponseEngine()
        self.current_state = 0  # 初始状态：待机监控
        self.state_widgets = []
        self.init_ui()

    def init_ui(self):
        # 纵向主框架
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # 模块大标题
        header = QLabel("智能路网突发事件协同处置与决策控制中控台")
        header.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        self.layout.addWidget(header)

        # --- 独特排版第一层：顶部横向 FSM 状态机步进指示器 ---
        self.top_flow_panel = QFrame()
        self.top_flow_panel.setObjectName("topFlow")
        self.top_flow_panel.setStyleSheet("""
            QFrame#topFlow { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }
        """)
        flow_layout = QHBoxLayout(self.top_flow_panel)
        flow_layout.setContentsMargins(15, 10, 15, 10)

        # 动态创建 5 个流转进度圆角小卡片
        self.state_widgets = []
        for i, stage in enumerate(self.engine.stages):
            card = QLabel(f" {i + 1}. {stage['name']} ")
            card.setFixedSize(110, 35)
            card.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card.setStyleSheet(f"""
                QLabel {{ 
                    background: #111827; color: #4b5563; border: 1px solid #374151; 
                    border-radius: 4px; font-weight: bold; font-size: 11px;
                }}
            """)
            flow_layout.addWidget(card)
            self.state_widgets.append(card)
            if i < 4:  # 加装箭头
                arrow = QLabel("➔")
                arrow.setStyleSheet("color: #1f2937; font-size: 14px;")
                flow_layout.addWidget(arrow)

        self.layout.addWidget(self.top_flow_panel)

        # 界面切分器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左下：突发事件人工仿真注入区 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 15, 0)

        self.inject_frame = QFrame()
        self.inject_frame.setObjectName("injectFrame")
        self.inject_frame.setStyleSheet(
            "QFrame#injectFrame { background: #111827; border: 1px solid #1f2937; border-radius: 8px; }")
        inject_layout = QVBoxLayout(self.inject_frame)
        inject_layout.setContentsMargins(20, 20, 20, 20)

        inject_layout.addWidget(QLabel("突发路况仿真与特级警报注入:"))

        form = QFormLayout()
        self.incident_combo = QComboBox()
        self.incident_combo.addItems(["桥隧相连段-严重多车追尾", "滨江隧道-三类违章火警", "高架桥墩-剪切应力破损告警"])
        self.incident_combo.currentIndexChanged.connect(self.on_incident_triggered)

        self.severity_slider = QSlider(Qt.Orientation.Horizontal)
        self.severity_slider.setRange(1, 5)  # 1-5 级严重度
        self.severity_slider.setValue(3)
        self.severity_slider.valueChanged.connect(self.on_incident_triggered)
        self.severity_lbl = QLabel("3级 (特大重度告警)")
        self.severity_lbl.setStyleSheet("color: #ef4444;")

        form.addRow("事故仿真特征源:", self.incident_combo)
        form.addRow("事故瞬时严重度:", self.severity_slider)
        form.addRow("实时危险指数评级:", self.severity_lbl)
        inject_layout.addLayout(form)
        inject_layout.addStretch()

        left_layout.addWidget(self.inject_frame)

        # --- 右下：FSM 控制决策台 ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(25, 25, 25, 25)

        right_layout.addWidget(QLabel("智能应急联合调度面板"))

        # 终端指令输出
        right_layout.addWidget(QLabel("状态机流转执行命令日志:"))
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 4px; color: #10b981; font-family: 'Consolas'; font-size: 11px; }
        """)
        right_layout.addWidget(self.console)

        # 状态推进按钮
        self.state_btn = QPushButton("确认警报: 强行切入下一流转阶段")
        self.state_btn.setStyleSheet("""
            QPushButton { background: #ef4444; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #dc2626; }
        """)
        self.state_btn.clicked.connect(self.trigger_fsm_transition)
        right_layout.addWidget(self.state_btn)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([450, 470])
        self.layout.addWidget(splitter)

        # 启动时高亮初始待机状态
        self.update_fsm_visuals()

    def on_incident_triggered(self):
        """核心交互：突发状态改变时重算中队派遣开销"""
        severity = self.severity_slider.value()
        self.severity_lbl.setText(f"{severity}级 " + ("(特级极高隐患)" if severity > 3 else "(中度事件)"))

        if self.current_state == 0:
            self.console.clear()
            self.console.addItem(
                f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [FSM: 待机监控] 传感器捕获脉冲信号...")
            self.console.addItem(f"模拟突发源: {self.incident_combo.currentText()}")
            self.console.addItem(f"----------------------------------------")

            # 计算推荐派遣的中队（开销最小者）
            best_unit = None
            best_cost = 999.0
            for name in self.engine.units.keys():
                cost = self.engine.calculate_dispatch_cost(severity, name)
                self.console.addItem(f"分析中队 -> {name} | 派遣开销评估: {cost} pts")
                if cost < best_cost:
                    best_cost = cost
                    best_unit = name
            self.console.addItem(f"----------------------------------------")
            self.console.addItem(f"决策建议: 优先派遣【{best_unit}】 (开销最优化值: {best_cost})")

    def trigger_fsm_transition(self):
        """核心状态机推进机制"""
        if self.current_state == 0:
            # 待机 -> 核实
            self.current_state = 1
            self.state_btn.setText("指派资源: 启动一键快速派遣")
            self.state_btn.setStyleSheet("background: #00d2ff; color: #000; font-weight: bold;")
        elif self.current_state == 1:
            # 核实 -> 派遣
            self.current_state = 2
            self.state_btn.setText("协同联勤: 开启路面交通管制")
            self.state_btn.setStyleSheet("background: #f97316; color: white; font-weight: bold;")
        elif self.current_state == 2:
            # 派遣 -> 管制
            self.current_state = 3
            self.state_btn.setText("恢复常态: 安全撤离闭环归档")
            self.state_btn.setStyleSheet("background: #10b981; color: white; font-weight: bold;")
        elif self.current_state == 3:
            # 管制 -> 闭环
            self.current_state = 4
            self.state_btn.setText("重置状态机: 进入下一监控周期")
            self.state_btn.setStyleSheet("background: #4b5563; color: white; font-weight: bold;")
        else:
            # 重置回待机
            self.current_state = 0
            self.state_btn.setText("确认警报: 强行切入下一流转阶段")
            self.state_btn.setStyleSheet("background: #ef4444; color: white; font-weight: bold;")

        # 同步更新顶部状态指示卡片的视觉效果
        self.update_fsm_visuals()

    def update_fsm_visuals(self):
        """根据当前状态，高亮状态机顶部卡片"""
        for i, card in enumerate(self.state_widgets):
            if i == self.current_state:
                # 高亮当前活跃节点，赋予所属等级的霓虹色
                color = self.engine.stages[i]["color"]
                card.setStyleSheet(f"""
                    QLabel {{ 
                        background: {color}; color: #000000; border: 1px solid {color}; 
                        border-radius: 4px; font-weight: 800; font-size: 11px;
                    }}
                """)
            else:
                # 暗色未激活状态
                card.setStyleSheet("""
                    QLabel { 
                        background: #111827; color: #4b5563; border: 1px solid #1f2937; 
                        border-radius: 4px; font-weight: bold; font-size: 11px;
                    }
                """)

        # 同步写入终端控制流
        now_time = datetime.datetime.now().strftime('%H:%M:%S')
        stage_name = self.engine.stages[self.current_state]["name"]
        self.console.addItem(f"[{now_time}] FSM 转换: 预案状态成功跃迁至 -> 【{stage_name}】")
        self.console.scrollToBottom()

    def refresh_data(self):
        pass

    def save_changes(self):
        pass