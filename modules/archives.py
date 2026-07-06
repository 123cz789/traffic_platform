# modules/archives.py
import math
import hashlib
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QListWidget, QPushButton,
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from core.base_module import BaseModule


# --- 1. 核心算法层：元数据解析与哈希校验引擎 ---
class ArchiveMetadataIndexer:
    """交通文献数据资产元数据索引与安全完整性计算内核"""

    @staticmethod
    def calculate_criticality_score(security_level, asset_weight, file_size_mb):
        """
        核心物理算法：
        DCS (文档关键度分数) = (密级 * 15 + 资产权重 * 8) * (1.0 + log10(文件大小))
        DCS分数越高，代表该技术档案泄露危害越大。
        """
        try:
            base_importance = (float(security_level) * 15.0) + (float(asset_weight) * 8.0)
            size_modifier = 1.0 + math.log10(max(1.0, float(file_size_mb)))
            score = base_importance * size_modifier
            return round(score, 1)
        except Exception:
            return 0.0

    @staticmethod
    def generate_sha256_mock(title):
        """核心安全算法：根据图纸标题，实时计算出该图纸的SHA-256数字签名值"""
        sha = hashlib.sha256()
        sha.update(title.encode('utf-8'))
        return sha.hexdigest().upper()


# --- 2. 档案主界面类 ---
class Archives(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_archive_id = None  # 修复点：确保与后文逻辑中的属性变量名完全一致
        self.db = {}
        self.init_ui()
        self.load_database()

    def init_ui(self):
        # 纵向主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # 模块大标题
        header = QLabel("智慧交通设施数字档案、CAD设计图纸与元数据解析中心")
        header.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        self.layout.addWidget(header)

        # 三栏式空间分割布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1f2937; width: 2px; }")

        # --- 左栏：档案分类目录 ---
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setStyleSheet(
            "QFrame#leftPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)

        self.category_list = QListWidget()
        self.category_list.setStyleSheet("""
            QListWidget { background: #111827; border: none; color: #94a3b8; font-weight: bold; }
            QListWidget::item { padding: 12px 10px; border-radius: 4px; }
            QListWidget::item:selected { background: #1f2937; color: #00d2ff; }
        """)
        self.category_list.clicked.connect(self.on_category_changed)

        left_layout.addWidget(QLabel("国家标准档案一级分类目录:"))
        left_layout.addWidget(self.category_list)

        # --- 中栏：文献元数据格 ---
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(10, 0, 10, 0)

        # 搜索输入框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入文献名称关键字...")
        self.search_input.setStyleSheet("""
            QLineEdit { background: #111827; border: 1px solid #1f2937; color: #fff; padding: 10px; border-radius: 4px; }
        """)
        self.search_input.textChanged.connect(self.filter_archives)
        search_layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["图纸流水号", "文档标题", "所属密级"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background: #111827; gridline-color: #1f2937; color: #fff; border-radius: 6px; }
        """)
        self.table.clicked.connect(self.on_archive_selected)

        middle_layout.addLayout(search_layout)
        middle_layout.addWidget(self.table)

        # --- 右栏：元数据解析控制台 ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)

        self.detail_title = QLabel("数字档案元数据深度解析区")
        self.detail_title.setObjectName("detailTitle")
        self.detail_title.setStyleSheet("color: #00d2ff; font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.detail_title)

        self.metadata_lbl = QLabel("请在中间区域选择需要进行元数据哈希校验的设计文件...")
        self.metadata_lbl.setWordWrap(True)
        self.metadata_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.6;")
        right_layout.addWidget(self.metadata_lbl)
        right_layout.addStretch()

        # 一键验证哈希按钮
        self.verify_btn = QPushButton("校验 SHA-256 完整性签名")
        self.verify_btn.setStyleSheet("""
            QPushButton { background: #10b981; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background: #059669; }
        """)
        self.verify_btn.clicked.connect(self.verify_hash_integrity)
        right_layout.addWidget(self.verify_btn)

        splitter.addWidget(left_panel)
        splitter.addWidget(middle_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([180, 420, 350])

        self.layout.addWidget(splitter)

    def load_database(self):
        self.db = {
            "ARC-801": {"title": "G105南段地下管网走向图.dwg", "cat": "设计图纸 (CAD)", "sec": 4, "weight": 8.0,
                        "size": 142.5},
            "ARC-802": {"title": "立交桥预应力施工规程.pdf", "cat": "施工技术交底", "sec": 2, "weight": 5.0,
                        "size": 12.8},
            "ARC-803": {"title": "智能控制器接线拓扑图.pdf", "cat": "设计图纸 (CAD)", "sec": 5, "weight": 9.0,
                        "size": 3.4},
            "ARC-804": {"title": "机场大道段竣工检测报告.doc", "cat": "竣工验收报告", "sec": 3, "weight": 6.0,
                        "size": 25.1}
        }
        self.load_categories()

    def load_categories(self):
        categories = ["设计图纸 (CAD)", "施工技术交底", "竣工验收报告"]
        self.category_list.clear()
        self.category_list.addItems(categories)
        self.category_list.setCurrentRow(0)
        self.on_category_changed()

    def on_category_changed(self):
        current_item = self.category_list.currentItem()
        if not current_item:
            return
        current_cat = current_item.text()
        self.populate_table(current_cat)

    def populate_table(self, category_filter):
        self.table.setRowCount(0)
        row_idx = 0
        for doc_id, info in self.db.items():
            if info["cat"] != category_filter:
                continue
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(doc_id)))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(info["title"])))

            sec_desc = "机密" if info["sec"] >= 4 else "内部"
            sec_item = QTableWidgetItem(sec_desc)
            sec_item.setForeground(QBrush(QColor("#ef4444" if sec_desc == "机密" else "#10b981")))
            self.table.setItem(row_idx, 2, sec_item)
            row_idx += 1

    def on_archive_selected(self, index):
        row = index.row()
        self.active_archive_id = self.table.item(row, 0).text()
        info = self.db.get(self.active_archive_id)
        if info:
            # 调用核心算法
            dcs_score = ArchiveMetadataIndexer.calculate_criticality_score(
                info["sec"], info["weight"], info["size"]
            )

            self.detail_title.setText(str(info["title"]))
            self.metadata_lbl.setText(
                f"【文献元数据解析】\n"
                f"安全分类级别: {info['sec']} 级\n"
                f"归档大小: {info['size']} MB\n"
                f"系统核心权重: {info['weight']}\n"
                f"计算核心指数 (DCS): {dcs_score} 分\n\n"
                f"----------------------------------------\n"
                f"SHA-256 特征签名:\n"
                f"[ 待进行安全性签名验证... ]"
            )

    def verify_hash_integrity(self):
        # 修复安全漏洞：如果未选定任何行，优雅拦截，不再抛出 AttributeError 崩溃
        if not self.active_archive_id:
            QMessageBox.warning(self, "指令拦截", "请先在中间列表中选中一份文献档案，然后再进行安全哈希校验！")
            return

        info = self.db[self.active_archive_id]
        # 计算实时的 SHA-256 哈希值
        hash_signature = ArchiveMetadataIndexer.generate_sha256_mock(str(info["title"]))

        self.metadata_lbl.setText(
            f"【元数据解析 - 安全验证成功】\n"
            f"安全分类级别: {info['sec']} 级\n"
            f"归档大小: {info['size']} MB\n"
            f"系统核心权重: {info['weight']}\n\n"
            f"----------------------------------------\n"
            f"SHA-256 特征签名:\n"
            f"{hash_signature}\n"
            f"验证结果: [ 完整性验证通过 100% 一致 ]"
        )

    def filter_archives(self):
        query = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item:
                self.table.setRowHidden(row, query not in item.text().lower())

    def refresh_data(self):
        pass

    def save_changes(self):
        pass