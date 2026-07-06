# modules/emergency.py
import datetime
import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QFormLayout, QComboBox,
                             QSlider, QListWidget, QPushButton, QProgressBar)
from PyQt6.QtCore import Qt
from core.base_module import BaseModule


# --- 1. 核心算法层：带动态避障功能的 3D Dijkstra 路径拓扑寻路引擎 ---
class DynamicAvoidanceDijkstraEngine:
    """
    智能路网动态规避避障 Dijkstra 寻路内核
    在拓扑图计算中，可实时将特定“火灾/泄露受灾节点”设为禁行节点(Prohibited Vertices)，
    自动重构并计算出一条绝对安全的第二最短路径。
    """

    def __init__(self):
        # 基础路网枢纽节点定义 (A:主枢纽, B:立交桥, C:隧道北, D:高架匝道, E:滨江路, F:货运港)
        self.nodes = ["A", "B", "C", "D", "E", "F"]

        # 初始路网拓扑权重图 (物理距离km)
        # 999.0 代表两点间无直接车道连通
        self.adjacency_matrix = {
            "A": {"B": 3.5, "C": 5.0, "D": 999.0, "E": 999.0, "F": 999.0},
            "B": {"A": 4.2, "C": 1.5, "D": 8.0, "E": 999.0, "F": 999.0},
            "C": {"A": 2.5, "B": 1.5, "D": 3.0, "E": 6.2},
            "D": {"B": 8.0, "C": 3.0, "A": 999.0, "E": 2.1},
            "E": {"C": 6.2, "D": 2.1, "A": 999.0, "B": 999.0}
        }

    def solve_safest_route(self, start, end, blocked_nodes):
        """
        核心寻路算法：
        在计算中屏蔽 blocked_nodes，实现动态规避绕行。
        """
        # 数据合法性基本校验
        if start not in self.nodes or end not in self.nodes:
            return None, 999.0, ["ERROR_CODE: 寻路首尾节点不属于当前物理图谱"]

        if start in blocked_nodes:
            return None, 999.0, [f"CRITICAL_ERROR: 起点 Node_{start} 自身处于极高危灾区，无法发送车辆！"]

        distances = {node: 999.0 for node in self.nodes}
        distances[start] = 0.0
        previous_nodes = {node: None for node in self.nodes}
        unvisited = list(self.nodes)
        log_steps = []

        log_steps.append(f"初始化拓扑导航。起始站: Node_{start} | 规避受灾禁行节点: {list(blocked_nodes)}")

        while unvisited:
            # 寻找当前未访问节点中距离最小的
            current_node = min(unvisited, key=lambda node: distances[node])
            unvisited.remove(current_node)

            # 如果当前节点已被标记为事故灾区，则强行跳过此节点的邻接边松弛，实现自动避障
            if current_node in blocked_nodes:
                log_steps.append(f"  ✕ [检测到禁行红区] Node_{current_node} 处于严重灾害中！强制闭锁此物理通道。")
                continue

            log_steps.append(
                f"正在松弛 Node_{current_node} 的邻接物理通路 (当前最优累积开销: {distances[current_node]} km)")

            if distances[current_node] == 999.0:
                break

            for neighbor, weight in self.adjacency_matrix[current_node].items():
                if weight == 999.0 or neighbor in blocked_nodes:
                    if neighbor in blocked_nodes:
                        log_steps.append(f"    └ 规避灾害弧 {current_node} -> {neighbor} (避障绕行中...)")
                    continue
                alternative_route = distances[current_node] + weight
                if alternative_route < distances[neighbor]:
                    old_dist = distances[neighbor]
                    distances[neighbor] = alternative_route
                    previous_nodes[neighbor] = current_node
                    log_steps.append(
                        f"    └ 缩短路损 {current_node}->{neighbor}: {old_dist}km -> {alternative_route}km")

        # 逆向生成最终最优解链条
        path = []
        current = end
        while current is not None:
            path.insert(0, current)
            current = previous_nodes[current]

        if distances[end] == 999.0:
            log_steps.append("寻路失败：路网已因灾害彻底锁死，无安全通道！")
            return None, 999.0, log_steps

        log_steps.append("Dijkstra 空间避障寻路计算完毕。")
        return path, round(distances[end], 2), log_steps


