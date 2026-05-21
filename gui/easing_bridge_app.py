# Author: 417_Butter
import json
import os
import webbrowser

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QSplitter, QTabWidget, QTextEdit, QToolBar, QVBoxLayout, QWidget,
)

from curve_math import BezierSegment, CompositeBezier, generate_easing_table
from graph_editor import BezierGraphEditor
from preset_manager import PresetManager
from tcp_server import EasingBridgeServer

HELP_URL = "https://github.com/417-Butter/417_easing_bridge"
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

UNDO_ICON = "\u21a9"
REDO_ICON = "\u21aa"
STAR_ON = "\u2605"
STAR_OFF = "\u2606"

UI_ICONS = {
    "fit": "\u26f6",
    "mini": "\u25a3",
    "add_point": "+",
    "del_point": "-",
    "tangents": "\u25c7",
    "help": "?",
    "save": "\u25a3",
    "delete": "x",
    "import": "\u2193",
    "export": "\u2191",
}

LANGUAGES = {
    "en": "English",
    "ja": "\u65e5\u672c\u8a9e",
    "zh": "\u4e2d\u6587",
    "ko": "\ud55c\uad6d\uc5b4",
}


def _help_html(lang):
    if lang == "ja":
        return (
            "<b>\u25a0 \u4f7f\u3044\u65b9</b><br>"
            "1. Cascadeur\u3067\u5bfe\u8c61\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u3068\u30d5\u30ec\u30fc\u30e0\u7bc4\u56f2\u3092\u9078\u629e\u3057\u307e\u3059\u3002<br>"
            "2. \u3053\u306eEasing Bridge GUI\u3067\u30ab\u30fc\u30d6\u3092\u8abf\u6574\u3057\u307e\u3059\u3002<br>"
            "3. Cascadeur\u3067 <b>Ctrl+B</b> / <b>Cmd+B</b> \u3092\u62bc\u3057\u3066\u30ab\u30fc\u30d6\u3092Bake\u3057\u307e\u3059\u3002<br>"
            "&nbsp;&nbsp;&nbsp;(\u307e\u305f\u306f Menu bar > Commands > Easing Bridge_417 > Bake)<br><br>"
            "<b>\u25a0 \u30b7\u30e7\u30fc\u30c8\u30ab\u30c3\u30c8</b><br>"
            "\u2022 <b>Ctrl+B</b> / <b>Cmd+B</b> (Cascadeur): \u30ab\u30fc\u30d6\u3092Bake<br>"
            "\u2022 <b>\u30c0\u30d6\u30eb\u30af\u30ea\u30c3\u30af</b> (\u30b0\u30e9\u30d5): \u5236\u5fa1\u70b9\u3092\u8ffd\u52a0<br>"
            "\u2022 <b>Alt+\u30af\u30ea\u30c3\u30af</b> (\u30a2\u30f3\u30ab\u30fc): \u30bf\u30f3\u30b8\u30a7\u30f3\u30c8\u3092\u30ea\u30bb\u30c3\u30c8<br>"
            "\u2022 <b>Shift+\u30c9\u30e9\u30c3\u30b0</b> (\u30bf\u30f3\u30b8\u30a7\u30f3\u30c8): \u5bfe\u79f0\u30df\u30e9\u30fc<br>"
            "\u2022 <b>Alt+\u30c9\u30e9\u30c3\u30b0</b> (\u30bf\u30f3\u30b8\u30a7\u30f3\u30c8): X\u8ef8\u30df\u30e9\u30fc (V\u5b57)<br>"
            "\u2022 <b>\u30de\u30a6\u30b9\u30db\u30a4\u30fc\u30eb</b>: \u62e1\u5927/\u7e2e\u5c0f<br>"
            "\u2022 <b>\u80cc\u666f\u30c9\u30e9\u30c3\u30b0</b>: \u30d3\u30e5\u30fc\u3092\u79fb\u52d5<br>"
        )
    if lang == "zh":
        return (
            "<b>\u25a0 \u4f7f\u7528\u65b9\u6cd5</b><br>"
            "1. \u5728 Cascadeur \u4e2d\u9009\u62e9\u5bf9\u8c61\u548c\u5e27\u8303\u56f4\u3002<br>"
            "2. \u5728\u8fd9\u4e2a Easing Bridge GUI \u4e2d\u8bbe\u8ba1\u66f2\u7ebf\u3002<br>"
            "3. \u5728 Cascadeur \u4e2d\u6309 <b>Ctrl+B</b> / <b>Cmd+B</b> \u6765 Bake \u66f2\u7ebf\u3002<br>"
            "&nbsp;&nbsp;&nbsp;(\u6216 Menu bar > Commands > Easing Bridge_417 > Bake)<br><br>"
            "<b>\u25a0 \u5feb\u6377\u952e</b><br>"
            "\u2022 <b>Ctrl+B</b> / <b>Cmd+B</b> (Cascadeur): Bake \u66f2\u7ebf<br>"
            "\u2022 <b>\u53cc\u51fb</b> (\u56fe\u8868): \u6dfb\u52a0\u63a7\u5236\u70b9<br>"
            "\u2022 <b>Alt+\u70b9\u51fb</b> (\u951a\u70b9): \u91cd\u7f6e\u5207\u7ebf<br>"
            "\u2022 <b>Shift+\u62d6\u52a8</b> (\u5207\u7ebf): \u5bf9\u79f0\u955c\u50cf<br>"
            "\u2022 <b>Alt+\u62d6\u52a8</b> (\u5207\u7ebf): X\u8f74\u955c\u50cf (V\u5f62)<br>"
            "\u2022 <b>\u9f20\u6807\u6eda\u8f6e</b>: \u653e\u5927/\u7f29\u5c0f<br>"
            "\u2022 <b>\u62d6\u52a8\u80cc\u666f</b>: \u5e73\u79fb\u89c6\u56fe<br>"
        )
    if lang == "ko":
        return (
            "<b>\u25a0 \uc0ac\uc6a9 \ubc29\ubc95</b><br>"
            "1. Cascadeur\uc5d0\uc11c \ub300\uc0c1 \uc624\ube0c\uc81d\ud2b8\uc640 \ud504\ub808\uc784 \ubc94\uc704\ub97c \uc120\ud0dd\ud569\ub2c8\ub2e4.<br>"
            "2. \uc774 Easing Bridge GUI\uc5d0\uc11c \ucee4\ube0c\ub97c \ub514\uc790\uc778\ud569\ub2c8\ub2e4.<br>"
            "3. Cascadeur\uc5d0\uc11c <b>Ctrl+B</b> / <b>Cmd+B</b>\ub97c \ub20c\ub7ec \ucee4\ube0c\ub97c Bake\ud569\ub2c8\ub2e4.<br>"
            "&nbsp;&nbsp;&nbsp;(\ub610\ub294 Menu bar > Commands > Easing Bridge_417 > Bake)<br><br>"
            "<b>\u25a0 \ub2e8\ucd95\ud0a4</b><br>"
            "\u2022 <b>Ctrl+B</b> / <b>Cmd+B</b> (Cascadeur): \ucee4\ube0c Bake<br>"
            "\u2022 <b>\ub354\ube14 \ud074\ub9ad</b> (\uadf8\ub798\ud504): \uc81c\uc5b4\uc810 \ucd94\uac00<br>"
            "\u2022 <b>Alt+\ud074\ub9ad</b> (\uc575\ucee4): \ud0c4\uc820\ud2b8 \ub9ac\uc14b<br>"
            "\u2022 <b>Shift+\ub4dc\ub798\uadf8</b> (\ud0c4\uc820\ud2b8): \ub300\uce6d \ubbf8\ub7ec<br>"
            "\u2022 <b>Alt+\ub4dc\ub798\uadf8</b> (\ud0c4\uc820\ud2b8): X\ucd95 \ubbf8\ub7ec (V \ubaa8\uc591)<br>"
            "\u2022 <b>\ub9c8\uc6b0\uc2a4 \ud720</b>: \ud655\ub300/\ucd95\uc18c<br>"
            "\u2022 <b>\ubc30\uacbd \ub4dc\ub798\uadf8</b>: \ubdf0 \uc774\ub3d9<br>"
        )
    return (
        "<b>\u25a0 How to Use</b><br>"
        "1. Select the objects and the frame interval in Cascadeur.<br>"
        "2. Design your curve here in the Easing Bridge GUI.<br>"
        "3. Press <b>Ctrl+B</b> / <b>Cmd+B</b> in Cascadeur to bake the curve.<br>"
        "&nbsp;&nbsp;&nbsp;(or Menu bar > Commands > Easing Bridge_417 > Bake)<br><br>"
        "<b>\u25a0 Shortcuts</b><br>"
        "\u2022 <b>Ctrl+B</b> / <b>Cmd+B</b> (Cascadeur): Bake curve<br>"
        "\u2022 <b>Double-Click</b> (Graph): Add control point<br>"
        "\u2022 <b>Alt+Click</b> (Anchor): Reset tangents<br>"
        "\u2022 <b>Shift+Drag</b> (Tangent): Symmetric mirror<br>"
        "\u2022 <b>Alt+Drag</b> (Tangent): X-Axis mirror (V-shape)<br>"
        "\u2022 <b>Mouse Wheel</b>: Zoom in/out<br>"
        "\u2022 <b>Drag Background</b>: Pan view<br>"
    )


