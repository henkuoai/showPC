import sys
import psutil
import time
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QSystemTrayIcon, QMenu, QAction, QMessageBox,
                             QInputDialog, QDialog, QFileDialog)
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QScreen
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal
import keyboard
import pyperclip
from PIL import ImageGrab
import io


class ScreenshotThread(QThread):
    screenshot_taken = pyqtSignal(object)  # 发送截图数据
    
    def __init__(self):
        super().__init__()
        self.is_running = True
        
    def run(self):
        # 监听快捷键
        keyboard.add_hotkey('ctrl+shift+s', self.take_screenshot)
        keyboard.wait()
        
    def take_screenshot(self):
        try:
            # 使用PIL截图
            screenshot = ImageGrab.grab()
            
            # 转换为QPixmap
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            
            # 发送信号
            self.screenshot_taken.emit(pixmap)
            
        except Exception as e:
            print(f"截图失败: {e}")
    
    def stop(self):
        self.is_running = False
        keyboard.unhook_all()
        self.quit()


class ReminderDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("久坐提醒")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 150)

        # 创建半透明背景
        self.background = QLabel(self)
        self.background.setStyleSheet("background: rgba(50, 50, 50, 200); border-radius: 10px;")
        self.background.setGeometry(0, 0, 300, 150)

        # 创建消息标签
        self.message_label = QLabel(message, self)
        self.message_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setGeometry(20, 30, 260, 60)

        # 创建确认按钮
        self.ok_button = QLabel("知道了", self)
        self.ok_button.setStyleSheet("""
            background: rgba(70, 130, 180, 200); 
            color: white; 
            font-size: 14px; 
            padding: 8px; 
            border-radius: 5px;
        """)
        self.ok_button.setAlignment(Qt.AlignCenter)
        self.ok_button.setGeometry(110, 100, 80, 30)
        self.ok_button.mousePressEvent = self.accept

        # 添加淡入动画
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(500)
        self.animation.setStartValue(QPoint(self.x(), self.y() - 50))
        self.animation.setEndValue(QPoint(self.x(), self.y()))
        self.animation.finished.connect(self.show)

    def showEvent(self, event):
        self.animation.start()
        super().showEvent(event)

    def accept(self, event=None):
        self.close()
        super().accept()


class ScreenshotResultDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.setWindowTitle("截图结果")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # 显示截图预览
        self.image_label = QLabel()
        scaled_pixmap = pixmap.scaled(380, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)
        
        # 按钮布局
        button_layout = QVBoxLayout()
        
        # 复制到剪贴板按钮
        copy_button = QLabel("复制到剪贴板")
        copy_button.setStyleSheet("""
            background: rgba(70, 130, 180, 200); 
            color: white; 
            font-size: 14px; 
            padding: 8px; 
            border-radius: 5px;
            margin: 5px;
        """)
        copy_button.setAlignment(Qt.AlignCenter)
        copy_button.mousePressEvent = self.copy_to_clipboard
        
        # 保存到本地按钮
        save_button = QLabel("保存到本地")
        save_button.setStyleSheet("""
            background: rgba(70, 130, 180, 200); 
            color: white; 
            font-size: 14px; 
            padding: 8px; 
            border-radius: 5px;
            margin: 5px;
        """)
        save_button.setAlignment(Qt.AlignCenter)
        save_button.mousePressEvent = self.save_to_local
        
        # 关闭按钮
        close_button = QLabel("关闭")
        close_button.setStyleSheet("""
            background: rgba(150, 150, 150, 200); 
            color: white; 
            font-size: 14px; 
            padding: 8px; 
            border-radius: 5px;
            margin: 5px;
        """)
        close_button.setAlignment(Qt.AlignCenter)
        close_button.mousePressEvent = self.close
        
        button_layout.addWidget(copy_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def copy_to_clipboard(self, event=None):
        try:
            # 将QPixmap转换为PIL Image
            buffer = io.BytesIO()
            self.pixmap.save(buffer, "PNG")
            buffer.seek(0)
            
            # 复制到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.pixmap)
            
            QMessageBox.information(self, "成功", "截图已复制到剪贴板！")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"复制失败: {e}")
    
    def save_to_local(self, event=None):
        try:
            # 生成默认文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"screenshot_{timestamp}.png"
            
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "保存截图", 
                default_filename, 
                "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
            )
            
            if file_path:
                # 保存图片
                self.pixmap.save(file_path)
                QMessageBox.information(self, "成功", f"截图已保存到: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")


class MonitorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("系统监控悬浮窗")
        self.resize(220, 140)

        self.label = QLabel()
        self.label.setStyleSheet("""
            color: white; 
            font-size: 12px; 
            background: rgba(0,0,0,0.7); 
            padding: 10px; 
            border-radius: 10px;
        """)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # 初始化网络统计
        self.last_bytes_recv = psutil.net_io_counters().bytes_recv
        self.last_bytes_sent = psutil.net_io_counters().bytes_sent
        self.last_time = time.time()

        # 久坐提醒设置（默认60分钟）
        self.reminder_interval = 60 * 60  # 秒
        self.last_reminder_time = time.time()
        self.next_reminder_time = time.time() + self.reminder_interval
        self.is_reminder_active = False

        # 主定时器（每秒更新）
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_info)
        self.timer.start(1000)

        # 拖动功能
        self._is_dragging = False
        self._drag_pos = None

        # 右键菜单
        self.context_menu = QMenu(self)
        reminder_config_action = QAction("久坐提醒设置", self)
        quit_action = QAction("退出软件", self)
        reminder_config_action.triggered.connect(self.config_reminder)
        quit_action.triggered.connect(QApplication.instance().quit)
        self.context_menu.addAction(reminder_config_action)
        self.context_menu.addSeparator()
        self.context_menu.addAction(quit_action)

        # 初始化截图功能
        self.screenshot_thread = ScreenshotThread()
        self.screenshot_thread.screenshot_taken.connect(self.show_screenshot_result)
        self.screenshot_thread.start()

    def show_screenshot_result(self, pixmap):
        """显示截图结果对话框"""
        dialog = ScreenshotResultDialog(pixmap, self)
        dialog.exec_()

    def closeEvent(self, event):
        """关闭事件处理"""
        if hasattr(self, 'screenshot_thread'):
            self.screenshot_thread.stop()
        event.accept()

    def config_reminder(self):
        minutes, ok = QInputDialog.getInt(
            self,
            "久坐提醒设置",
            "请输入提醒间隔时间（分钟）:",
            self.reminder_interval // 60,
            1,  # 最小值
            240,  # 最大值（4小时）
            1  # 步长
        )
        if ok:
            self.reminder_interval = minutes * 60
            self.last_reminder_time = time.time()
            self.next_reminder_time = time.time() + self.reminder_interval
            self.is_reminder_active = False

    def show_reminder(self):
        if not self.is_reminder_active:
            self.is_reminder_active = True

            # 创建并显示提醒对话框
            message = f"您已经坐了{self.reminder_interval // 60}分钟了，该起来活动一下了！"
            self.reminder_dialog = ReminderDialog(message, self)

            # 定位对话框在悬浮窗上方
            dialog_pos = self.mapToGlobal(QPoint(0, 0)) - QPoint(0, 160)
            self.reminder_dialog.move(dialog_pos)

            # 显示对话框并重置提醒时间
            self.reminder_dialog.exec_()

            # 重置提醒时间
            self.last_reminder_time = time.time()
            self.next_reminder_time = time.time() + self.reminder_interval
            self.is_reminder_active = False

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
        # 获取系统信息
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        # 计算网络速度（带异常保护）
        now = time.time()
        time_diff = now - self.last_time

        # 时间差过大时（如系统唤醒）重置基准值
        if time_diff > 5:
            self.last_bytes_recv = psutil.net_io_counters().bytes_recv
            self.last_bytes_sent = psutil.net_io_counters().bytes_sent
            self.last_time = now
            return

        now_bytes_recv = psutil.net_io_counters().bytes_recv
        now_bytes_sent = psutil.net_io_counters().bytes_sent

        dl_speed = (now_bytes_recv - self.last_bytes_recv) / time_diff / 1024
        ul_speed = (now_bytes_sent - self.last_bytes_sent) / time_diff / 1024

        self.last_bytes_recv = now_bytes_recv
        self.last_bytes_sent = now_bytes_sent
        self.last_time = now

        # 检查久坐提醒
        current_time = time.time()
        if current_time >= self.next_reminder_time and not self.is_reminder_active:
            self.show_reminder()

        # 计算倒计时
        countdown = max(0, self.next_reminder_time - current_time)
        minutes = int(countdown // 60)
        seconds = int(countdown % 60)

        # 更新显示
        self.label.setText(
            f"CPU: {cpu:.1f}% | MEM: {mem:.1f}%\n"
            f"↓: {dl_speed:.1f} KB/s | ↑: {ul_speed:.1f} KB/s\n"
            f"久坐提醒: {minutes:02d}:{seconds:02d}\n"
            f"下次提醒: {time.strftime('%H:%M', time.localtime(self.next_reminder_time))}"
        )


class SystemTray(QSystemTrayIcon):
    def __init__(self, widget, app):
        # 创建默认图标（如果文件不存在）
        try:
            icon = QIcon("icon.ico")
            if icon.isNull():
                raise Exception("自定义图标不存在")
        except:
            # 创建简单的程序图标
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor(70, 130, 180))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 32, 32)
            painter.setFont(QFont("Arial", 14))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "M")
            painter.end()
            icon = QIcon(pixmap)

        super().__init__(icon, app)
        self.widget = widget
        self.app = app

        menu = QMenu()
        show_action = QAction("显示/隐藏悬浮窗")
        config_action = QAction("久坐提醒设置")
        quit_action = QAction("退出")

        menu.addAction(show_action)
        menu.addAction(config_action)
        menu.addAction(quit_action)

        show_action.triggered.connect(self.toggle_widget)
        config_action.triggered.connect(self.widget.config_reminder)
        quit_action.triggered.connect(app.quit)

        self.setContextMenu(menu)
        self.activated.connect(self.on_activated)

        # 添加气泡提示
        self.showMessage("系统监控", "监控程序已启动", QSystemTrayIcon.Information, 2000)

    def toggle_widget(self):
        if self.widget.isVisible():
            self.widget.hide()
        else:
            self.widget.show()

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # 左键单击
            self.toggle_widget()


def main():
    app = QApplication(sys.argv)

    # 设置应用名称（用于任务管理器识别）
    app.setApplicationName("SystemMonitor")
    app.setApplicationDisplayName("系统监控")

    widget = MonitorWidget()
    tray = SystemTray(widget, app)

    # 将系统托盘引用传递给主窗口
    widget.tray = tray

    tray.show()
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()