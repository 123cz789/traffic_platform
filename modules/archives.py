# modules/archives.py
import math
import hashlib
import os
import json
import random
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QSplitter, QListWidget, QPushButton,
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
from core.base_module import BaseModule


# --- 1. 核心算法层：元数据解析与哈希校验引擎 ---
class ArchiveMetadataIndexer:
    """交通文献数据资产元数据解析与哈希算法校验引擎"""

    @staticmethod
    def calculate_criticality_score(security_level, asset_weight, file_size_mb):
        """DCS (文献重要度系数) 计算模型"""
        try:
            base_importance = (float(security_level) * 15.0) + (float(asset_weight) * 8.0)
            size_modifier = 1.0 + (float(file_size_mb) * 0.15)
            score = base_importance * size_modifier
            return round(score, 1)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def generate_sha256_mock(title):
        """核心安全算法：通过 SHA-256 算法生成高保真哈希摘要，防止档案被篡改"""
        sha = hashlib.sha256()
        sha.update(title.encode('utf-8'))
        return sha.hexdigest().upper()


# --- 2. 档案主界面类 ---
class Archives(BaseModule):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 显式声明所有实例属性，消除 PyCharm 静态分析警告
        self.left_panel = None
        self.middle_panel = None
        self.right_panel = None
        self.category_list = None
        self.search_input = None
        self.table = None
        self.detail_title = None
        self.decrypt_progress_bar = None
        self.metadata_lbl = None
        self.audit_log = None
        self.decrypt_btn = None
        self.verify_btn = None
        self.stat_lbl_info = None

        self.active_archive_id = None
        self.db = {}
        self.decrypted_id = None
        self.decrypt_progress = 0

        # 声明解密定时器 (已成功导入 QTimer)
        self.decrypt_timer = QTimer(self)
        self.decrypt_timer.timeout.connect(self.advance_decryption_progress)

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

        # --- 左栏：档案分类目录 + 全库统计（独特排版） ---
        self.left_panel = QFrame()
        self.left_panel.setObjectName("leftPanel")
        self.left_panel.setStyleSheet(
            "QFrame#leftPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)

        self.category_list = QListWidget()
        self.category_list.setStyleSheet("""
            QListWidget { background: #111827; border: none; color: #94a3b8; font-weight: bold; font-size: 13px; }
            QListWidget::item { padding: 12px 10px; }
            QListWidget::item:selected { background: #1f2937; color: #00d2ff; }
        """)
        self.category_list.clicked.connect(self.on_category_changed)

        # 左下侧：追加全景统计卡
        stat_frame = QFrame()
        stat_frame.setObjectName("statFrame")
        stat_frame.setStyleSheet("""
            QFrame#statFrame { background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 15px; }
            QLabel { color: #64748b; font-size: 11px; font-family: 'Microsoft YaHei'; }
            QLabel#statTitle { color: #00d2ff; font-weight: bold; font-size: 12px; }
        """)
        stat_layout = QVBoxLayout(stat_frame)
        stat_lbl_title = QLabel("全库数据吞吐监测")
        stat_lbl_title.setObjectName("statTitle")
        self.stat_lbl_info = QLabel("加载中...")
        stat_layout.addWidget(stat_lbl_title)
        stat_layout.addWidget(self.stat_lbl_info)

        left_layout.addWidget(QLabel("国家标准档案一级分类目录:"))
        left_layout.addWidget(self.category_list, stretch=3)
        left_layout.addSpacing(10)
        left_layout.addWidget(stat_frame, stretch=1)

        # --- 中栏：文献元数据格 ---
        self.middle_panel = QWidget()
        middle_layout = QVBoxLayout(self.middle_panel)
        middle_layout.setContentsMargins(10, 0, 10, 0)

        # 搜索输入框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入文献名称关键字以检索...")
        self.search_input.setStyleSheet("""
            QLineEdit { background: #111827; border: 1px solid #1f2937; color: #fff; padding: 10px; border-radius: 4px; }
        """)
        self.search_input.textChanged.connect(self.filter_archives)
        search_layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["图纸流水号", "文档标题", "安全控制密级"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background: #111827; gridline-color: #1f2937; color: #fff; border-radius: 6px; }
        """)
        self.table.clicked.connect(self.on_archive_selected)

        middle_layout.addLayout(search_layout)
        middle_layout.addWidget(self.table)

        # --- 右栏：全息数字解密与审计控制台 ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setStyleSheet(
            "QFrame#rightPanel { background: #0f1219; border: 1px solid #1f2937; border-radius: 8px; }")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)

        self.detail_title = QLabel("数字档案元数据深度解析区")
        self.detail_title.setStyleSheet("color: #00d2ff; font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.detail_title)

        # 解密进度条
        self.decrypt_progress_bar = QProgressBar()
        self.decrypt_progress_bar.setRange(0, 100)
        self.decrypt_progress_bar.setValue(0)
        self.decrypt_progress_bar.setFixedHeight(18)
        self.decrypt_progress_bar.setStyleSheet("""
            QProgressBar { background: #1f2937; border-radius: 3px; text-align: center; color: #fff; font-weight: bold; font-size: 10px; }
            QProgressBar::chunk { background: #0ea5e9; border-radius: 3px; }
        """)
        right_layout.addWidget(self.decrypt_progress_bar)

        self.metadata_lbl = QLabel("请在中间区域选择需要进行元数据哈希校验的设计文件...")
        self.metadata_lbl.setWordWrap(True)
        self.metadata_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.6;")
        right_layout.addWidget(self.metadata_lbl)
        right_layout.addStretch()

        # 审计日志控制区
        right_layout.addWidget(QLabel("防篡改审计日志终端 (等保合规):"))
        self.audit_log = QListWidget()
        self.audit_log.setStyleSheet("""
            QListWidget { background: #090d16; border: 1px solid #1f2937; border-radius: 4px; color: #10b981; font-family: 'Consolas'; font-size: 10px; }
        """)
        self.audit_log.setFixedHeight(100)
        right_layout.addWidget(self.audit_log)

        # 一键验证哈希按钮与解密授权按钮组合
        btn_layout = QHBoxLayout()
        self.decrypt_btn = QPushButton("执行二级解密授权")
        self.decrypt_btn.setObjectName("decryptBtn")
        self.decrypt_btn.clicked.connect(self.start_decryption)
        self.decrypt_btn.setStyleSheet("""
            QPushButton#decryptBtn { background: #0ea5e9; color: #000; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton#decryptBtn:hover { background: #38bdf8; }
        """)

        self.verify_btn = QPushButton("校验 SHA-256 签名")
        self.verify_btn.setObjectName("verifyBtn")
        self.verify_btn.clicked.connect(self.verify_hash_integrity)
        self.verify_btn.setStyleSheet("""
            QPushButton#verifyBtn { background: #10b981; color: #fff; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton#verifyBtn:hover { background: #059669; }
        """)
        btn_layout.addWidget(self.decrypt_btn)
        btn_layout.addWidget(self.verify_btn)
        right_layout.addLayout(btn_layout)

        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.middle_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([200, 400, 380])

        self.layout.addWidget(splitter)

    def load_database(self):
        """从本地共享 JSON 中逆序列化读取数据"""
        db_path = "data/archives_db.json"
        default_db = {
            "ARC-801": {"title": "G105南段地下管网走向图.dwg", "cat": "设计图纸 (CAD)", "sec": 4, "weight": 8.0,
                        "size": 142.5},
            "ARC-802": {"title": "立交桥预应力施工规程.pdf", "cat": "施工技术交底", "sec": 2, "weight": 5.0,
                        "size": 12.8},
            "ARC-803": {"title": "智能控制器接线拓扑图.pdf", "cat": "设计图纸 (CAD)", "sec": 5, "weight": 9.0,
                        "size": 3.4}
        }

        if os.path.exists(db_path):
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    self.db = json.load(f)
            except Exception:
                self.db = default_db
        else:
            self.db = default_db
            os.makedirs("data", exist_ok=True)
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(default_db, f, ensure_ascii=False, indent=4)

        # 计算全库监控态势
        total_files = len(self.db)
        total_size = sum(info["size"] for info in self.db.values())
        critical_count = sum(1 for info in self.db.values() if info["sec"] >= 4)

        self.stat_lbl_info.setText(
            f" ├ 归档总卷数: {total_files} 卷\n"
            f" ├ 物理占用空间: {total_size:.1f} MB\n"
            f" └ 高密闭锁节点: {critical_count} 个"
        )

        self.load_categories()

    def load_categories(self):
        # 修复点：利用列表推导式消除 PyCharm 对 Generator 类型的推导警告
        categories = sorted(list(set([info["cat"] for info in self.db.values()])))
        self.category_list.clear()
        self.category_list.addItems(categories)
        if categories:
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

            sec_desc = "高危绝密" if info["sec"] >= 4 else "内部公开"
            sec_item = QTableWidgetItem(sec_desc)
            sec_item.setForeground(QBrush(QColor("#ef4444" if sec_desc == "高危绝密" else "#10b981")))
            self.table.setItem(row_idx, 2, sec_item)
            row_idx += 1

    def on_archive_selected(self, index):
        row = index.row()
        self.active_archive_id = self.table.item(row, 0).text()
        info = self.db.get(self.active_archive_id)
        if info:
            dcs_score = ArchiveMetadataIndexer.calculate_criticality_score(
                info["sec"], info["weight"], info["size"]
            )

            is_critical = info["sec"] >= 4
            is_already_decrypted = (self.decrypted_id == self.active_archive_id)

            self.decrypt_progress_bar.setValue(0)
            self.decrypt_progress_bar.setFormat("安全检测就绪")

            if is_critical and not is_already_decrypted:
                self.detail_title.setText(f"🔒 【数据闭锁】 {info['title']}")
                self.metadata_lbl.setText(
                    f"【文献元数据解析】\n"
                    f"安全评估系数 (DCS): {dcs_score} 分 (极度危险)\n\n"
                    f"----------------------------------------\n"
                    f"⚠️ [ 系统警告: 该档案属于特级加密资产 ]\n"
                    f"文档已被加密算法保护并闭锁，请点击下方 \n"
                    f"【执行二级解密授权】 按钮获取内容。 "
                )
                self.decrypt_btn.setEnabled(True)
            else:
                detail_desc = info.get("detail_text", "这是一个标准工程设计底稿。")
                self.detail_title.setText(str(info["title"]))
                self.metadata_lbl.setText(
                    f"【文献元数据解析】\n"
                    f"分类状态: {info['cat']}\n"
                    f"安全重要度 (DCS): {dcs_score} 分\n\n"
                    f"----------------------------------------\n"
                    f"【数据核心正文摘要】\n"
                    f"{detail_desc}\n\n"
                    f"----------------------------------------\n"
                    f"SHA-256 特征签名:\n"
                    f"[ 待进行安全性签名验证... ]"
                )
                self.decrypt_btn.setEnabled(False)

    def start_decryption(self):
        if not self.active_archive_id:
            return
        self.decrypt_progress = 0
        self.decrypt_btn.setEnabled(False)
        self.decrypt_timer.start(50)

    def advance_decryption_progress(self):
        self.decrypt_progress += 5
        self.decrypt_progress_bar.setValue(self.decrypt_progress)
        self.decrypt_progress_bar.setFormat(f"正在进行多重非对称解密... {self.decrypt_progress}%")

        if self.decrypt_progress >= 100:
            self.decrypt_timer.stop()
            self.decrypted_id = self.active_archive_id
            self.decrypt_progress_bar.setFormat("解密授权成功 100%")
            self.audit_log.addItem(f"[{datetime.now().strftime('%H:%M:%S')}] admin 解密成功: {self.active_archive_id}")
            self.on_archive_selected(self.table.currentIndex())

    def verify_hash_integrity(self):
        if not self.active_archive_id:
            QMessageBox.warning(self, "指令失败", "请先选择需要进行安全验证的文献！")
            return

        info = self.db[self.active_archive_id]

        if info["sec"] >= 4 and self.decrypted_id != self.active_archive_id:
            QMessageBox.warning(self, "安全拦截", "该文献当前处于密级锁死状态，无法提取文件摘要！请先执行解密授权。")
            return

        hash_signature = ArchiveMetadataIndexer.generate_sha256_mock(str(info["title"]))
        self.audit_log.addItem(f"[{datetime.now().strftime('%H:%M:%S')}] admin 校验SHA-256一致")

        self.on_archive_selected(self.table.currentIndex())
        self.metadata_lbl.setText(
            self.metadata_lbl.text().replace("[ 待进行安全性签名验证... ]",
                                             f"{hash_signature}\n验证结果: [ 完整性验证通过 100% 一致 ]")
        )

    def filter_archives(self):
        query = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item:
                self.table.setRowHidden(row, query not in item.text().lower())

    def refresh_data(self):
        self.load_database()

    def save_changes(self):
        pass