TRANSLATIONS = {
    "en": {
        "fit": "Fit", "mini": "Mini", "exit": "Exit", "add_point": "Add Point",
        "del_point": "Del Point", "tangents": "Tangents", "help": "Help",
        "initial_presets": "Initial Presets", "user_presets": "User Presets",
        "favorites": "Favorites", "save": "Save", "delete": "Delete",
        "import": "Import", "export": "Export", "no_presets": "No Presets",
        "select_preset": "Select Preset", "help_title": "How to Use & Shortcuts",
        "more": "More... (Open Browser)", "close": "Close",
        "default_no_delete": "Default presets cannot be deleted.",
        "default_no_rename": "'{name}' is a default preset and cannot be renamed.",
        "default_name_exists": "'{name}' is a default preset name. Please choose another name.",
    },
    "ja": {
        "fit": "\u30d5\u30a3\u30c3\u30c8", "mini": "Mini", "exit": "\u623b\u308b",
        "add_point": "\u30dd\u30a4\u30f3\u30c8\u8ffd\u52a0", "del_point": "\u30dd\u30a4\u30f3\u30c8\u524a\u9664",
        "tangents": "\u30bf\u30f3\u30b8\u30a7\u30f3\u30c8", "help": "\u30d8\u30eb\u30d7",
        "initial_presets": "\u521d\u671f\u30d7\u30ea\u30bb\u30c3\u30c8", "user_presets": "\u30e6\u30fc\u30b6\u30fc\u30d7\u30ea\u30bb\u30c3\u30c8",
        "favorites": "\u304a\u6c17\u306b\u5165\u308a", "save": "\u4fdd\u5b58", "delete": "\u524a\u9664",
        "import": "\u8aad\u307f\u8fbc\u307f", "export": "\u66f8\u304d\u51fa\u3057", "no_presets": "\u30d7\u30ea\u30bb\u30c3\u30c8\u306a\u3057",
        "select_preset": "\u30d7\u30ea\u30bb\u30c3\u30c8\u9078\u629e", "help_title": "\u4f7f\u3044\u65b9\u3068\u30b7\u30e7\u30fc\u30c8\u30ab\u30c3\u30c8",
        "more": "\u8a73\u3057\u304f\u898b\u308b\uff08\u30d6\u30e9\u30a6\u30b6\uff09", "close": "\u9589\u3058\u308b",
        "default_no_delete": "\u521d\u671f\u30d7\u30ea\u30bb\u30c3\u30c8\u306f\u524a\u9664\u3067\u304d\u307e\u305b\u3093\u3002",
        "default_no_rename": "'{name}' \u306f\u521d\u671f\u30d7\u30ea\u30bb\u30c3\u30c8\u306a\u306e\u3067\u540d\u524d\u5909\u66f4\u3067\u304d\u307e\u305b\u3093\u3002",
        "default_name_exists": "'{name}' \u306f\u521d\u671f\u30d7\u30ea\u30bb\u30c3\u30c8\u540d\u3067\u3059\u3002\u5225\u306e\u540d\u524d\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
    },
    "zh": {
        "fit": "\u9002\u914d", "mini": "Mini", "exit": "\u9000\u51fa", "add_point": "\u6dfb\u52a0\u70b9",
        "del_point": "\u5220\u9664\u70b9", "tangents": "\u5207\u7ebf", "help": "\u5e2e\u52a9",
        "initial_presets": "\u521d\u59cb\u9884\u8bbe", "user_presets": "\u7528\u6237\u9884\u8bbe",
        "favorites": "\u6536\u85cf", "save": "\u4fdd\u5b58", "delete": "\u5220\u9664",
        "import": "\u5bfc\u5165", "export": "\u5bfc\u51fa", "no_presets": "\u65e0\u9884\u8bbe",
        "select_preset": "\u9009\u62e9\u9884\u8bbe", "help_title": "\u4f7f\u7528\u65b9\u6cd5\u4e0e\u5feb\u6377\u952e",
        "more": "\u66f4\u591a...\uff08\u6253\u5f00\u6d4f\u89c8\u5668\uff09", "close": "\u5173\u95ed",
        "default_no_delete": "\u521d\u59cb\u9884\u8bbe\u4e0d\u80fd\u5220\u9664\u3002",
        "default_no_rename": "'{name}' \u662f\u521d\u59cb\u9884\u8bbe\uff0c\u4e0d\u80fd\u91cd\u547d\u540d\u3002",
        "default_name_exists": "'{name}' \u662f\u521d\u59cb\u9884\u8bbe\u540d\u79f0\u3002\u8bf7\u4f7f\u7528\u5176\u4ed6\u540d\u79f0\u3002",
    },
    "ko": {
        "fit": "\ub9de\ucda4", "mini": "Mini", "exit": "\ub098\uac00\uae30", "add_point": "\uc810 \ucd94\uac00",
        "del_point": "\uc810 \uc0ad\uc81c", "tangents": "\ud0c4\uc820\ud2b8", "help": "\ub3c4\uc6c0\ub9d0",
        "initial_presets": "\ucd08\uae30 \ud504\ub9ac\uc14b", "user_presets": "\uc0ac\uc6a9\uc790 \ud504\ub9ac\uc14b",
        "favorites": "\uc990\uaca8\ucc3e\uae30", "save": "\uc800\uc7a5", "delete": "\uc0ad\uc81c",
        "import": "\uac00\uc838\uc624\uae30", "export": "\ub0b4\ubcf4\ub0b4\uae30", "no_presets": "\ud504\ub9ac\uc14b \uc5c6\uc74c",
        "select_preset": "\ud504\ub9ac\uc14b \uc120\ud0dd", "help_title": "\uc0ac\uc6a9 \ubc29\ubc95\uacfc \ub2e8\ucd95\ud0a4",
        "more": "\ub354 \ubcf4\uae30... (\ube0c\ub77c\uc6b0\uc800)", "close": "\ub2eb\uae30",
        "default_no_delete": "\ucd08\uae30 \ud504\ub9ac\uc14b\uc740 \uc0ad\uc81c\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.",
        "default_no_rename": "'{name}'\uc740 \ucd08\uae30 \ud504\ub9ac\uc14b\uc774\ub77c \uc774\ub984\uc744 \ubc14\uafc0 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.",
        "default_name_exists": "'{name}'\uc740 \ucd08\uae30 \ud504\ub9ac\uc14b \uc774\ub984\uc785\ub2c8\ub2e4. \ub2e4\ub978 \uc774\ub984\uc744 \uc785\ub825\ud574 \uc8fc\uc138\uc694.",
    },
}


