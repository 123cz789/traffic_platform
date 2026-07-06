# modules/gis_map.py
import datetime
import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QFormLayout, QComboBox,
                             QSlider, QListWidget, QPushButton, QMessageBox, QGridLayout)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QBrush
from core.base_module import BaseModule


# --- 1. 核心算法层：拓扑图 Dijkstra 最短路径求解器 ---
class GisRoutingEngine:
    """
    空间地理网络拓扑求解引擎
    定义路网邻接矩阵，并使用 Dijkstra 算法求解任意两点间的最短物理路径。
    """

    def __init__(self):
        # 节点定义：A:立交桥, B:迎宾路, C:机场路, D:港口大桥, E:货运通道
        self.nodes = ["A", "B", "C", "D", "E"]

        # 邻接矩阵 (Adjacency Matrix)，存储节点间的物理距离(km)
        # 999.0 代表两点间无直接车道连通
        self.graph = {
            "A": {"B": 4.2, "C": 2.5, "D": 999.0, "E": 999.0},
            "B": {"A": 4.2, "C": 1.5, "D": 8.0, "E": 999.0},
            "C": {"A": 2.5, "B": 1.5, "D": 3.0, "E": 6.2},
            "D": {"B": 8.0, "C": 3.0, "A": 999.0, "E": 2.1},
            "E": {"C": 6.2, "D": 2.1, "A": 999.0, "B": 999.0}
        }

    def solve_dijkstra_with_steps(self, start, end):
        """标准 Dijkstra 最短路径算法，包含详细的中间松弛步骤日志"""
        if start not in self.nodes or end not in self.nodes:
            return None, 999.0, ["ERROR: 无效的目标拓扑节点"]

        distances = {node: 999.0 for node in self.nodes}
        distances[start] = 0.0
        previous_nodes = {node: None for node in self.nodes}
        unvisited = list(self.nodes)
        calculation_steps = []  # 记录算法迭代步骤

        calculation_steps.append(f"Dijkstra 初始化: 起始节点设置为 Node_{start}")

        while unvisited:
            # 寻找当前未访问节点中距离最小的
            current_node = min(unvisited, key=lambda node: distances[node])
            unvisited.remove(current_node)

            calculation_steps.append(f"选定松弛节点 Node_{current_node} (当前累积路径值: {distances[current_node]} km)")

            if distances[current_node] == 999.0:
                break

            for neighbor, weight in self.graph[current_node].items():
                if weight == 999.0:
                    continue
                alternative_route = distances[current_node] + weight
                if alternative_route < distances[neighbor]:
                    old_dist = distances[neighbor]
                    distances[neighbor] = alternative_route
                    previous_nodes[neighbor] = current_node
                    calculation_steps.append(
                        f"  └ 松弛邻接弧 {current_node}->{neighbor}: 距离由 {old_dist}km 缩短至 {alternative_route}km")

        # 逆向重构最优路径链条
        path = []
        current = end
        while current is not None:
            path.insert(0, current)
            current = previous_nodes[current]

        calculation_steps.append("路网最优拓扑树重构完成。")
        return path, round(distances[end], 2), calculation_steps


