# Author: 417_Butter
import sys
import os
import socket
import traceback
import datetime
import ctypes  # 追加: Windowsタスクバー用
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon  # 追加: アイコン読み込み用
from easing_bridge_app import EasingBridgeApp

def resource_path(relative_path):
    """PyInstallerでexe化した場合と、通常実行時の両方で正しいファイルの場所を取得する"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_executable_dir():
    """exe化された場合、一時フォルダではなくexe本体と同じディレクトリを取得する(ログ保存用)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# ── Error log ─────────────────────────────────
# 修正: exe化した時に見えない一時フォルダにログが作られるのを防ぐ
LOG_DIR = get_executable_dir()
ERROR_LOG = os.path.join(LOG_DIR, "error.log")

def setup_error_logging():
    """Global exception handler that writes to error.log for user bug reports."""
    def handler(exc_type, exc_value, exc_tb):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        entry = f"\n{'='*60}\n[{timestamp}] UNHANDLED EXCEPTION\n{tb_text}"
        try:
            with open(ERROR_LOG, "a", encoding="utf-8") as f:
                f.write(entry)
            # Trim log if too large (keep last 200KB)
            if os.path.getsize(ERROR_LOG) > 200_000:
                with open(ERROR_LOG, "r", encoding="utf-8") as f:
                    content = f.read()
                with open(ERROR_LOG, "w", encoding="utf-8") as f:
                    f.write(content[-100_000:])
        except Exception:
            pass
        # Print to console too
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = handler

def is_already_running(port=65432):
    """Check if another instance is already listening on the port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            s.connect(('127.0.0.1', port))
            # Send ACTIVATE command to bring existing window to front
            import struct, json
            payload = json.dumps({"command": "ACTIVATE"}).encode('utf-8')
            s.sendall(struct.pack(">I", len(payload)) + payload)
            s.close()
        return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False

def main():
    # 追加: Windowsタスクバーに正しいアイコンを表示させるためのおまじない
    try:
        myappid = '417_Butter.EasingBridge.App.1_0' # 任意のID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    setup_error_logging()

    # Single instance check
    if is_already_running():
        # Existing instance will bring itself to front
        sys.exit(0)

    app = QApplication(sys.argv)

    # 追加: ここでアプリのアイコンを設定する
    icon_path = resource_path('icon.ico')
    app.setWindowIcon(QIcon(icon_path))

    app.setStyle("Fusion")
    
    dark_stylesheet = """
    QMainWindow, QWidget {
        background-color: #2b2b2b;
        color: #e0e0e0;
    }
    QTextEdit {
        background-color: #1e1e1e;
        color: #a9b7c6;
        border: 1px solid #3c3f41;
    }
    QPushButton {
        background-color: #3c3f41;
        border: 1px solid #555555;
        padding: 5px;
        border-radius: 3px;
    }
    QPushButton:hover {
        background-color: #4b4f53;
    }
    QPushButton:disabled {
        background-color: #2b2b2b;
        color: #555555;
    }
    QSplitter::handle {
        background-color: #3c3f41;
    }
    """
    app.setStyleSheet(dark_stylesheet)
    
    window = EasingBridgeApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()