def create_text_icon(text, font_size=18, color=Qt.white, size=32):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    font = painter.font()
    font.setPointSize(font_size)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(color)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
    painter.end()
    return QIcon(pixmap)


def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class PresetListWidget(QListWidget):
    def __init__(self, group, favorite_callback, parent=None):
        super().__init__(parent)
        self.group = group
        self.favorite_callback = favorite_callback

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            rect = self.visualItemRect(item)
            star_rect = rect.adjusted(4, 4, -rect.width() + 28, -rect.height() + 28)
            if star_rect.contains(event.pos()):
                self.favorite_callback(item.data(Qt.UserRole), self.group)
                event.accept()
                return
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        # IconModeのデフォルトスクロール量が大きすぎるので制限
        scroll_bar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        step = 40  # 1回あたりのスクロール量(px)
        if delta > 0:
            scroll_bar.setValue(scroll_bar.value() - step)
        else:
            scroll_bar.setValue(scroll_bar.value() + step)
        event.accept()


class EasingBridgeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("417_Easing Bridge v0.9.1")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.server = EasingBridgeServer(self, port=65432)
        self.server.status_message.connect(self.log_message)
        self.server.data_received.connect(self.handle_incoming_data)

        self.preset_manager = PresetManager()
        self.active_fetch_data = None
        self.is_mini_mode = False
        self.current_preset_group = "default"
        self.current_preset_index = 0
        self._tangents_visible = True
        self._normal_geometry = None
        self.language = "en"
        self.help_dialog = None

        self.setup_ui()
        self._restore_settings()
        self.server.start()

    def tr(self, key):
        return TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

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
            "graph_view": self.graph_editor.get_view_state(),
            "language": self.language,
        }
        save_settings(data)

    def _restore_settings(self):
        settings = load_settings()
        if not settings:
            self.resize(850, 600)
            return

        self.language = settings.get("language", "en")
        combo_index = self.language_combo.findData(self.language)
        if combo_index >= 0:
            self.language_combo.setCurrentIndex(combo_index)
        self.apply_language()

        self.setGeometry(settings.get("x", 100), settings.get("y", 100), settings.get("width", 850), settings.get("height", 600))
        self._normal_geometry = self.geometry()

        self._tangents_visible = settings.get("tangents_visible", True)
        self.graph_editor.set_tangents_visible(self._tangents_visible)
        self.update_tangent_label()

        splitter_sizes = settings.get("splitter")
        if splitter_sizes:
            self.splitter_main.setSizes(splitter_sizes)

        if settings.get("mini_mode", False):
            self.toggle_mini_mode()

        graph_view = settings.get("graph_view")
        if graph_view:
            QTimer.singleShot(0, lambda: self.graph_editor.set_view_state(graph_view))

    def setup_ui(self):
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(34, 34))
        self.addToolBar(self.toolbar)

        self.action_fit = QAction(self.tr("fit"), self)
        self.action_fit.triggered.connect(self.fit_graph)
        self.toolbar.addAction(self.action_fit)

        self.action_mini = QAction(self.tr("mini"), self)
        self.action_mini.triggered.connect(self.toggle_mini_mode)
        self.toolbar.addAction(self.action_mini)

        self.toolbar.addSeparator()

        self.action_undo = QAction(create_text_icon(UNDO_ICON, 28, size=48), "Undo", self)
        self.action_undo.setToolTip("Undo last graph edit")
        self.action_undo.triggered.connect(self.do_undo)
        self.toolbar.addAction(self.action_undo)

        self.action_redo = QAction(create_text_icon(REDO_ICON, 28, size=48), "Redo", self)
        self.action_redo.setToolTip("Redo last undone edit")
        self.action_redo.triggered.connect(self.do_redo)
        self.toolbar.addAction(self.action_redo)

        self.toolbar.addSeparator()

        self.action_add_node = QAction(self.tr("add_point"), self)
        self.action_add_node.setToolTip("Add a control point to the curve (Double-click on graph)")
        self.action_add_node.triggered.connect(self.add_midpoint)
        self.toolbar.addAction(self.action_add_node)

        self.action_del_node = QAction(self.tr("del_point"), self)
        self.action_del_node.setToolTip("Delete the selected control point")
        self.action_del_node.triggered.connect(self.delete_selected_node)
        self.toolbar.addAction(self.action_del_node)

        self.action_tangent = QAction("", self)
        self.action_tangent.setToolTip("Toggle tangent handle visibility")
        self.action_tangent.triggered.connect(self.toggle_tangents)
        self.toolbar.addAction(self.action_tangent)

        self.toolbar.addSeparator()

        self.action_help = QAction(self.tr("help"), self)
        self.action_help.setToolTip("Open documentation & shortcuts")
        self.action_help.triggered.connect(self.show_help_dialog)
        self.toolbar.addAction(self.action_help)

        self.toolbar.addSeparator()
        self.language_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        self.toolbar.addWidget(self.language_combo)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.splitter_main = QSplitter(Qt.Horizontal)
        self.sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        self.preset_tabs = QTabWidget()
        self.default_preset_list = self._create_preset_list("default")
        self.custom_preset_list = self._create_preset_list("custom")
        self.favorite_preset_list = self._create_preset_list("favorite")
        self.preset_tabs.addTab(self.default_preset_list, self.tr("initial_presets"))
        self.preset_tabs.addTab(self.custom_preset_list, self.tr("user_presets"))
        self.preset_tabs.addTab(self.favorite_preset_list, self.tr("favorites"))
        self.preset_tabs.currentChanged.connect(self._on_preset_tab_changed)
        sidebar_layout.addWidget(self.preset_tabs)

        ctrl_layout = QHBoxLayout()
        self.save_btn = QPushButton(self.tr("save"))
        self.save_btn.clicked.connect(self.save_current_preset)
        self.del_btn = QPushButton(self.tr("delete"))
        self.del_btn.clicked.connect(self.delete_selected_preset)
        ctrl_layout.addWidget(self.save_btn)
        ctrl_layout.addWidget(self.del_btn)
        sidebar_layout.addLayout(ctrl_layout)

        io_layout = QHBoxLayout()
        self.import_btn = QPushButton(self.tr("import"))
        self.import_btn.clicked.connect(self.import_presets)
        self.export_btn = QPushButton(self.tr("export"))
        self.export_btn.clicked.connect(self.export_presets)
        io_layout.addWidget(self.import_btn)
        io_layout.addWidget(self.export_btn)
        sidebar_layout.addLayout(io_layout)

        self.graph_widget = QWidget()
        graph_layout = QVBoxLayout(self.graph_widget)
        graph_layout.setContentsMargins(0, 0, 0, 0)

        self.graph_editor = BezierGraphEditor()
        graph_layout.addWidget(self.graph_editor)

        self.mini_overlay = QWidget()
        mo_layout = QVBoxLayout(self.mini_overlay)
        mo_layout.setContentsMargins(0, 5, 0, 0)

        btn_layout = QHBoxLayout()
        self.btn_prev = QPushButton("<")
        self.btn_prev.setMaximumWidth(40)
        self.btn_prev.setFocusPolicy(Qt.NoFocus)
        self.btn_prev.clicked.connect(self.prev_preset)

        self.btn_preset_name = QPushButton("Preset Name")
        self.btn_preset_name.setFocusPolicy(Qt.NoFocus)
        self.btn_preset_name.clicked.connect(self.open_preset_dialog)

        self.btn_next = QPushButton(">")
        self.btn_next.setMaximumWidth(40)
        self.btn_next.setFocusPolicy(Qt.NoFocus)
        self.btn_next.clicked.connect(self.next_preset)

        btn_layout.addWidget(self.btn_prev)
        btn_layout.addWidget(self.btn_preset_name)
        btn_layout.addWidget(self.btn_next)
        mo_layout.addLayout(btn_layout)

        mini_actions_layout = QHBoxLayout()
        self.btn_fit_mini = QPushButton(self.tr("fit"))
        self.btn_fit_mini.setMinimumHeight(42)
        self.btn_fit_mini.setFocusPolicy(Qt.NoFocus)
        self.btn_fit_mini.clicked.connect(self.fit_graph)

        self.btn_undo_m = QPushButton()
        self.btn_undo_m.setIcon(create_text_icon(UNDO_ICON, 30, size=48))
        self.btn_undo_m.setIconSize(QSize(32, 32))
        self.btn_undo_m.setFixedSize(QSize(48, 42))
        self.btn_undo_m.setToolTip("Undo")
        self.btn_undo_m.setFocusPolicy(Qt.NoFocus)
        self.btn_undo_m.clicked.connect(self.do_undo)

        self.btn_redo_m = QPushButton()
        self.btn_redo_m.setIcon(create_text_icon(REDO_ICON, 30, size=48))
        self.btn_redo_m.setIconSize(QSize(32, 32))
        self.btn_redo_m.setFixedSize(QSize(48, 42))
        self.btn_redo_m.setToolTip("Redo")
        self.btn_redo_m.setFocusPolicy(Qt.NoFocus)
        self.btn_redo_m.clicked.connect(self.do_redo)

        self.btn_add_mini = QPushButton("+")
        self.btn_add_mini.setMinimumHeight(42)
        self.btn_add_mini.setFocusPolicy(Qt.NoFocus)
        self.btn_add_mini.clicked.connect(self.add_midpoint)

        self.btn_tan_mini = QPushButton("T")
        self.btn_tan_mini.setMinimumHeight(42)
        self.btn_tan_mini.setFocusPolicy(Qt.NoFocus)
        self.btn_tan_mini.clicked.connect(self.toggle_tangents)

        self.btn_expand_mini = QPushButton(self.tr("exit"))
        self.btn_expand_mini.setMinimumHeight(42)
        self.btn_expand_mini.setFocusPolicy(Qt.NoFocus)
        self.btn_expand_mini.clicked.connect(self.toggle_mini_mode)

        mini_actions_layout.addWidget(self.btn_fit_mini)
        mini_actions_layout.addWidget(self.btn_undo_m)
        mini_actions_layout.addWidget(self.btn_redo_m)
        mini_actions_layout.addWidget(self.btn_add_mini)
        mini_actions_layout.addWidget(self.btn_tan_mini)
        mini_actions_layout.addWidget(self.btn_expand_mini)
        mo_layout.addLayout(mini_actions_layout)

        self.mini_overlay.hide()
        graph_layout.addWidget(self.mini_overlay)

        self.splitter_main.addWidget(self.sidebar_widget)
        self.splitter_main.addWidget(self.graph_widget)
        self.splitter_main.setSizes([300, 500])
        self.main_layout.addWidget(self.splitter_main, stretch=1)

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
        self.apply_language()

    def apply_language(self):
        self.action_fit.setText(self.icon_text("fit"))
        self.action_mini.setText(self.icon_text("mini"))
        self.action_add_node.setText(self.icon_text("add_point"))
        self.action_del_node.setText(self.icon_text("del_point"))
        self.action_help.setText(self.icon_text("help"))
        self.preset_tabs.setTabText(0, self.tr("initial_presets"))
        self.preset_tabs.setTabText(1, self.tr("user_presets"))
        self.preset_tabs.setTabText(2, self.tr("favorites"))
        self.save_btn.setText(self.icon_text("save"))
        self.del_btn.setText(self.icon_text("delete"))
        self.import_btn.setText(self.icon_text("import"))
        self.export_btn.setText(self.icon_text("export"))
        self.btn_fit_mini.setText(self.icon_text("fit"))
        self.btn_expand_mini.setText(self.icon_text("mini", self.tr("exit")))
        self.update_tangent_label()
        self.update_mini_preset_label()
        if self.help_dialog and self.help_dialog.isVisible():
            self._populate_help_dialog(self.help_dialog)

    def on_language_changed(self):
        self.language = self.language_combo.currentData() or "en"
        self.apply_language()

    def icon_text(self, key, text=None):
        return f"{UI_ICONS.get(key, '')} {text if text is not None else self.tr(key)}".strip()

    def update_tangent_label(self):
        label = "ON" if self._tangents_visible else "OFF"
        self.action_tangent.setText(f"{UI_ICONS['tangents']} {self.tr('tangents')} {label}")

    def do_undo(self):
        if self.graph_editor.undo():
            self.graph_editor.set_tangents_visible(self._tangents_visible)

    def do_redo(self):
        if self.graph_editor.redo():
            self.graph_editor.set_tangents_visible(self._tangents_visible)

    def fit_graph(self):
        self.graph_editor.fit_to_view()

    def _create_preset_list(self, group):
        preset_list = PresetListWidget(group, self.toggle_preset_favorite)
        preset_list.setProperty("preset_group", group)
        preset_list.setViewMode(QListWidget.IconMode)
        preset_list.setMovement(QListWidget.Static)
        preset_list.setIconSize(QSize(100, 100))
        preset_list.setGridSize(QSize(120, 140))
        preset_list.setResizeMode(QListWidget.Adjust)
        preset_list.setSpacing(5)
        preset_list.setWordWrap(True)
        preset_list.itemClicked.connect(self.on_preset_selected)
        preset_list.itemDoubleClicked.connect(self.rename_selected_preset)
        return preset_list

    def _thumbnail_with_star(self, data, name):
        pixmap = BezierGraphEditor.generate_thumbnail(data, 100, 100)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.TextAntialiasing)
        font = painter.font()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        is_favorite = self.preset_manager.is_favorite(name)
        painter.setPen(Qt.yellow if is_favorite else Qt.lightGray)
        painter.drawText(4, 4, 22, 22, Qt.AlignCenter, STAR_ON if is_favorite else STAR_OFF)
        painter.end()
        return pixmap

    def _populate_preset_list(self, preset_list, presets):
        preset_list.clear()
        for name, data in presets.items():
            item = QListWidgetItem(QIcon(self._thumbnail_with_star(data, name)), name)
            item.setData(Qt.UserRole, name)
            item.setTextAlignment(Qt.AlignCenter)
            preset_list.addItem(item)

    def refresh_preset_list(self):
        self._populate_preset_list(self.default_preset_list, self.preset_manager.get_presets("default"))
        self._populate_preset_list(self.custom_preset_list, self.preset_manager.get_presets("custom"))
        self._populate_preset_list(self.favorite_preset_list, self.preset_manager.get_presets("favorite"))
        self.update_mini_preset_label()

    def _on_preset_tab_changed(self, index):
        if index < 0:
            return
        self.current_preset_group = ["default", "custom", "favorite"][index]
        self.current_preset_index = 0
        self.update_mini_preset_label()

    def _current_presets(self):
        return self.preset_manager.get_presets(self.current_preset_group)

    def _select_preset(self, group, name):
        presets = self.preset_manager.get_presets(group)
        if name not in presets:
            return
        self.current_preset_group = group
        self.preset_tabs.setCurrentIndex({"default": 0, "custom": 1, "favorite": 2}.get(group, 0))
        self.graph_editor.load_preset(presets[name])
        self.graph_editor.set_tangents_visible(self._tangents_visible)
        self.current_preset_index = list(presets.keys()).index(name)
        self.update_mini_preset_label()

    def on_preset_selected(self, item):
        group = item.listWidget().property("preset_group") or self.current_preset_group
        self._select_preset(group, item.data(Qt.UserRole))

    def _on_preset_order_changed(self, group):
        list_widget = {"default": self.default_preset_list, "custom": self.custom_preset_list, "favorite": self.favorite_preset_list}[group]
        names = [list_widget.item(i).data(Qt.UserRole) for i in range(list_widget.count())]
        self.preset_manager.save_order(names, group=group)

    def toggle_preset_favorite(self, name, group=None):
        self.preset_manager.toggle_favorite(name)
        self.refresh_preset_list()
        if group == "favorite" and not self.preset_manager.is_favorite(name):
            self.current_preset_index = 0

    def save_current_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Enter preset name:")
        if ok and name:
            if name in self.preset_manager.get_default_presets():
                self.log_message(self.tr("default_name_exists").format(name=name))
                return
            data = self.graph_editor.get_current_data()
            self.preset_manager.add_custom_preset(name, data)
            self.refresh_preset_list()
            self._select_preset("custom", name)

    def rename_selected_preset(self, item=None):
        if item is not None and item.listWidget().property("preset_group") != "custom":
            self.log_message(self.tr("default_no_rename").format(name=item.data(Qt.UserRole)))
            return
        item = item or self.custom_preset_list.currentItem()
        if not item:
            return
        old_name = item.data(Qt.UserRole)
        if old_name not in self.preset_manager.custom_presets:
            self.log_message(self.tr("default_no_rename").format(name=old_name))
            return
        new_name, ok = QInputDialog.getText(self, "Rename Preset", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            data = self.preset_manager.custom_presets[old_name]
            was_favorite = self.preset_manager.is_favorite(old_name)
            self.preset_manager.add_custom_preset(new_name, data)
            self.preset_manager.remove_custom_preset(old_name)
            if was_favorite:
                self.preset_manager.set_favorite(new_name, True)
            self.refresh_preset_list()
            self._select_preset("custom", new_name)

    def delete_selected_preset(self):
        if self.current_preset_group != "custom":
            self.log_message(self.tr("default_no_delete"))
            return
        item = self.custom_preset_list.currentItem()
        if item:
            name = item.data(Qt.UserRole)
            if name not in self.preset_manager.custom_presets:
                self.log_message(self.tr("default_no_delete"))
                return
            self.preset_manager.remove_custom_preset(name)
            self.refresh_preset_list()

    def import_presets(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Presets", "", "JSON Files (*.json)")
        if not path:
            return
        reply = QMessageBox.question(
            self, "Import Mode",
            "Overwrite existing custom presets?\n\nYes = Replace all custom presets\nNo = Add new presets only (skip duplicates)",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No,
        )
        if reply == QMessageBox.Cancel:
            return
        try:
            added, skipped = self.preset_manager.import_presets(path, overwrite=(reply == QMessageBox.Yes))
            self.refresh_preset_list()
            self.log_message(f"Imported: {added} added, {skipped} skipped.")
        except Exception as e:
            self.log_message(f"Import failed: {e}")

    def export_presets(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Presets", "easing_presets.json", "JSON Files (*.json)")
        if not path:
            return
        try:
            self.preset_manager.export_presets(path)
            self.log_message(f"Exported to: {path}")
        except Exception as e:
            self.log_message(f"Export failed: {e}")

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

    def prev_preset(self):
        presets = self._current_presets()
        keys = list(presets.keys())
        if not keys:
            return
        self.current_preset_index = (self.current_preset_index - 1) % len(keys)
        name = keys[self.current_preset_index]
        self.graph_editor.load_preset(presets[name])
        self.graph_editor.set_tangents_visible(self._tangents_visible)
        self.update_mini_preset_label()

    def next_preset(self):
        presets = self._current_presets()
        keys = list(presets.keys())
        if not keys:
            return
        self.current_preset_index = (self.current_preset_index + 1) % len(keys)
        name = keys[self.current_preset_index]
        self.graph_editor.load_preset(presets[name])
        self.graph_editor.set_tangents_visible(self._tangents_visible)
        self.update_mini_preset_label()

    def update_mini_preset_label(self):
        keys = list(self._current_presets().keys())
        if keys and 0 <= self.current_preset_index < len(keys):
            self.btn_preset_name.setText(keys[self.current_preset_index])
        else:
            self.btn_preset_name.setText(self.tr("no_presets"))

    def open_preset_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("select_preset"))
        dlg_layout = QVBoxLayout(dlg)

        def clicked(item):
            group = item.listWidget().property("preset_group")
            self._select_preset(group, item.data(Qt.UserRole))
            dlg.accept()

        tabs = QTabWidget()
        for group, label_key in (("default", "initial_presets"), ("custom", "user_presets"), ("favorite", "favorites")):
            list_clone = PresetListWidget(group, self.toggle_preset_favorite)
            list_clone.setProperty("preset_group", group)
            list_clone.setViewMode(QListWidget.IconMode)
            list_clone.setIconSize(QSize(100, 100))
            list_clone.setGridSize(QSize(120, 140))
            list_clone.setResizeMode(QListWidget.Adjust)
            list_clone.setWordWrap(True)
            self._populate_preset_list(list_clone, self.preset_manager.get_presets(group))
            list_clone.itemClicked.connect(clicked)
            tabs.addTab(list_clone, self.tr(label_key))
        tabs.setCurrentIndex({"default": 0, "custom": 1, "favorite": 2}.get(self.current_preset_group, 0))
        dlg_layout.addWidget(tabs)
        dlg.resize(420, 320)
        dlg.exec()

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
        self.update_tangent_label()

    def _populate_help_dialog(self, dlg):
        dlg.setWindowTitle(self.tr("help_title"))
        info = dlg.findChild(QLabel, "helpInfo")
        btn_more = dlg.findChild(QPushButton, "helpMore")
        btn_close = dlg.findChild(QPushButton, "helpClose")
        if info:
            info.setText(_help_html(self.language))
        if btn_more:
            btn_more.setText(self.tr("more"))
        if btn_close:
            btn_close.setText(self.tr("close"))

    def show_help_dialog(self):
        if self.help_dialog and self.help_dialog.isVisible():
            self.help_dialog.raise_()
            self.help_dialog.activateWindow()
            return

        dlg = QDialog(self)
        self.help_dialog = dlg
        dlg.setModal(False)
        dlg.setWindowModality(Qt.NonModal)
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        dlg.destroyed.connect(lambda *_: setattr(self, "help_dialog", None))
        layout = QVBoxLayout(dlg)

        info = QLabel()
        info.setObjectName("helpInfo")
        info.setTextFormat(Qt.RichText)
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_more = QPushButton()
        btn_more.setObjectName("helpMore")
        btn_more.clicked.connect(lambda: webbrowser.open(HELP_URL))
        layout.addWidget(btn_more)

        btn_close = QPushButton()
        btn_close.setObjectName("helpClose")
        btn_close.clicked.connect(dlg.close)
        layout.addWidget(btn_close)

        self._populate_help_dialog(dlg)
        dlg.resize(460, 360)
        dlg.show()

    def handle_incoming_data(self, data_packet):
        client = data_packet.get("client")
        payload = data_packet.get("payload", {})
        cmd = payload.get("command")

        if cmd == "ACTIVATE":
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
            self.raise_()
            self.activateWindow()
            return

        if cmd == "FETCH_RESULT":
            self.active_fetch_data = payload
            start = payload.get("frame_start", 0)
            end = payload.get("frame_end", 0)
            self.info_label.setText(f"Selection: Frames {start}-{end} | {len(payload.get('layers', []))} Layers")
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
            
            import sys, os
            gui_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(sys.argv[0]))
            
            self.server.send_response(client, {
                "command": "CURVE_DATA",
                "frame_start": start,
                "frame_end": end,
                "easing_table": table,
                "allow_overshoot": True,
                "gui_dir": gui_dir,
            })
        except Exception as e:
            self.log_message(f"Error: {e}")
            import traceback
            self.log_message(traceback.format_exc())
            self.server.send_response(client, {"command": "ERROR", "message": f"{e}"})