# --- 2. GIS 主页面控制台 ---
class GisMap(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = GisRoutingEngine()
        self.select_mode = "START"  # 起止点选择状态缓存
        self.node_btns = {}
        self.init_ui()

    def init_ui(self):
        # 纵向主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # 头部标题
        header = QLabel("数字孪生路网拓扑分析与最优路由导航中控台")
        header.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        self.layout.addWidget(header)

        # 左右双区切分
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左侧：数字孪生拓扑几何节点阵列 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 15, 0)

        # 空间网格框
        map_box = QFrame()
        map_box.setObjectName("mapBox")
        map_box.setStyleSheet("""
            QFrame#mapBox { 
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #090c15, stop:1 #06080e);
                border: 1px solid #1f2937; border-radius: 8px; 
            }
        """)
        grid_layout = QGridLayout(map_box)
        grid_layout.setSpacing(20)

        # 修复后的节点对照表：ID，显示名，几何行，几何列
        nodes_config = [
            ("DEV-A", "Node_A", "G105立交枢纽", 0, 0),
            ("DEV-B", "Node_B", "迎宾路交叉口", 0, 2),
            ("DEV-C", "Node_C", "机场大道收费站", 2, 0),
            ("DEV-D", "Node_D", "滨江隧道核心段", 2, 2)
        ]

        # 修复后的遍历与信号绑定机制，彻底消除语法解析错误
        for dev_id, node_code, display_name, row, col in nodes_config:
            btn = QPushButton(f"{display_name}\n({node_code})")
            btn.setFixedSize(160, 100)
            btn.setStyleSheet("""
                QPushButton { 
                    background: #111827; color: #94a3b8; border: 1px solid #374151; 
                    border-radius: 6px; font-weight: bold; font-size: 13px;
                }
                QPushButton:hover { border: 1px solid #00d2ff; color: #00d2ff; background: #0f172a; }
            """)

            # 使用默认参数绑定机制，解决 Python 闭包作用域混淆导致的未解析引用问题
            btn.clicked.connect(lambda checked, code=node_code: self.on_node_clicked(code))
            grid_layout.addWidget(btn, row, col, alignment=Qt.AlignmentFlag.AlignCenter)
            self.node_btns[dev_id] = btn

        left_layout.addWidget(QLabel("数字孪生路面拓扑空间节点矩阵 (点击交互选择起止点):"))
        left_layout.addWidget(map_box)

        # --- 右侧：Dijkstra 路径分析控制台 ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(25, 25, 25, 25)

        right_layout.addWidget(QLabel("地理路径规划控制中心"), alignment=Qt.AlignmentFlag.AlignTop)

        form = QFormLayout()
        self.start_combo = QComboBox()
        self.start_combo.addItems(["A (G105枢纽)", "B (迎宾路)", "C (机场路)", "D (港口大桥)", "E (货运通道)"])

        self.end_combo = QComboBox()
        self.end_combo.addItems(["E (货运通道)", "D (港口大桥)", "C (机场路)", "B (迎宾路)", "A (G105枢纽)"])

        # 阻泥系数滑动条
        self.stress_slider = QSlider(Qt.Orientation.Horizontal)
        self.stress_slider.setRange(10, 300)  # 1.0x - 3.0x
        self.stress_slider.setValue(110)
        self.stress_slider.valueChanged.connect(self.on_param_changed)
        self.stress_lbl = QLabel("1.1x (微度缓行)")
        self.stress_lbl.setStyleSheet("color: #00d2ff;")

        form.addRow("导航源起跳点 (Start):", self.start_combo)
        form.addRow("目标汇聚点 (End):", self.end_combo)
        form.addRow("实时路网阻尼因子:", self.stress_slider)
        form.addRow("路况损耗值:", self.stress_lbl)

        right_layout.addLayout(form)

        # 寻路终端输出黑框
        right_layout.addWidget(QLabel("Dijkstra 算法解算过程 (逐步拓扑松弛矩阵):"))
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 4px; color: #10b981; font-family: 'Consolas'; font-size: 11px; }
        """)
        right_layout.addWidget(self.console)

        # 执行寻路按钮
        self.nav_btn = QPushButton("执行 Dijkstra 三维空间寻路")
        self.nav_btn.setStyleSheet("""
            QPushButton { background: #00d2ff; color: #000; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #00b4d8; }
        """)
        self.nav_btn.clicked.connect(self.run_routing_solver)
        right_layout.addWidget(self.nav_btn)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([500, 440])
        self.layout.addWidget(splitter)

    # 4个节点高保真按钮交互
    def on_node_clicked(self, node_code):
        node_char = node_code[-1]  # 提取 A, B, C, D
        if self.select_mode == "START":
            for i in range(self.start_combo.count()):
                if self.start_combo.itemText(i).startswith(node_char):
                    self.start_combo.setCurrentIndex(i)
            self.select_mode = "END"
            self.console.clear()
            self.console.addItem(f"[系统设定] 起始节点锁定 -> Node_{node_char}")
        else:
            for i in range(self.end_combo.count()):
                if self.end_combo.itemText(i).startswith(node_char):
                    self.end_combo.setCurrentIndex(i)
            self.select_mode = "START"
            self.console.addItem(f"[系统设定] 终止节点锁定 -> Node_{node_char}")
            self.run_routing_solver()  # 自动开始寻路

    def on_param_changed(self):
        val = self.stress_slider.value() / 100.0
        self.stress_lbl.setText(f"{val:.1f}x" + (" (严重大雾阻塞)" if val > 2.0 else " (路网基本顺畅)"))

    def run_routing_solver(self):
        """执行 Dijkstra 最短路径解算"""
        start_char = self.start_combo.currentText()[0]
        end_char = self.end_combo.currentText()[0]

        if start_char == end_char:
            QMessageBox.warning(self, "拓扑冲突", "空间寻路起点不可与终点相同！")
            return

        # 解算算法（包含详细的演算步骤日志）
        path, base_distance, calculation_steps = self.engine.solve_dijkstra_with_steps(start_char, end_char)

        # 考虑滑动条环境系数阻尼
        stress = self.stress_slider.value() / 100.0
        final_distance = base_distance * stress

        # 预估时间
        eta = int(final_distance * 1.8)

        self.console.clear()
        # 实时逐行吐出算法的每一步计算步骤，极大提升科技交互感与代码厚度
        for step in calculation_steps:
            self.console.addItem(step)

        self.console.addItem(f"----------------------------------------")
        self.console.addItem(f"最优导航路径: " + " -> ".join(path))
        self.console.addItem(f"经过物理损耗修正的总距离: {final_distance:.2f} km")
        self.console.addItem(f"估计行驶时间 (ETA): {eta} 分钟")
        self.console.addItem(f"----------------------------------------")
        self.console.scrollToBottom()

    def refresh_data(self):
        pass

    def save_changes(self):
        pass