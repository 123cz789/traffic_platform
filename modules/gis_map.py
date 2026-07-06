# modules/gis_map.py
import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QFormLayout, QComboBox,
                             QSlider, QListWidget, QPushButton, QMessageBox, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont
from core.base_module import BaseModule


# --- 1. 核心算法层：拓扑图 Dijkstra 最短路径求解器 ---
class DynamicAvoidanceDijkstraEngine:
    """
    空间地理网络拓扑寻路内核
    定义 6 节点复合邻接矩阵，并使用 Dijkstra 算法求解任意两点间的最短物理路径。
    支持在计算中实时屏蔽 blocked_nodes（灾害禁行节点），自动重构并计算出绕行路径。
    """

    def __init__(self):
        # 基础路网枢纽节点定义 (A:主枢纽, B:立交桥, C:隧道北, D:高架匝道, E:滨江路, F:货运港)
        self.nodes = ["A", "B", "C", "D", "E", "F"]

        # 初始路网拓扑权重图 (物理距离km)
        # 999.0 代表两点之间无直接物理相连
        self.adjacency_matrix = {
            "A": {"B": 3.5, "C": 5.0, "D": 999.0, "E": 999.0, "F": 999.0},
            "B": {"A": 3.5, "C": 1.2, "D": 4.1, "E": 999.0, "F": 999.0},
            "C": {"A": 5.0, "B": 1.2, "D": 2.2, "E": 6.0, "F": 999.0},
            "D": {"B": 4.1, "C": 2.2, "E": 1.8, "F": 7.5},
            "E": {"C": 6.0, "D": 1.8, "F": 3.0},
            "F": {"D": 7.5, "E": 3.0}
        }

    def solve_safest_route(self, start, end, blocked_nodes):
        """
        核心寻路算法：
        在计算中屏蔽 blocked_nodes，实现动态规避绕行。
        """
        if start not in self.nodes or end not in self.nodes:
            return None, 999.0, ["ERROR_CODE: 寻路首尾节点不属于当前物理图谱"]

        if start in blocked_nodes:
            return None, 999.0, [f"CRITICAL_ERROR: 起点 Node_{start} 自身处于极高危灾区，无法发送车辆！"]

        distances = {node: 999.0 for node in self.nodes}
        distances[start] = 0.0
        previous_nodes = {node: None for node in self.nodes}
        unvisited = list(self.nodes)
        log_steps = []

        log_steps.append(f"初始化拓扑导航。起始站: Node_{start} | 规避受损禁行节点: {list(blocked_nodes)}")

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


