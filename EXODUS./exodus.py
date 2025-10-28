import sys
import os
import pty
import select
import subprocess
import struct
import fcntl
import termios
import re
import json
import resources_rc
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QLineEdit, 
                             QVBoxLayout, QWidget, QAction, QFileDialog, QMessageBox,
                             QDialog, QTextBrowser, QPushButton, QHBoxLayout, QLabel)
from PyQt5.QtGui import QFont, QTextCursor, QKeySequence, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
class PTYThread(QThread):
    """Поток для чтения из псевдотерминала"""
    output_received = pyqtSignal(bytes)
    
    def __init__(self, master_fd):
        super().__init__()
        self.master_fd = master_fd
        self.running = True
    
    def run(self):
        """Читаем вывод из PTY"""
        while self.running:
            try:
                r, w, e = select.select([self.master_fd], [], [], 0.1)
                if r:
                    data = os.read(self.master_fd, 4096)
                    if data:
                        self.output_received.emit(data)
                    else:
                        break
            except (OSError, ValueError):
                break
    
    def stop(self):
        self.running = False

class CommandHistoryDialog(QDialog):
    """Диалог для просмотра истории команд"""
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command History")
        self.setGeometry(200, 200, 600, 400)
        self.selected_command = None
        
        layout = QVBoxLayout()
        
        label = QLabel("Command History (double-click to use):")
        layout.addWidget(label)
        
        self.history_browser = QTextBrowser()
        self.history_browser.setFont(QFont('Courier New', 10))
        
        # Форматируем историю
        history_text = ""
        for i, cmd in enumerate(reversed(history), 1):
            history_text += f"{i}. {cmd}\n"
        
        self.history_browser.setPlainText(history_text)
        self.history_browser.textCursor().clearSelection()
        layout.addWidget(self.history_browser)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self.clear_history)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Применяем темную тему
        self.setStyleSheet("""
            QDialog {
                background-color: #000;
                color: #00FF00;
            }
            QLabel, QTextBrowser {
                background-color: #001100;
                color: #00FF00;
                border: 1px solid #00FF00;
            }
            QPushButton {
                background-color: #001100;
                color: #00FF00;
                border: 2px solid #00FF00;
                padding: 5px 15px;
                font-family: 'Courier New';
            }
            QPushButton:hover {
                background-color: #003300;
            }
        """)
    
    def clear_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear command history?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.history_browser.clear()
            self.accept()