# --- 2. 突发事件灾害性指数 (DPSI) 评估算法 ---
class IncidentDecisionMatrix:
    """危险度多因子加权评估算法"""

    @staticmethod
    def evaluate_danger_level(temp, gas_ppm, spread_speed):
        """
        DPSI = (温度 * 0.4 + 气体浓度 * 0.1) * (1 + 扩散风速 * 0.1)
        """
        try:
            base_damage = (float(temp) * 0.4) + (float(gas_ppm) * 0.1)
            wind_modifier = 1.0 + (float(spread_speed) * 0.1)
            dpsi = base_damage * wind_modifier

            # 限制在 0 - 100 分
            dpsi = max(0.0, min(100.0, dpsi))

            if dpsi > 75.0:
                return round(dpsi, 1), "特级危险 (立即启动一类响应机制)", "#ef4444"
            elif dpsi > 45.0:
                return round(dpsi, 1), "重度隐患 (启动二类联动抢险)", "#f59e0b"
            return round(dpsi, 1), "可控偏离 (执行三类常态巡防)", "#10b981"
        except Exception:
            return 0.0, "计算异常", "#64748b"


# --- 3. 应急处置主界面 (三舱一廊高级物理排版) ---
class Emergency(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.router_engine = DynamicAvoidanceDijkstraEngine()
        self.fsm_state = 0  # 初始：0(空闲监控)
        self.active_blocked_nodes = set()  # 动态火灾避障禁行集
        self.current_state = 0

        # 有限状态机5大节点定义
        self.fsm_stages = [
            {"name": "待机监控", "color": "#4b5563"},
            {"name": "警报核实", "color": "#f59e0b"},
            {"name": "避障寻路", "color": "#00d2ff"},
            {"name": "资源派遣", "color": "#f97316"},
            {"name": "恢复归档", "color": "#10b981"}
        ]
        self.fsm_labels = []
        self.init_ui()

    def init_ui(self):
        # 纵向大排版
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # --- 独特排版第一层：顶部横向 FSM 状态机步进廊 ---
        self.top_flow_panel = QFrame()
        self.top_flow_panel.setObjectName("topFlow")
        self.top_flow_panel.setStyleSheet("""
            QFrame#topFlow { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }
        """)
        flow_layout = QHBoxLayout(self.top_flow_panel)
        flow_layout.setContentsMargins(20, 12, 20, 12)

        # 绘制5个高保真状态步进卡片
        self.fsm_labels = []
        for i, stage in enumerate(self.fsm_stages):
            card = QLabel(f" {i + 1}. {stage['name']} ")
            card.setFixedSize(115, 38)
            card.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card.setStyleSheet("""
                QLabel { 
                    background: #111827; color: #4b5563; border: 1px solid #374151; 
                    border-radius: 4px; font-weight: bold; font-size: 11px;
                }
            """)
            flow_layout.addWidget(card)
            self.fsm_labels.append(card)
            if i < 4:
                arrow = QLabel("➔")
                arrow.setStyleSheet("color: #1f2937; font-size: 14px;")
                flow_layout.addWidget(arrow)

        self.layout.addWidget(self.top_flow_panel)

        # --- 独特排版第二层：下部三舱协同室 (QSplitter 三栏分割) ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # 1. 左舱：突发事件遥测输入舱
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setStyleSheet(
            "QFrame#leftPanel { background: #111827; border: 1px solid #1f2937; border-radius: 8px; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)

        left_layout.addWidget(QLabel("物理传感器遥测特征输入 (人工模拟注入):"))

        form = QFormLayout()
        self.incident_type = QComboBox()
        self.incident_type.addItems(
            ["A 区立交桥 - 严重多车追尾", "C 区隧道南段 - 易燃货车火灾", "D 区高架匝道 - 地震应力断裂"])
        self.incident_type.currentIndexChanged.connect(self.on_telemetry_changed)

        # 火源温度滑块
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(20, 1000);
        self.temp_slider.setValue(45)
        self.temp_slider.valueChanged.connect(self.on_telemetry_changed)
        self.temp_lbl = QLabel("45 ℃")
        self.temp_lbl.setStyleSheet("color: #00d2ff;")

        # 有毒气体浓度
        self.gas_slider = QSlider(Qt.Orientation.Horizontal)
        self.gas_slider.setRange(0, 500);
        self.gas_slider.setValue(10)
        self.gas_slider.valueChanged.connect(self.on_telemetry_changed)
        self.gas_lbl = QLabel("10 ppm")
        self.gas_lbl.setStyleSheet("color: #00d2ff;")

        # 扩散风速
        self.wind_slider = QSlider(Qt.Orientation.Horizontal)
        self.wind_slider.setRange(0, 30);
        self.wind_slider.setValue(2)
        self.wind_slider.valueChanged.connect(self.on_telemetry_changed)
        self.wind_lbl = QLabel("2.0 m/s")
        self.wind_lbl.setStyleSheet("color: #00d2ff;")

        form.addRow("突发事件类型选择:", self.incident_type)
        form.addRow("事故核心温度:", self.temp_slider)
        form.addRow("当前读取温度:", self.temp_lbl)
        form.addRow("有毒气体浓度 (PPM):", self.gas_slider)
        form.addRow("气体浓度值:", self.gas_lbl)
        form.addRow("局部扩散风速:", self.wind_slider)
        form.addRow("当前风速值:", self.wind_lbl)
        left_layout.addLayout(form)
        left_layout.addStretch()

        # 一键注入警报按钮
        self.alarm_btn = QPushButton("触发系统特级警报信号")
        self.alarm_btn.setStyleSheet("""
            QPushButton { background: #ef4444; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #dc2626; }
        """)
        self.alarm_btn.clicked.connect(self.inject_emergency_alert)
        left_layout.addWidget(self.alarm_btn)

        # 2. 中舱：最优避障路径分析舱
        mid_panel = QFrame()
        mid_panel.setObjectName("midPanel")
        mid_panel.setStyleSheet(
            "QFrame#midPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        mid_layout = QVBoxLayout(mid_panel)
        mid_layout.setContentsMargins(20, 20, 20, 20)

        mid_layout.addWidget(QLabel("DPSI 危害性解算与避障寻路引擎:"))

        # 危害度进度条 (已引入 QProgressBar)
        self.danger_progress = QProgressBar()
        self.danger_progress.setRange(0, 100)
        self.danger_progress.setValue(0)
        self.danger_progress.setStyleSheet("""
            QProgressBar { background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }
            QProgressBar::chunk { background: #10b981; border-radius: 4px; }
        """)
        mid_layout.addWidget(self.danger_progress)

        self.danger_desc = QLabel("状态待机中。请注入警报信号开启寻路模型。")
        self.danger_desc.setWordWrap(True)
        self.danger_desc.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.6;")
        mid_layout.addWidget(self.danger_desc)

        # 寻路控制表单
        form_route = QFormLayout()
        self.start_node_combo = QComboBox()
        self.start_node_combo.addItems(["A (应急一号库)", "B (迎宾路中队)", "E (货运特勤组)"])
        self.start_node_combo.currentIndexChanged.connect(self.trigger_realtime_path_solving)

        self.end_node_combo = QComboBox()
        self.end_node_combo.addItems(["F (受灾终端 Node_F)", "D (桥隧终端 Node_D)"])
        self.end_node_combo.currentIndexChanged.connect(self.trigger_realtime_path_solving)

        form_route.addRow("救援源头节点 (Start):", self.start_node_combo)
        form_route.addRow("受灾目的节点 (End):", self.end_node_combo)
        mid_layout.addLayout(form_route)
        mid_layout.addStretch()

        # 3. 右舱：联勤指令控制台终端
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)

        right_layout.addWidget(QLabel("FSM 状态机流转控制终端 (时序数据输出):"))
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 6px; color: #10b981; font-family: 'Consolas'; font-size: 11px; }
        """)
        right_layout.addWidget(self.console)

        # 状态流转推进按钮
        self.fsm_btn = QPushButton("预案校准：强行突跃至下一阶段")
        self.fsm_btn.setStyleSheet("""
            QPushButton { background: #ef4444; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #dc2626; }
        """)
        self.fsm_btn.clicked.connect(self.advance_fsm_state)
        right_layout.addWidget(self.fsm_btn)

        splitter.addWidget(left_panel)
        splitter.addWidget(mid_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([280, 290, 280])

        self.layout.addWidget(splitter)

        # 初始化高亮
        self.update_fsm_visuals()

    def on_telemetry_changed(self):
        """核心交互：调整滑块实时计算危害指数并警告"""
        temp = self.temp_slider.value()
        gas = self.gas_slider.value()
        wind = self.wind_slider.value()

        # 更新滑动条Label文本
        self.temp_lbl.setText(f"{temp} ℃")
        self.gas_lbl.setText(f"{gas} ppm")
        self.wind_lbl.setText(f"{wind:.1f} m/s")

        # 调用多准则决策
        dpsi, desc, color = IncidentDecisionMatrix.evaluate_danger_level(temp, gas, wind)

        # 动态反馈UI渲染
        self.danger_progress.setValue(int(dpsi))
        self.danger_progress.setStyleSheet(f"""
            QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}
            QProgressBar {{ background: #1f2937; border-radius: 4px; text-align: center; color: #fff; font-weight: bold; height: 25px; }}
        """)

        self.danger_desc.setText(
            f"【DPSI 突发事件危害等级评估】\n"
            f"瞬时危险度评分: {dpsi}分\n"
            f"系统响应特征: {desc}\n\n"
            f"应急联动指示:\n"
            f" ├ 隧道排风系统：开启 3 级全频引风\n"
            f" └ 信息诱导情报：高亮闪烁红底警示"
        )

        self.active_blocked_nodes.clear()
        idx = self.incident_type.currentIndex()
        if idx == 0:
            self.active_blocked_nodes.add("A")  # 封锁 A 节点
        elif idx == 1:
            self.active_blocked_nodes.add("C")  # 封锁 C 核心受灾隧道
        else:
            self.active_blocked_nodes.add("D")  # 封锁 D 高架

        self.trigger_realtime_path_solving()

    def trigger_realtime_path_solving(self):
        """执行带有动态故障点避障功能的最优路径寻路"""
        if self.current_state < 2:  # 只有状态机流转到 “避障寻路” 阶段后，才启动寻路解算
            return

        start_char = self.start_node_combo.currentText()[0]
        end_char = self.end_node_combo.currentText()[0]

        path, distance, steps = self.router_engine.solve_safest_route(
            start_char, end_char, self.active_blocked_nodes
        )

        self.console.clear()
        self.console.addItem(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Dijkstra 动态规避避障解算:")
        self.console.addItem(f"当前避障禁用红区: {list(self.active_blocked_nodes)}")
        self.console.addItem(f"----------------------------------------")

        for step in steps:
            self.console.addItem(step)

        if path:
            self.console.addItem(f"----------------------------------------")
            self.console.addItem(f"规划安全避障路线: " + " -> ".join(path))
            self.console.addItem(f"安全路径物理距离: {distance:.2f} km")
            self.console.addItem(f"预计车队抵达时间 (ETA): {int(distance * 2.2)} 分钟")
        else:
            self.console.addItem(f"----------------------------------------")
            self.console.addItem("警告：全通路已受火灾严重损毁，无法安全通行！请调遣空中直升机编队。")

        self.console.scrollToBottom()

    def inject_emergency_alert(self):
        """人工手动注入特级故障"""
        self.fsm_state = 1  # 强行进入 1 (警报核实)
        self.update_fsm_visuals()
        self.temp_slider.setValue(680)  # 强行升温
        self.gas_slider.setValue(380)  # 强行释放有毒气体
        self.wind_slider.setValue(18)  # 强行模拟大风扩散
        self.on_telemetry_changed()

        self.console.addItem(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] ！！！警报中心人工注入特级灾害事件！！！")

    def advance_fsm_state(self):
        """FSM有限状态机状态平滑推进算法"""
        self.current_state = (self.current_state + 1) % len(self.fsm_stages)

        # 按钮样式状态响应变换
        if self.current_state == 0:
            self.fsm_btn.setText("预案校准：强行突跃至下一阶段")
            self.fsm_btn.setStyleSheet("background: #ef4444; color: white; font-weight: bold;")
        elif self.current_state == 1:
            self.fsm_btn.setText("核实无误：一键启动避障寻路")
            self.fsm_btn.setStyleSheet("background: #f59e0b; color: white; font-weight: bold;")
        elif self.current_state == 2:
            self.fsm_btn.setText("解算通过：启动应急资源派遣")
            self.fsm_btn.setStyleSheet("background: #00d2ff; color: #000; font-weight: bold;")
            self.trigger_realtime_path_solving()  # 自动开始避障路径规划
        elif self.current_state == 3:
            self.fsm_btn.setText("特勤就位：执行撤离与恢复")
            self.fsm_btn.setStyleSheet("background: #f97316; color: white; font-weight: bold;")
        elif self.current_state == 4:
            self.fsm_btn.setText("处置完毕：重置状态机监控")
            self.fsm_btn.setStyleSheet("background: #10b981; color: white; font-weight: bold;")

        self.update_fsm_visuals()

    def update_fsm_visuals(self):
        """更新顶部横向状态指示廊的颜色高亮"""
        for i, card in enumerate(self.fsm_labels):
            if i == self.current_state:
                color = self.fsm_stages[i]["color"]
                card.setStyleSheet(f"""
                    QLabel {{ 
                        background: {color}; color: #000000; border: 1px solid {color}; 
                        border-radius: 4px; font-weight: 800; font-size: 11px;
                    }}
                """)
            else:
                card.setStyleSheet("""
                    QLabel { 
                        background: #111827; color: #4b5563; border: 1px solid #1f2937; 
                        border-radius: 4px; font-weight: bold; font-size: 11px;
                    }
                """)

        now_time = datetime.datetime.now().strftime('%H:%M:%S')
        stage_name = self.fsm_stages[self.current_state]["name"]
        self.console.addItem(f"[{now_time}] FSM 跃迁: 预案状态成功跃迁至 -> 【{stage_name}】")
        self.console.scrollToBottom()

    def refresh_data(self):
        pass

    def save_changes(self):
        pass