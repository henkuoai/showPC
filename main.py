import sys
import psutil
import time
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon

class MonitorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("系统监控悬浮窗")
        self.resize(220, 100)

        self.label = QLabel()
        self.label.setStyleSheet("color: white; font-size: 14px; background: rgba(0,0,0,0.7); padding: 10px; border-radius: 10px;")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.last_bytes = psutil.net_io_counters().bytes_recv
        self.last_time = time.time()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_info)
        self.timer.start(1000)

        self.update_info()

        # 拖动相关变量
        self._is_dragging = False
        self._drag_pos = None

        # 右键菜单
        self.context_menu = QMenu(self)
        quit_action = QAction("退出软件", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        self.context_menu.addAction(quit_action)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.context_menu.exec_(event.globalPos())
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            event.accept()

    def update_info(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        now_bytes = psutil.net_io_counters().bytes_recv
        now_time = time.time()
        speed = (now_bytes - self.last_bytes) / (now_time - self.last_time) / 1024  # KB/s
        self.last_bytes = now_bytes
        self.last_time = now_time

        self.label.setText(
            f"CPU利用率: {cpu:.1f}%\n"
            f"内存利用率: {mem:.1f}%\n"
            f"下载速度: {speed:.1f} KB/s"
        )

class SystemTray(QSystemTrayIcon):
    def __init__(self, widget, app):
        super().__init__(QIcon("icon.ico"), app)
        self.widget = widget
        self.app = app

        menu = QMenu()
        show_action = QAction("显示悬浮窗")
        quit_action = QAction("退出")
        menu.addAction(show_action)
        menu.addAction(quit_action)
        show_action.triggered.connect(self.show_widget)
        quit_action.triggered.connect(app.quit)
        self.setContextMenu(menu)
        self.activated.connect(self.on_activated)

    def show_widget(self):
        self.widget.show()

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.widget.isVisible():
                self.widget.hide()
            else:
                self.widget.show()

def main():
    app = QApplication(sys.argv)
    widget = MonitorWidget()
    tray = SystemTray(widget, app)
    tray.show()
    widget.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()