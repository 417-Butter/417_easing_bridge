import os
import json
import webbrowser
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLabel, QPushButton, QSplitter, QListWidget, 
    QListWidgetItem, QInputDialog, QToolBar, QDialog,
    QMessageBox, QFileDialog
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QSize, QTimer
from tcp_server import EasingBridgeServer
from graph_editor import BezierGraphEditor
from preset_manager import PresetManager
from curve_math import generate_easing_table, CompositeBezier, BezierSegment

# =====================================================================
# HELP URL — Change this URL to your documentation page before release
# =====================================================================
HELP_URL = "https://github.com/417-Butter/417_easing_bridge"

# Settings file path (next to this script, stays in the zip)
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class ReorderableListWidget(QListWidget):
    """QListWidget subclass with manual drag-and-drop reordering in IconMode."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._on_reorder = None
        self._drag_row = -1

    def set_reorder_callback(self, callback):
        self._on_reorder = callback

    def startDrag(self, supportedActions):
        self._drag_row = self.currentRow()
        super().startDrag(supportedActions)

    def dropEvent(self, event):
        drop_pos = event.position().toPoint()
        target_item = self.itemAt(drop_pos)
        source_row = self._drag_row

        if source_row < 0 or source_row >= self.count():
            event.ignore()
            return

        target_row = self.row(target_item) if target_item else self.count() - 1
        if source_row == target_row:
            event.ignore()
            return

        source_item = self.takeItem(source_row)
        if not source_item:
            event.ignore()
            return

        self.insertItem(target_row, source_item)
        self.setCurrentItem(source_item)
        event.accept()
        self._drag_row = -1

        if self._on_reorder:
            QTimer.singleShot(0, self._on_reorder)


class EasingBridgeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cascadeur Easing Bridge")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.server = EasingBridgeServer(self, port=65432)
        self.server.status_message.connect(self.log_message)
        self.server.data_received.connect(self.handle_incoming_data)
        
        self.preset_manager = PresetManager()
        self.active_fetch_data = None
        self.is_mini_mode = False
        self.current_preset_index = 0
        self._tangents_visible = True
        self._normal_geometry = None  # saved geometry before mini mode

        self.setup_ui()
        self._restore_settings()
        self.server.start()

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    # ── Settings persistence ──────────────────

    def _save_settings(self):
        geo = self.geometry() if not self.is_mini_mode else self._normal_geometry
        data = {
            "x": geo.x() if geo else 100,
            "y": geo.y() if geo else 100,
            "width": geo.width() if geo else 850,
            "height": geo.height() if geo else 600,
            "mini_mode": self.is_mini_mode,
            "tangents_visible": self._tangents_visible,
            "splitter": self.splitter_main.sizes() if not self.is_mini_mode else None,
        }
        save_settings(data)

    def _restore_settings(self):
        s = load_settings()
        if not s:
            self.resize(850, 600)
            return
        x = s.get("x", 100)
        y = s.get("y", 100)
        w = s.get("width", 850)
        h = s.get("height", 600)
        self.setGeometry(x, y, w, h)
        self._normal_geometry = self.geometry()

        self._tangents_visible = s.get("tangents_visible", True)
        self.graph_editor.set_tangents_visible(self._tangents_visible)
        label = "ON" if self._tangents_visible else "OFF"
        self.action_tangent.setText(f"🔷 Tangents {label}")

        splitter_sizes = s.get("splitter")
        if splitter_sizes:
            self.splitter_main.setSizes(splitter_sizes)

        if s.get("mini_mode", False):
            self.toggle_mini_mode()

    # ── UI setup ──────────────────────────────

    def setup_ui(self):
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        
        self.action_fit = QAction("⛶ Fit", self)
        self.action_fit.triggered.connect(self.fit_graph)
        self.toolbar.addAction(self.action_fit)
        
        self.action_mini = QAction("🔳 Mini", self)
        self.action_mini.triggered.connect(self.toggle_mini_mode)
        self.toolbar.addAction(self.action_mini)
        
        self.toolbar.addSeparator()

        # Undo / Redo
        self.action_undo = QAction("⟵ Undo", self)
        self.action_undo.setToolTip("Undo last graph edit")
        self.action_undo.triggered.connect(self.do_undo)
        self.toolbar.addAction(self.action_undo)

        self.action_redo = QAction("Redo ⟶", self)
        self.action_redo.setToolTip("Redo last undone edit")
        self.action_redo.triggered.connect(self.do_redo)
        self.toolbar.addAction(self.action_redo)

        self.toolbar.addSeparator()
        
        self.action_add_node = QAction("➕ Add Point", self)
        self.action_add_node.setToolTip("Add a control point to the curve")
        self.action_add_node.triggered.connect(self.add_midpoint)
        self.toolbar.addAction(self.action_add_node)
        
        self.action_del_node = QAction("➖ Del Point", self)
        self.action_del_node.setToolTip("Delete the selected control point")
        self.action_del_node.triggered.connect(self.delete_selected_node)
        self.toolbar.addAction(self.action_del_node)
        
        self.action_tangent = QAction("🔷 Tangents ON", self)
        self.action_tangent.setToolTip("Toggle tangent handle visibility")
        self.action_tangent.triggered.connect(self.toggle_tangents)
        self.toolbar.addAction(self.action_tangent)

        self.toolbar.addSeparator()

        self.action_help = QAction("❓ Help", self)
        self.action_help.setToolTip("Open online documentation")
        self.action_help.triggered.connect(lambda: webbrowser.open(HELP_URL))
        self.toolbar.addAction(self.action_help)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        self.splitter_main = QSplitter(Qt.Horizontal)
        
        # Sidebar
        self.sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.preset_list = ReorderableListWidget()
        self.preset_list.setViewMode(QListWidget.IconMode)
        self.preset_list.setIconSize(QSize(100, 100))
        self.preset_list.setGridSize(QSize(120, 140))
        self.preset_list.setResizeMode(QListWidget.Adjust)
        self.preset_list.setSpacing(5)
        self.preset_list.setMovement(QListWidget.Snap)
        self.preset_list.setDragDropMode(QListWidget.InternalMove)
        self.preset_list.setDefaultDropAction(Qt.MoveAction)
        self.preset_list.setWordWrap(True)
        self.preset_list.itemClicked.connect(self.on_preset_selected)
        self.preset_list.itemDoubleClicked.connect(self.rename_selected_preset)
        self.preset_list.set_reorder_callback(self._on_preset_order_changed)
        sidebar_layout.addWidget(self.preset_list)
        
        # Preset controls
        ctrl_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_current_preset)
        self.del_btn = QPushButton("🗑 Delete")
        self.del_btn.clicked.connect(self.delete_selected_preset)
        ctrl_layout.addWidget(self.save_btn)
        ctrl_layout.addWidget(self.del_btn)
        sidebar_layout.addLayout(ctrl_layout)

        # Import / Export
        io_layout = QHBoxLayout()
        self.import_btn = QPushButton("📥 Import")
        self.import_btn.clicked.connect(self.import_presets)
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.clicked.connect(self.export_presets)
        io_layout.addWidget(self.import_btn)
        io_layout.addWidget(self.export_btn)
        sidebar_layout.addLayout(io_layout)

        self.graph_widget = QWidget()
        graph_layout = QVBoxLayout(self.graph_widget)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        
        self.graph_editor = BezierGraphEditor()
        graph_layout.addWidget(self.graph_editor)
        
        # Mini Mode Overlay
        self.mini_overlay = QWidget()
        mo_layout = QVBoxLayout(self.mini_overlay)
        mo_layout.setContentsMargins(0, 5, 0, 0)
        
        btn_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setMaximumWidth(40)
        self.btn_prev.clicked.connect(self.prev_preset)
        self.btn_preset_name = QPushButton("Preset Name")
        self.btn_preset_name.clicked.connect(self.open_preset_dialog)
        self.btn_next = QPushButton("▶")
        self.btn_next.setMaximumWidth(40)
        self.btn_next.clicked.connect(self.next_preset)
        btn_layout.addWidget(self.btn_prev)
        btn_layout.addWidget(self.btn_preset_name)
        btn_layout.addWidget(self.btn_next)
        mo_layout.addLayout(btn_layout)

        mini_actions_layout = QHBoxLayout()
        btn_fit = QPushButton("⛶ Fit")
        btn_fit.clicked.connect(self.fit_graph)
        btn_undo_m = QPushButton("⟵")
        btn_undo_m.clicked.connect(self.do_undo)
        btn_redo_m = QPushButton("⟶")
        btn_redo_m.clicked.connect(self.do_redo)
        btn_add = QPushButton("➕")
        btn_add.clicked.connect(self.add_midpoint)
        btn_tan = QPushButton("🔷")
        btn_tan.clicked.connect(self.toggle_tangents)
        btn_expand = QPushButton("🔳 Exit")
        btn_expand.clicked.connect(self.toggle_mini_mode)
        mini_actions_layout.addWidget(btn_fit)
        mini_actions_layout.addWidget(btn_undo_m)
        mini_actions_layout.addWidget(btn_redo_m)
        mini_actions_layout.addWidget(btn_add)
        mini_actions_layout.addWidget(btn_tan)
        mini_actions_layout.addWidget(btn_expand)
        mo_layout.addLayout(mini_actions_layout)
        
        self.mini_overlay.hide()
        graph_layout.addWidget(self.mini_overlay)

        self.splitter_main.addWidget(self.sidebar_widget)
        self.splitter_main.addWidget(self.graph_widget)
        self.splitter_main.setSizes([300, 500])
        self.main_layout.addWidget(self.splitter_main, stretch=1)
        
        # Info Panel
        self.bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(self.bottom_panel)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.info_label = QLabel("No selection fetched from Cascadeur.")
        bottom_layout.addWidget(self.info_label)
        self.main_layout.addWidget(self.bottom_panel)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(80)
        self.main_layout.addWidget(self.log_text)

        self.refresh_preset_list()

    # ── Undo / Redo ───────────────────────────

    def do_undo(self):
        if self.graph_editor.undo():
            self.graph_editor.set_tangents_visible(self._tangents_visible)

    def do_redo(self):
        if self.graph_editor.redo():
            self.graph_editor.set_tangents_visible(self._tangents_visible)

    # ── Preset display ────────────────────────

    def fit_graph(self):
        self.graph_editor.fit_to_view()

    def refresh_preset_list(self):
        self.preset_list.clear()
        presets = self.preset_manager.get_all_presets()
        for name, data in presets.items():
            pixmap = BezierGraphEditor.generate_thumbnail(data, 100, 100)
            item = QListWidgetItem(QIcon(pixmap), name)
            self.preset_list.addItem(item)
        self.update_mini_preset_label()

    def on_preset_selected(self, item):
        name = item.text()
        presets = self.preset_manager.get_all_presets()
        if name in presets:
            self.graph_editor.load_preset(presets[name])
            self.graph_editor.set_tangents_visible(self._tangents_visible)
            self.current_preset_index = list(presets.keys()).index(name)
            self.update_mini_preset_label()

    def _on_preset_order_changed(self):
        names = []
        for i in range(self.preset_list.count()):
            item = self.preset_list.item(i)
            if item:
                names.append(item.text())
        if names:
            self.preset_manager.save_order(names)

    def save_current_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Enter preset name:")
        if ok and name:
            data = self.graph_editor.get_current_data()
            self.preset_manager.add_custom_preset(name, data)
            self.refresh_preset_list()

    def rename_selected_preset(self):
        item = self.preset_list.currentItem()
        if not item:
            return
        old_name = item.text()
        if old_name not in self.preset_manager.custom_presets:
            self.log_message(f"'{old_name}' is a default preset and cannot be renamed.")
            return
        new_name, ok = QInputDialog.getText(self, "Rename Preset", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            data = self.preset_manager.custom_presets[old_name]
            self.preset_manager.add_custom_preset(new_name, data)
            self.preset_manager.remove_custom_preset(old_name)
            self.refresh_preset_list()

    def delete_selected_preset(self):
        item = self.preset_list.currentItem()
        if item:
            name = item.text()
            if name not in self.preset_manager.custom_presets:
                self.log_message(f"'{name}' is a default preset and cannot be deleted.")
                return
            self.preset_manager.remove_custom_preset(name)
            self.refresh_preset_list()

    # ── Import / Export ───────────────────────

    def import_presets(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Presets", "", "JSON Files (*.json)")
        if not path:
            return
        # Ask overwrite or append
        reply = QMessageBox.question(
            self, "Import Mode",
            "Overwrite existing custom presets?\n\n"
            "Yes = Replace all custom presets\n"
            "No = Add new presets only (skip duplicates)",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.No
        )
        if reply == QMessageBox.Cancel:
            return
        try:
            added, skipped = self.preset_manager.import_presets(
                path, overwrite=(reply == QMessageBox.Yes))
            self.refresh_preset_list()
            self.log_message(f"Imported: {added} added, {skipped} skipped.")
        except Exception as e:
            self.log_message(f"Import failed: {e}")

    def export_presets(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Presets", "easing_presets.json", "JSON Files (*.json)")
        if not path:
            return
        try:
            self.preset_manager.export_presets(path)
            self.log_message(f"Exported to: {path}")
        except Exception as e:
            self.log_message(f"Export failed: {e}")

    # ── Mini Mode ─────────────────────────────

    def toggle_mini_mode(self):
        self.is_mini_mode = not self.is_mini_mode
        self.sidebar_widget.setVisible(not self.is_mini_mode)
        self.bottom_panel.setVisible(not self.is_mini_mode)
        self.log_text.setVisible(not self.is_mini_mode)
        self.mini_overlay.setVisible(self.is_mini_mode)
        if self.is_mini_mode:
            self._normal_geometry = self.geometry()
            self.resize(350, 450)
            self.toolbar.hide()
        else:
            self.toolbar.show()
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            else:
                self.resize(850, 600)
        self.fit_graph()

    def prev_preset(self):
        keys = list(self.preset_manager.get_all_presets().keys())
        if not keys:
            return
        self.current_preset_index = (self.current_preset_index - 1) % len(keys)
        name = keys[self.current_preset_index]
        self.graph_editor.load_preset(self.preset_manager.get_all_presets()[name])
        self.graph_editor.set_tangents_visible(self._tangents_visible)
        self.update_mini_preset_label()

    def next_preset(self):
        keys = list(self.preset_manager.get_all_presets().keys())
        if not keys:
            return
        self.current_preset_index = (self.current_preset_index + 1) % len(keys)
        name = keys[self.current_preset_index]
        self.graph_editor.load_preset(self.preset_manager.get_all_presets()[name])
        self.graph_editor.set_tangents_visible(self._tangents_visible)
        self.update_mini_preset_label()
        
    def update_mini_preset_label(self):
        keys = list(self.preset_manager.get_all_presets().keys())
        if keys and 0 <= self.current_preset_index < len(keys):
            self.btn_preset_name.setText(keys[self.current_preset_index])

    def open_preset_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Preset")
        dlg_layout = QVBoxLayout(dlg)
        list_clone = QListWidget()
        list_clone.setViewMode(QListWidget.IconMode)
        list_clone.setIconSize(QSize(100, 100))
        list_clone.setResizeMode(QListWidget.Adjust)
        presets = self.preset_manager.get_all_presets()
        for name, data in presets.items():
            pixmap = BezierGraphEditor.generate_thumbnail(data, 100, 100)
            list_clone.addItem(QListWidgetItem(QIcon(pixmap), name))
        def clicked(item):
            name = item.text()
            self.graph_editor.load_preset(presets[name])
            self.graph_editor.set_tangents_visible(self._tangents_visible)
            self.current_preset_index = list(presets.keys()).index(name)
            self.update_mini_preset_label()
            dlg.accept()
        list_clone.itemClicked.connect(clicked)
        dlg_layout.addWidget(list_clone)
        dlg.resize(400, 300)
        dlg.exec()

    # ── Tool actions ──────────────────────────

    def log_message(self, msg):
        self.log_text.append(msg)
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def add_midpoint(self):
        self.graph_editor.add_midpoint_at_center()
        self.log_message("Midpoint added. Drag to adjust.")

    def delete_selected_node(self):
        if self.graph_editor.delete_selected_anchor():
            self.log_message("Midpoint deleted.")
        else:
            self.log_message("No deletable midpoint selected (start/end cannot be deleted).")

    def toggle_tangents(self):
        self._tangents_visible = not self._tangents_visible
        self.graph_editor.set_tangents_visible(self._tangents_visible)
        label = "ON" if self._tangents_visible else "OFF"
        self.action_tangent.setText(f"🔷 Tangents {label}")

    # ── TCP communication ─────────────────────

    def handle_incoming_data(self, data_packet):
        client = data_packet.get("client")
        payload = data_packet.get("payload", {})
        cmd = payload.get("command")
        
        if cmd == "ACTIVATE":
            # Bring window to front (single instance support)
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
            self.raise_()
            self.activateWindow()
            return

        if cmd == "FETCH_RESULT":
            self.active_fetch_data = payload
            s = payload.get("frame_start", 0)
            e = payload.get("frame_end", 0)
            self.info_label.setText(f"Selection: Frames {s}-{e} | {len(payload.get('layers', []))} Layers")
            self.info_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif cmd == "REQUEST_CURVE":
            self.handle_request_curve(client, payload)

    def handle_request_curve(self, client, payload):
        try:
            start = payload.get("frame_start")
            end = payload.get("frame_end")
            if start is None:
                start = self.active_fetch_data.get("frame_start", 0) if self.active_fetch_data else 0
            if end is None:
                end = self.active_fetch_data.get("frame_end", 0) if self.active_fetch_data else 0
            frame_count = max(1, end - start)
            data = self.graph_editor.get_current_data()
            comp = CompositeBezier([BezierSegment(*seg) for seg in data])
            table = generate_easing_table(comp, frame_count)
            self.server.send_response(client, {
                "command": "CURVE_DATA",
                "frame_start": start,
                "frame_end": end,
                "easing_table": table,
                "allow_overshoot": True,
            })
        except Exception as e:
            self.log_message(f"Error: {e}")
            import traceback
            self.log_message(traceback.format_exc())
            self.server.send_response(client, {
                "command": "ERROR",
                "message": f"{e}"
            })