class HackerTerminal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.master_fd = None
        self.slave_fd = None
        self.pty_thread = None
        self.shell_process = None
        self.color_scheme = 'green'
        self.command_history = []
        self.history_index = -1
        self.temp_command = ""
        self.session_commands = []  # Команды текущей сессии
        self.start_time = datetime.now()
        self.command_count = 0
        
        # Загружаем историю из файла
        self.load_history()
        
        self.initUI()
        self.start_shell()
        
        # Таймер для автосохранения
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.save_history)
        self.autosave_timer.start(60000)  # Каждую минуту
    
    def initUI(self):
        self.setWindowTitle('EXODUS')
        self.setGeometry(100, 100, 900, 650)
        self.setWindowIcon(QIcon(":/icon.png"))  # иконка из встроенного ресурса
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        layout.addWidget(self.terminal_output)
        
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.send_command)
        self.command_input.installEventFilter(self)
        self.command_input.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.command_input)
        
        self.create_menu()
        self.apply_color_scheme()
        
        self.show_welcome_banner()
        self.command_input.setFocus()
    
    def show_welcome_banner(self):
        """Показать приветственный баннер"""
        banner = [
            "=" * 91,
            "███████╗██╗  ██╗ ██████╗ ██████╗ ██╗   ██╗███████╗",
            "██╔════╝╚██╗██╔╝██╔═══██╗██╔══██╗██║   ██║██╔════╝",
            "█████╗   ╚███╔╝ ██║   ██║██║  ██║██║   ██║███████╗",
            "██╔══╝   ██╔██╗ ██║   ██║██║  ██║██║   ██║╚════██║",
            "███████╗██╔╝ ██╗╚██████╔╝██████╔╝╚██████╔╝███████║",
            "╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝",
            "                                                  ",
            "=" * 91,
            "",
            "🔥 Features:",
            "  • PTY Shell Support",
            "  • Command History (↑/↓)",
            "  • Destructive Command Protection",
            "  • Auto-completion (Tab)",
            "  • Session Statistics",
            "",
            "📌 Shortcuts:",
            "  Ctrl+C: Interrupt | Ctrl+D: EOF | Ctrl+L: Clear",
            "  Ctrl+H: History | Ctrl+Shift+C/V: Copy/Paste",
            "",
        ]
        for line in banner:
            self.terminal_output.append(line)
    
    def create_menu(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu('File')
        
        new_tab = QAction('New Terminal Window', self)
        new_tab.setShortcut(QKeySequence('Ctrl+N'))
        new_tab.triggered.connect(self.new_window)
        file_menu.addAction(new_tab)
        
        file_menu.addSeparator()
        
        save_output = QAction('Save Output...', self)
        save_output.setShortcut(QKeySequence('Ctrl+S'))
        save_output.triggered.connect(self.save_terminal_output)
        file_menu.addAction(save_output)
        
        save_session = QAction('Save Session Log...', self)
        save_session.triggered.connect(self.save_session_log)
        file_menu.addAction(save_session)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence('Ctrl+Q'))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu('Edit')
        
        copy_action = QAction('Copy', self)
        copy_action.setShortcut(QKeySequence('Ctrl+Shift+C'))
        copy_action.triggered.connect(self.copy_selection)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction('Paste', self)
        paste_action.setShortcut(QKeySequence('Ctrl+Shift+V'))
        paste_action.triggered.connect(self.paste_text)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        history_action = QAction('Command History...', self)
        history_action.setShortcut(QKeySequence('Ctrl+H'))
        history_action.triggered.connect(self.show_history_dialog)
        edit_menu.addAction(history_action)
        
        edit_menu.addSeparator()
        
        clear_action = QAction('Clear Terminal', self)
        clear_action.setShortcut(QKeySequence('Ctrl+Shift+K'))
        clear_action.triggered.connect(self.clear_terminal)
        edit_menu.addAction(clear_action)
        
        select_all = QAction('Select All', self)
        select_all.setShortcut(QKeySequence('Ctrl+Shift+A'))
        select_all.triggered.connect(self.terminal_output.selectAll)
        edit_menu.addAction(select_all)
        
        # View Menu
        view_menu = menubar.addMenu('View')
        
        green_scheme = QAction('Matrix Green', self)
        green_scheme.triggered.connect(lambda: self.change_color_scheme('green'))
        view_menu.addAction(green_scheme)
        
        amber_scheme = QAction('Amber', self)
        amber_scheme.triggered.connect(lambda: self.change_color_scheme('amber'))
        view_menu.addAction(amber_scheme)
        
        blue_scheme = QAction('Blue', self)
        blue_scheme.triggered.connect(lambda: self.change_color_scheme('blue'))
        view_menu.addAction(blue_scheme)
        
        red_scheme = QAction('Red', self)
        red_scheme.triggered.connect(lambda: self.change_color_scheme('red'))
        view_menu.addAction(red_scheme)
        
        view_menu.addSeparator()
        
        stats_action = QAction('Session Statistics', self)
        stats_action.setShortcut(QKeySequence('Ctrl+I'))
        stats_action.triggered.connect(self.show_session_stats)
        view_menu.addAction(stats_action)
        
        view_menu.addSeparator()
        
        zoom_in = QAction('Zoom In', self)
        zoom_in.setShortcut(QKeySequence('Ctrl++'))
        zoom_in.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in)
        
        zoom_out = QAction('Zoom Out', self)
        zoom_out.setShortcut(QKeySequence('Ctrl+-'))
        zoom_out.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out)
        
        reset_zoom = QAction('Reset Zoom', self)
        reset_zoom.setShortcut(QKeySequence('Ctrl+0'))
        reset_zoom.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom)
        
        # Help Menu
        help_menu = menubar.addMenu('Help')
        
        shortcuts_action = QAction('Keyboard Shortcuts', self)
        shortcuts_action.setShortcut(QKeySequence('F1'))
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def apply_color_scheme(self):
        schemes = {
            'green': {'bg': '#000', 'fg': '#00FF00', 'input_bg': '#001100', 'border': '#00FF00'},
            'amber': {'bg': '#000', 'fg': '#FFB000', 'input_bg': '#1A0F00', 'border': '#FFB000'},
            'blue': {'bg': '#000', 'fg': '#00BFFF', 'input_bg': '#000F1A', 'border': '#00BFFF'},
            'red': {'bg': '#000', 'fg': '#FF3333', 'input_bg': '#1A0000', 'border': '#FF3333'}
        }
        c = schemes.get(self.color_scheme, schemes['green'])
        style = f"""
            QMainWindow {{ background-color: {c['bg']}; }}
            QTextEdit {{
                background-color: {c['bg']};
                color: {c['fg']};
                border: none;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                padding: 10px;
                selection-background-color: #333;
            }}
            QLineEdit {{
                background-color: {c['input_bg']};
                color: {c['fg']};
                border: 2px solid {c['border']};
                font-family: 'Courier New', monospace;
                font-size: 14px;
                padding: 5px;
            }}
            QMenuBar {{
                background-color: {c['bg']};
                color: {c['fg']};
                border-bottom: 1px solid {c['border']};
            }}
            QMenuBar::item:selected {{
                background-color: {c['input_bg']};
            }}
            QMenu {{
                background-color: {c['bg']};
                color: {c['fg']};
                border: 1px solid {c['border']};
            }}
            QMenu::item:selected {{
                background-color: {c['input_bg']};
            }}
        """
        self.setStyleSheet(style)
    
    def change_color_scheme(self, scheme):
        self.color_scheme = scheme
        self.apply_color_scheme()

    def is_destructive(self, cmd: str) -> bool:
        """Проверка опасных команд"""
        s = cmd.strip().lower()
        if not s:
            return False
        
        # Опасные паттерны
        patterns = [
            r'\brm\b.*(-rf|--recursive|--force).*[/\*]',  # rm -rf
            r':\s*\(\s*\)\s*\{.*\}\s*;',  # fork bomb
            r'\bmkfs\b',  # форматирование
            r'\bdd\b.*if=.*of=/dev/',  # запись на диск
            r'\bwipefs\b',
            r'\bshred\b',
            r'\bparted\b',
            r'\bfdisk\b.*-w',
            r'>\s*/dev/sd[a-z]',  # запись напрямую на диск
        ]
        
        for pattern in patterns:
            if re.search(pattern, s):
                return True
        
        return False
    
    def send_command(self):
        if self.master_fd is None:
            return
        
        text = self.command_input.text()
        self.command_input.clear()

        # Пустая команда
        if not text.strip():
            try:
                os.write(self.master_fd, b'\n')
            except Exception:
                pass
            return

        # Добавляем в историю
        if not self.command_history or self.command_history[-1] != text:
            self.command_history.append(text)
            self.session_commands.append({
                'command': text,
                'time': datetime.now().strftime('%H:%M:%S')
            })
        
        self.history_index = len(self.command_history)
        self.temp_command = ""
        self.command_count += 1

        # Проверка опасных команд
        try:
            if self.is_destructive(text):
                reply = QMessageBox.question(
                    self,
                    "⚠️ Dangerous Command Detected",
                    f"This command appears to be potentially destructive:\n\n"
                    f"Command: {text}\n\n"
                    f"Are you absolutely sure you want to execute it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    self.terminal_output.append("\n[EXODUS] Command cancelled by user.\n")
                    return
            
            os.write(self.master_fd, (text + '\n').encode('utf-8'))
        except Exception as e:
            self.terminal_output.append(f"\nERROR: {str(e)}\n")

    def on_text_changed(self, text):
        """Подсказки при вводе команд"""
        # Можно добавить автодополнение или подсказки
        pass

    def eventFilter(self, obj, event):
        if obj == self.command_input and event.type() == event.KeyPress:
            # История команд - стрелка вверх
            if event.key() == Qt.Key_Up:
                if self.command_history:
                    if self.history_index == len(self.command_history):
                        self.temp_command = self.command_input.text()
                    if self.history_index > 0:
                        self.history_index -= 1
                        self.command_input.setText(self.command_history[self.history_index])
                return True
            
            # История команд - стрелка вниз
            if event.key() == Qt.Key_Down:
                if self.command_history:
                    if self.history_index < len(self.command_history) - 1:
                        self.history_index += 1
                        self.command_input.setText(self.command_history[self.history_index])
                    elif self.history_index == len(self.command_history) - 1:
                        self.history_index = len(self.command_history)
                        self.command_input.setText(self.temp_command)
                return True
            
            # Ctrl+C - SIGINT
            if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
                self.send_signal(b'\x03')
                return True
            
            # Ctrl+D - EOF
            if event.key() == Qt.Key_D and event.modifiers() == Qt.ControlModifier:
                if not self.command_input.text():
                    self.send_signal(b'\x04')
                return True
            
            # Ctrl+Z - SIGTSTP
            if event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
                self.send_signal(b'\x1a')
                return True
            
            # Ctrl+L - очистка
            if event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
                self.send_signal(b'\x0c')
                return True
            
            # Tab - автодополнение
            if event.key() == Qt.Key_Tab:
                text = self.command_input.text()
                cursor_pos = self.command_input.cursorPosition()
                self.send_input(text[:cursor_pos].encode('utf-8') + b'\t')
                return True
        
        return super().eventFilter(obj, event)

    def start_shell(self):
        try:
            self.master_fd, self.slave_fd = pty.openpty()
            self.update_terminal_size()
            
            env = os.environ.copy()
            env['TERM'] = 'xterm-256color'
            env['COLORTERM'] = 'truecolor'
            
            self.shell_process = subprocess.Popen(
                ['/bin/bash', '-i'],
                stdin=self.slave_fd,
                stdout=self.slave_fd,
                stderr=self.slave_fd,
                env=env,
                start_new_session=True
            )
            os.close(self.slave_fd)
            
            self.pty_thread = PTYThread(self.master_fd)
            self.pty_thread.output_received.connect(self.handle_output)
            self.pty_thread.start()
        except Exception as e:
            self.terminal_output.append(f"ERROR starting shell: {str(e)}")

    def update_terminal_size(self):
        if self.master_fd is None:
            return
        try:
            fm = self.terminal_output.fontMetrics()
            cols = max(20, self.terminal_output.viewport().width() // fm.averageCharWidth())
            rows = max(10, self.terminal_output.viewport().height() // fm.height())
            size = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_terminal_size()

    def handle_output(self, data):
        try:
            text = data.decode('utf-8', errors='replace')
            # Удаляем ANSI escape последовательности
            text = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', text)
            text = re.sub(r'\x1b\][0-9;]*[^\x07\x1b]*[\x07\x1b]', '', text)
            text = re.sub(r'\x1b[^\x1b]*[\x07\x1b\\]', '', text)
            
            scrollbar = self.terminal_output.verticalScrollBar()
            at_bottom = scrollbar.value() == scrollbar.maximum()
            
            self.terminal_output.insertPlainText(text)
            self.terminal_output.moveCursor(QTextCursor.End)
            
            if at_bottom:
                scrollbar.setValue(scrollbar.maximum())
            
            # Ограничение буфера
            doc = self.terminal_output.document()
            if doc.blockCount() > 2000:
                cursor = QTextCursor(doc)
                cursor.movePosition(QTextCursor.Start)
                cursor.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor, 500)
                cursor.removeSelectedText()
        except Exception:
            pass

    def send_input(self, data):
        if self.master_fd:
            try:
                os.write(self.master_fd, data)
            except Exception:
                pass

    def send_signal(self, signal):
        self.send_input(signal)
        self.command_input.clear()

    def copy_selection(self):
        self.terminal_output.copy()
    
    def paste_text(self):
        self.command_input.insert(QApplication.clipboard().text())
    
    def clear_terminal(self):
        self.send_input(b'\x0c')

    def new_window(self):
        """Открыть новое окно терминала"""
        new_terminal = HackerTerminal()
        new_terminal.show()

    def show_history_dialog(self):
        """Показать историю команд"""
        dialog = CommandHistoryDialog(self.command_history, self)
        dialog.exec_()

    def show_session_stats(self):
        """Показать статистику сессии"""
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        stats = f"""
<h2>Session Statistics</h2>
<table style='color: #00FF00; font-family: Courier New;'>
<tr><td><b>Session Start:</b></td><td>{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
<tr><td><b>Uptime:</b></td><td>{int(hours)}h {int(minutes)}m {int(seconds)}s</td></tr>
<tr><td><b>Commands Executed:</b></td><td>{self.command_count}</td></tr>
<tr><td><b>History Size:</b></td><td>{len(self.command_history)} commands</td></tr>
<tr><td><b>Current Directory:</b></td><td>{os.getcwd()}</td></tr>
<tr><td><b>Terminal Size:</b></td><td>{self.terminal_output.viewport().width()}x{self.terminal_output.viewport().height()}px</td></tr>
</table>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Session Statistics")
        msg.setTextFormat(Qt.RichText)
        msg.setText(stats)
        msg.exec_()

    def show_shortcuts(self):
        """Показать клавиатурные сокращения"""
        shortcuts = """
<h2>Keyboard Shortcuts</h2>
<table style='color: #00FF00; font-family: Courier New;'>
<tr><td><b>Ctrl+C</b></td><td>Send interrupt signal (SIGINT)</td></tr>
<tr><td><b>Ctrl+D</b></td><td>Send EOF signal</td></tr>
<tr><td><b>Ctrl+Z</b></td><td>Suspend process (SIGTSTP)</td></tr>
<tr><td><b>Ctrl+L</b></td><td>Clear screen</td></tr>
<tr><td><b>Tab</b></td><td>Auto-complete command</td></tr>
<tr><td><b>↑/↓</b></td><td>Navigate command history</td></tr>
<tr><td><b>Ctrl+H</b></td><td>Show command history dialog</td></tr>
<tr><td><b>Ctrl+Shift+C</b></td><td>Copy selected text</td></tr>
<tr><td><b>Ctrl+Shift+V</b></td><td>Paste text</td></tr>
<tr><td><b>Ctrl+Shift+K</b></td><td>Clear terminal</td></tr>
<tr><td><b>Ctrl+N</b></td><td>New terminal window</td></tr>
<tr><td><b>Ctrl+S</b></td><td>Save terminal output</td></tr>
<tr><td><b>Ctrl+I</b></td><td>Show session statistics</td></tr>
<tr><td><b>Ctrl++/-</b></td><td>Zoom in/out</td></tr>
<tr><td><b>Ctrl+0</b></td><td>Reset zoom</td></tr>
<tr><td><b>F1</b></td><td>Show this help</td></tr>
</table>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Keyboard Shortcuts")
        msg.setTextFormat(Qt.RichText)
        msg.setText(shortcuts)
        msg.exec_()

    def save_terminal_output(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Save Output", "", "Text Files (*.txt);;All Files (*)")
        if fn:
            try:
                with open(fn, 'w', encoding='utf-8') as f:
                    f.write(self.terminal_output.toPlainText())
                QMessageBox.information(self, "Saved", "Output saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def save_session_log(self):
        """Сохранить лог сессии с командами"""
        fn, _ = QFileDialog.getSaveFileName(self, "Save Session Log", "", "JSON Files (*.json);;Text Files (*.txt)")
        if fn:
            try:
                if fn.endswith('.json'):
                    log_data = {
                        'session_start': self.start_time.isoformat(),
                        'commands': self.session_commands,
                        'total_commands': self.command_count
                    }
                    with open(fn, 'w', encoding='utf-8') as f:
                        json.dump(log_data, f, indent=2)
                else:
                    with open(fn, 'w', encoding='utf-8') as f:
                        f.write(f"Session Log - {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("=" * 60 + "\n\n")
                        for cmd in self.session_commands:
                            f.write(f"[{cmd['time']}] {cmd['command']}\n")
                
                QMessageBox.information(self, "Saved", "Session log saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def load_history(self):
        """Загрузить историю команд из файла"""
        history_file = os.path.expanduser('~/.exodus_history')
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.command_history = [line.strip() for line in f.readlines() if line.strip()]
        except Exception:
            pass

    def save_history(self):
        """Сохранить историю команд в файл"""
        history_file = os.path.expanduser('~/.exodus_history')
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                # Сохраняем только последние 1000 команд
                for cmd in self.command_history[-1000:]:
                    f.write(cmd + '\n')
        except Exception:
            pass

    def zoom_in(self):
        f = self.terminal_output.font()
        if f.pointSize() < 30:
            f.setPointSize(f.pointSize() + 1)
            self.terminal_output.setFont(f)
            self.command_input.setFont(f)
            self.update_terminal_size()

    def zoom_out(self):
        f = self.terminal_output.font()
        if f.pointSize() > 8:
            f.setPointSize(f.pointSize() - 1)
            self.terminal_output.setFont(f)
            self.command_input.setFont(f)
            self.update_terminal_size()

    def reset_zoom(self):
        f = self.terminal_output.font()
        f.setPointSize(14)
        self.terminal_output.setFont(f)
        self.command_input.setFont(f)
        self.update_terminal_size()

    def show_about(self):
        about_text = """
<h2 style='color: #00FF00;'>EXODUS Terminal v1.0</h2>
<p style='color: #00FF00; font-family: Courier New;'>
Advanced terminal emulator with PTY support and enhanced features.
</p>
<p style='color: #00FF00;'><b>Features:</b></p>
<ul style='color: #00FF00;'>
<li>Full PTY terminal emulation</li>
<li>Command history with persistence</li>
<li>Destructive command protection</li>
<li>Session statistics and logging</li>
<li>Multiple color schemes</li>
<li>Auto-completion support</li>
<li>Signal handling (Ctrl+C, Ctrl+Z, etc.)</li>
</ul>
<p style='color: #00FF00;'>
<b>Created with PyQt5</b><br>
Press F1 for keyboard shortcuts
</p>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("About EXODUS Terminal")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        
        # Применяем тёмную тему к диалогу
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #000;
                color: #00FF00;
            }
            QLabel {
                color: #00FF00;
            }
            QPushButton {
                background-color: #001100;
                color: #00FF00;
                border: 2px solid #00FF00;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #003300;
            }
        """)
        msg.exec_()

    def closeEvent(self, event):
        # Сохраняем историю перед выходом
        self.save_history()
        
        # Останавливаем таймер
        self.autosave_timer.stop()
        
        # Закрываем поток
        if self.pty_thread:
            self.pty_thread.stop()
            self.pty_thread.wait()
        
        # Закрываем PTY
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except:
                pass
        
        # Завершаем процесс shell
        if self.shell_process:
            try:
                self.shell_process.terminate()
                self.shell_process.wait(timeout=1)
            except:
                try:
                    self.shell_process.kill()
                except:
                    pass
        
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    terminal = HackerTerminal()
    terminal.show()
    sys.exit(app.exec_())