# --- 2. 视觉组件：3D 等轴测全息投影网格画布 (修正了所有核心绘图部件的导入) ---
class Gis3DCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.parent_module = parent

        # 定义 3D 空间坐标系 (X, Y, Z)
        # 节点 C (机场路) 设为高空中继节点 (Z=60)
        self.nodes_3d = {
            "A": (-120, -100, 0),
            "B": (120, -100, 0),
            "C": (0, 0, 60),
            "D": (-120, 100, 0),
            "E": (120, 100, 0),
            "F": (0, 200, 0)
        }

    def project(self, x, y, z):
        """数学公式：等轴测 30 度三维空间坐标投影至 2D 屏幕物理像素"""
        cx = self.width() / 2
        cy = self.height() / 2 - 20

        cos_30 = 0.866
        sin_30 = 0.5

        # 投影计算
        u = (x - y) * cos_30 + cx
        v = (x + y) * sin_30 - z + cy
        return int(u), int(v)

    def paintEvent(self, event):
        if self.width() < 10 or not self.isVisible() or not self.parent_module:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. 绘制虚幻的 3D 地向网格线 (Grid Floor)
        painter.setPen(QPen(QColor("#111827"), 1, Qt.PenStyle.DashLine))
        for g in range(-3, 4):
            # 绘制纵横网格线
            u1, v1 = self.project(g * 50, -150, 0)
            u2, v2 = self.project(g * 50, 250, 0)
            painter.drawLine(u1, v1, u2, v2)

            u3, v3 = self.project(-150, g * 50, 0)
            u4, v4 = self.project(150, g * 50, 0)
            painter.drawLine(u3, v3, u4, v4)

        # 2. 绘制 3D 承重支架立柱 (专为高空 C 节点设计)
        u_base, v_base = self.project(0, 0, 0)
        u_top, v_top = self.project(0, 0, 60)
        painter.setPen(QPen(QColor("#1f2937"), 4))
        painter.drawLine(u_base, v_base, u_top, v_top)
        painter.setPen(QPen(QColor("#00d2ff"), 1, Qt.PenStyle.DotLine))
        painter.drawLine(u_base, v_base, u_top, v_top)

        # 获取当前主模块计算好的活跃最短路径和禁行集
        active_path = getattr(self.parent_module, "active_path", [])
        blocked_nodes = getattr(self.parent_module, "active_blocked_nodes", set())
        start_node = self.parent_module.get_current_start_node()
        end_node = self.parent_module.get_current_end_node()

        # 3. 绘制 3D 拓扑边连接线
        edges = [
            ("A", "B"), ("A", "C"), ("B", "C"), ("B", "D"),
            ("C", "D"), ("C", "E"), ("D", "E"), ("D", "F"), ("E", "F")
        ]

        for n1, n2 in edges:
            u1, v1 = self.project(*self.nodes_3d[n1])
            u2, v2 = self.project(*self.nodes_3d[n2])

            # 判断这条边是否属于当前规划的“最优避障路径”
            is_active = False
            if active_path:
                for idx in range(len(active_path) - 1):
                    if (active_path[idx] == n1 and active_path[idx + 1] == n2) or \
                            (active_path[idx] == n2 and active_path[idx + 1] == n1):
                        is_active = True
                        break

            if is_active:
                painter.setPen(QPen(QColor("#00d2ff"), 4))
                painter.drawLine(u1, v1, u2, v2)
            else:
                painter.setPen(QPen(QColor("#1f2937"), 1))
                painter.drawLine(u1, v1, u2, v2)

        # 4. 绘制 3D 空间球状节点
        for char, coord in self.nodes_3d.items():
            u, v = self.project(*coord)

            is_blocked = char in blocked_nodes
            is_start = char == start_node
            is_end = char == end_node

            if is_blocked:
                # 绘制蓝色发光防护罩
                painter.setBrush(QBrush(QColor(239, 68, 68, 40)))
                painter.setPen(QPen(QColor("#ef4444"), 1, Qt.PenStyle.DashLine))
                painter.drawEllipse(u - 25, v - 25, 50, 50)

                # 核心点
                painter.setBrush(QBrush(QColor("#ef4444")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(u - 8, v - 8, 16, 16)

                # 文字
                painter.setPen(QPen(QColor("#ef4444")))
                painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                painter.drawText(u + 12, v + 5, f"{char} [ ⚠️ 已封锁 ]")

            elif is_start:
                painter.setBrush(QBrush(QColor("#10b981")))
                painter.setPen(QPen(QColor("#ffffff"), 1))
                painter.drawRect(u - 8, v - 8, 16, 16)
                painter.setPen(QPen(QColor("#10b981")))
                painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                painter.drawText(u + 12, v + 5, f"{char} [ 起点 ]")

            elif is_end:
                painter.setBrush(QBrush(QColor("#f59e0b")))
                painter.setPen(QPen(QColor("#ffffff"), 1))
                painter.drawRect(u - 8, v - 8, 16, 16)
                painter.setPen(QPen(QColor("#f59e0b")))
                painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                painter.drawText(u + 12, v + 5, f"{char} [ 终点 ]")

            else:
                painter.setBrush(QBrush(QColor("#0f172a")))
                painter.setPen(QPen(QColor("#00d2ff"), 1))
                painter.drawEllipse(u - 6, v - 6, 12, 12)
                painter.setPen(QPen(QColor("#94a3b8")))
                painter.setFont(QFont("Microsoft YaHei", 8))
                painter.drawText(u + 12, v + 4, char)

        painter.end()


# --- 3. GIS 主控制台 ---
class GisMap(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.router_engine = DynamicAvoidanceDijkstraEngine()
        self.active_blocked_nodes = set()
        self.active_path = []
        self.selected_node_char = "A"

        self.nodes_data = {
            "A": {"name": "G105立交枢纽 (Node_A)", "status": "ONLINE", "desc": "高架桥网交汇核心"},
            "B": {"name": "迎宾路交叉口 (Node_B)", "status": "ONLINE", "desc": "干线交通枢纽"},
            "C": {"name": "机场路高架大桥 (Node_C)", "status": "ONLINE", "desc": "高空立体桥梁系统"},
            "D": {"name": "滨江隧道入口段 (Node_D)", "status": "ONLINE", "desc": "地下管廊与路面交界"},
            "E": {"name": "货运快速通道 (Node_E)", "status": "ONLINE", "desc": "重载集卡专用货运线"},
            "F": {"name": "临港枢纽大桥段 (Node_F)", "status": "ONLINE", "desc": "特大跨江钢混结构桥"}
        }
        self.node_btns = {}
        self.init_ui()
        self.run_routing_solver()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # 左右双区切分
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左侧：3D全息大屏 + 节点控制舱 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 15, 0)
        left_layout.setSpacing(12)

        self.canvas_3d = Gis3DCanvas(self)

        # 3x2 蜂窝按钮布局 (用作下方的物理节点分配面板)
        btn_grid_frame = QFrame()
        btn_grid_frame.setObjectName("btnGridFrame")
        btn_grid_frame.setStyleSheet(
            "QFrame#btnGridFrame { background: #111827; border-radius: 8px; border: 1px solid #1f2937; }")
        grid_layout = QGridLayout(btn_grid_frame)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(15, 15, 15, 15)

        node_positions = {
            "A": (0, 0), "B": (0, 2), "C": (1, 1),
            "D": (2, 0), "E": (2, 2), "F": (3, 1)
        }
        for char, pos in node_positions.items():
            btn = QPushButton(f"节点 {char}")
            btn.setFixedSize(100, 40)
            btn.clicked.connect(lambda checked, c=char: self.on_node_clicked(c))
            grid_layout.addWidget(btn, pos[0], pos[1], alignment=Qt.AlignmentFlag.AlignCenter)
            self.node_btns[char] = btn

        # 选中节点状态舱
        self.control_cabin = QFrame()
        self.control_cabin.setObjectName("controlCabin")
        self.control_cabin.setStyleSheet("""
            QFrame#controlCabin { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; padding: 12px; }
            QLabel#cabinTitle { color: #00d2ff; font-weight: bold; font-size: 13px; }
            QLabel#cabinDesc { color: #64748b; font-size: 11px; }
        """)
        cabin_layout = QVBoxLayout(self.control_cabin)
        self.cabin_title = QLabel("当前选中: Node_A")
        self.cabin_title.setObjectName("cabinTitle")
        self.cabin_desc = QLabel("状态: 运行正常 | 描述: 高架桥网交汇核心")
        self.cabin_desc.setObjectName("cabinDesc")

        btn_box = QHBoxLayout()
        set_start_btn = QPushButton("设为寻路起点")
        set_start_btn.setStyleSheet(
            "background: #0ea5e9; color: #000; font-weight: bold; padding: 6px; border-radius: 3px;")
        set_start_btn.clicked.connect(self.set_active_as_start)

        set_end_btn = QPushButton("设为寻路终点")
        set_end_btn.setStyleSheet(
            "background: #06b6d4; color: #000; font-weight: bold; padding: 6px; border-radius: 3px;")
        set_end_btn.clicked.connect(self.set_active_as_end)

        self.block_btn = QPushButton("注入路障/事故封锁")
        self.block_btn.setStyleSheet(
            "background: #ef4444; color: #fff; font-weight: bold; padding: 6px; border-radius: 3px;")
        self.block_btn.clicked.connect(self.toggle_node_blockage)

        btn_box.addWidget(set_start_btn)
        btn_box.addWidget(set_end_btn)
        btn_box.addWidget(self.block_btn)

        cabin_layout.addWidget(self.cabin_title)
        cabin_layout.addWidget(self.cabin_desc)
        cabin_layout.addSpacing(5)
        cabin_layout.addLayout(btn_box)

        left_layout.addWidget(QLabel("数字孪生 3D 全息路网拓扑分析大屏:"))
        left_layout.addWidget(self.canvas_3d, stretch=3)
        left_layout.addWidget(btn_grid_frame, stretch=2)
        left_layout.addWidget(self.control_cabin, stretch=1)

        # --- 右侧：Dijkstra 路径规划控制台 ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(25, 25, 25, 25)

        right_layout.addWidget(QLabel("最优化避障寻路决策中心"), alignment=Qt.AlignmentFlag.AlignTop)

        form = QFormLayout()
        self.start_combo = QComboBox()
        self.start_combo.addItems(["A (应急一号库)", "B (迎宾路中队)", "E (货运特勤组)"])
        self.start_combo.currentIndexChanged.connect(self.run_routing_solver)

        self.end_combo = QComboBox()
        self.end_combo.addItems(["F (临港大桥)", "D (隧道南段)", "C (高架桥面)"])
        self.end_combo.currentIndexChanged.connect(self.run_routing_solver)

        self.stress_slider = QSlider(Qt.Orientation.Horizontal)
        self.stress_slider.setRange(10, 300);
        self.stress_slider.setValue(110)
        self.stress_slider.valueChanged.connect(self.on_param_changed)
        self.stress_lbl = QLabel("1.1x (微度缓行)")
        self.stress_lbl.setStyleSheet("color: #00d2ff;")

        form.addRow("导航源起跳点 (Start):", self.start_combo)
        form.addRow("目标汇聚点 (End):", self.end_combo)
        form.addRow("实时路网阻尼因子:", self.stress_slider)
        form.addRow("路况损耗值:", self.stress_lbl)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("Dijkstra 算法解算过程 (逐步拓扑松弛矩阵):"))
        self.console = QListWidget()
        self.console.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 4px; color: #10b981; font-family: 'Consolas'; font-size: 11px; }
        """)
        right_layout.addWidget(self.console)

        btn_group = QHBoxLayout()
        self.nav_btn = QPushButton("执行 3D 避障寻路解算")
        self.nav_btn.setStyleSheet("""
            QPushButton { background: #00d2ff; color: #000; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #00b4d8; }
        """)
        self.nav_btn.clicked.connect(self.run_routing_solver)

        self.reset_btn = QPushButton("一键重置全路网")
        self.reset_btn.setStyleSheet("""
            QPushButton { background: #1f2937; color: #94a3b8; padding: 12px; font-weight: bold; border-radius: 4px; border: 1px solid #374151; }
            QPushButton:hover { color: #fff; background: #374151; }
        """)
        self.reset_btn.clicked.connect(self.reset_entire_network)

        btn_group.addWidget(self.nav_btn, stretch=2)
        btn_group.addWidget(self.reset_btn, stretch=1)
        right_layout.addLayout(btn_group)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([550, 410])
        self.layout.addWidget(splitter)

        self.on_node_clicked("A")

    def get_current_start_node(self):
        return self.start_combo.currentText()[0]

    def get_current_end_node(self):
        return self.end_combo.currentText()[0]

    def on_node_clicked(self, code):
        """点击底部控制按钮时，更新3D画布焦点并配置样式"""
        self.selected_node_char = code
        info = self.nodes_data[code]

        self.cabin_title.setText(f"当前选中: Node_{code} (物理遥测)")
        status_text = "运行正常 (ONLINE)" if info["status"] == "ONLINE" else "⚠️ 已被路障封锁 (BLOCKED)"
        self.cabin_desc.setText(f"状态: {status_text} | 描述: {info['desc']}")

        # 刷新按钮样式
        for char, btn in self.node_btns.items():
            if char == code:
                btn.setStyleSheet("""
                    QPushButton { 
                        background: #0f172a; color: #00d2ff; border: 2px solid #00d2ff; 
                        border-radius: 6px; font-weight: bold; font-size: 12px;
                    }
                """)
            else:
                if self.nodes_data[char]["status"] == "BLOCKED":
                    btn.setStyleSheet("""
                        QPushButton { 
                            background: #2b121a; color: #ef4444; border: 1px dashed #ef4444; 
                            border-radius: 6px; font-weight: bold; font-size: 12px;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton { 
                            background: #111827; color: #94a3b8; border: 1px solid #374151; 
                            border-radius: 6px; font-weight: bold; font-size: 12px;
                        }
                    """)

        # 核心绘制重绘调用 (刷新 3D 画布)
        self.canvas_3d.update()

    def set_active_as_start(self):
        for i in range(self.start_combo.count()):
            if self.start_combo.itemText(i).startswith(self.selected_node_char):
                self.start_combo.setCurrentIndex(i)
                self.console.addItem(f"定位更新: 起点配置为 -> Node_{self.selected_node_char}")
                self.run_routing_solver()
                return
        QMessageBox.warning(self, "定位拦截", "抱歉！该节点在规划网络中不能作为合法的救援始发中队！")

    def set_active_as_end(self):
        for i in range(self.end_combo.count()):
            if self.end_combo.itemText(i).startswith(self.selected_node_char):
                self.end_combo.setCurrentIndex(i)
                self.console.addItem(f"定位更新: 终点配置为 -> Node_{self.selected_node_char}")
                self.run_routing_solver()
                return
        QMessageBox.warning(self, "定位拦截", "抱歉！该节点在规划网络中不能作为合法的受灾终端！")

    def toggle_node_blockage(self):
        """核心交互：对特定节点执行路障闭锁注入或清空"""
        current_status = self.nodes_data[self.selected_node_char]["status"]
        if current_status == "ONLINE":
            self.nodes_data[self.selected_node_char]["status"] = "BLOCKED"
            self.active_blocked_nodes.add(self.selected_node_char)
            self.console.addItem(
                f"⚠️ [路网警报] 节点 Node_{self.selected_node_char} 已成功注入火灾/事故路障！全线封锁中。")
        else:
            self.nodes_data[self.selected_node_char]["status"] = "ONLINE"
            self.active_blocked_nodes.discard(self.selected_node_char)
            self.console.addItem(f"[系统提示] 节点 Node_{self.selected_node_char} 清障完成，物理通道恢复畅通。")

        self.on_node_clicked(self.selected_node_char)
        self.run_routing_solver()

    def on_param_changed(self):
        val = self.stress_slider.value() / 100.0
        self.stress_lbl.setText(f"{val:.1f}x" + (" (严重大雾阻塞)" if val > 2.0 else " (路网基本顺畅)"))
        self.run_routing_solver()

    def run_routing_solver(self):
        """执行带有动态故障点避障功能的最优路径寻路"""
        start_char = self.get_current_start_node()
        end_char = self.get_current_end_node()

        if start_char == end_char:
            self.console.clear()
            self.console.addItem("等待解算... 起点与终点不能相同！")
            return

        # 调用避障寻路引擎
        self.active_path, distance, steps = self.router_engine.solve_safest_route(
            start_char, end_char, self.active_blocked_nodes
        )

        # 刷新右侧控制台
        self.console.clear()
        for step in steps:
            self.console.addItem(step)

        if self.active_path:
            self.console.addItem(f"----------------------------------------")
            self.console.addItem(f"规划安全避障路线: " + " -> ".join(self.active_path))
            self.console.addItem(f"安全路径物理距离: {distance:.2f} km")
            self.console.addItem(f"预计车队抵达时间 (ETA): {int(distance * 1.8)} 分钟")
        else:
            self.console.addItem(f"----------------------------------------")
            self.console.addItem("警告：全通路已受灾害严重损毁，无法通行！")

        self.console.scrollToBottom()

        # 核心绘制重绘调用 (通知 3D 画布重绘)
        self.canvas_3d.update()

    def reset_entire_network(self):
        self.active_blocked_nodes.clear()
        for k in self.nodes_data.keys():
            self.nodes_data[k]["status"] = "ONLINE"
        self.on_node_clicked(self.selected_node_char)
        self.run_routing_solver()
        self.console.addItem("[系统状态] 已成功重置全路网！所有阻断恢复，物理信道畅通。")

    def refresh_data(self):
        pass

    def save_changes(self):
        pass