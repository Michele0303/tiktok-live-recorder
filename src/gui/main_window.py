"""
Main GUI Window for TikTok Live Recorder
"""
import sys
import os
import threading
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QLineEdit, QPushButton, QRadioButton, 
    QButtonGroup, QSpinBox, QCheckBox, QTextEdit, QGroupBox, 
    QFileDialog, QProgressBar, QStatusBar, QTabWidget, QFrame,
    QComboBox, QSplitter, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPixmap, QIcon

# Add the src directory to the path to import from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.args_handler import parse_args
from utils.utils import read_cookies
from utils.logger_manager import logger
from core.tiktok_recorder import TikTokRecorder
from utils.custom_exceptions import TikTokRecorderError
from utils.enums import Mode


class LogHandler(QObject):
    """Custom log handler to emit signals for GUI updates"""
    log_signal = pyqtSignal(str)
    
    def emit(self, message):
        self.log_signal.emit(str(message))


class RecorderWorker(QThread):
    """Worker thread for running the recorder to prevent GUI blocking"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)
    
    def __init__(self, recorder_args):
        super().__init__()
        self.recorder_args = recorder_args
        self.is_running = False
    
    def run(self):
        try:
            self.is_running = True
            self.status_update.emit("Starting recording...")
            
            # Get cookies
            cookies = read_cookies()
            
            # Create recorder instance
            recorder = TikTokRecorder(
                url=self.recorder_args.get('url'),
                user=self.recorder_args.get('user'),
                room_id=self.recorder_args.get('room_id'),
                mode=self.recorder_args.get('mode'),
                automatic_interval=self.recorder_args.get('automatic_interval'),
                cookies=cookies,
                proxy=self.recorder_args.get('proxy'),
                output=self.recorder_args.get('output'),
                duration=self.recorder_args.get('duration'),
                use_telegram=self.recorder_args.get('use_telegram'),
            )
            
            # Run the recorder
            recorder.run()
            
            self.status_update.emit("Recording completed successfully!")
            
        except TikTokRecorderError as ex:
            self.error.emit(f"Application Error: {ex}")
        except Exception as ex:
            self.error.emit(f"Generic Error: {ex}")
        finally:
            self.is_running = False
            self.finished.emit()
    
    def stop(self):
        self.is_running = False
        self.terminate()
        self.wait()


class TikTokRecorderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.recorder_worker = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("TikTok Live Recorder v6.5")
        self.setGeometry(100, 100, 900, 700)
        
        # Set application icon (you can add an icon file later)
        # self.setWindowIcon(QIcon("icon.png"))
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create title
        title_label = QLabel("TikTok Live Recorder")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2E86AB; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Create input section
        input_widget = self.create_input_section()
        splitter.addWidget(input_widget)
        
        # Create output section
        output_widget = self.create_output_section()
        splitter.addWidget(output_widget)
        
        # Set splitter proportions
        splitter.setSizes([400, 300])
        
        # Create status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready to record")
        
        # Apply modern styling
        self.apply_styles()
        
    def create_input_section(self):
        """Create the input configuration section"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create tabs for better organization
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Source Tab
        source_tab = self.create_source_tab()
        tabs.addTab(source_tab, "📺 Source")
        
        # Settings Tab
        settings_tab = self.create_settings_tab()
        tabs.addTab(settings_tab, "⚙️ Settings")
        
        # Advanced Tab
        advanced_tab = self.create_advanced_tab()
        tabs.addTab(advanced_tab, "🔧 Advanced")
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶️ Start Recording")
        self.start_button.clicked.connect(self.start_recording)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        
        self.stop_button = QPushButton("⏹️ Stop Recording")
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        return widget
    
    def create_source_tab(self):
        """Create the source configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Source selection group
        source_group = QGroupBox("Recording Source")
        source_layout = QGridLayout(source_group)
        
        # Radio buttons for source type
        self.source_button_group = QButtonGroup()
        
        self.url_radio = QRadioButton("TikTok Live URL")
        self.url_radio.setChecked(True)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.tiktok.com/@username/live")
        
        self.user_radio = QRadioButton("Username")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("@username or username")
        self.user_input.setEnabled(False)
        
        self.room_id_radio = QRadioButton("Room ID")
        self.room_id_input = QLineEdit()
        self.room_id_input.setPlaceholderText("1234567890123456789")
        self.room_id_input.setEnabled(False)
        
        # Add to button group
        self.source_button_group.addButton(self.url_radio, 0)
        self.source_button_group.addButton(self.user_radio, 1)
        self.source_button_group.addButton(self.room_id_radio, 2)
        
        # Connect radio button signals
        self.url_radio.toggled.connect(lambda checked: self.url_input.setEnabled(checked))
        self.user_radio.toggled.connect(lambda checked: self.user_input.setEnabled(checked))
        self.room_id_radio.toggled.connect(lambda checked: self.room_id_input.setEnabled(checked))
        
        # Add to layout
        source_layout.addWidget(self.url_radio, 0, 0)
        source_layout.addWidget(self.url_input, 0, 1)
        source_layout.addWidget(self.user_radio, 1, 0)
        source_layout.addWidget(self.user_input, 1, 1)
        source_layout.addWidget(self.room_id_radio, 2, 0)
        source_layout.addWidget(self.room_id_input, 2, 1)
        
        layout.addWidget(source_group)
        
        # Recording mode group
        mode_group = QGroupBox("Recording Mode")
        mode_layout = QGridLayout(mode_group)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Manual", "Automatic"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        self.interval_label = QLabel("Check Interval (minutes):")
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1)
        self.interval_spinbox.setMaximum(60)
        self.interval_spinbox.setValue(5)
        self.interval_spinbox.setEnabled(False)
        
        mode_layout.addWidget(QLabel("Mode:"), 0, 0)
        mode_layout.addWidget(self.mode_combo, 0, 1)
        mode_layout.addWidget(self.interval_label, 1, 0)
        mode_layout.addWidget(self.interval_spinbox, 1, 1)
        
        layout.addWidget(mode_group)
        layout.addStretch()
        
        return widget
    
    def create_settings_tab(self):
        """Create the settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Output settings group
        output_group = QGroupBox("Output Settings")
        output_layout = QGridLayout(output_group)
        
        # Output directory
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Default output directory will be used")
        output_browse_button = QPushButton("Browse...")
        output_browse_button.clicked.connect(self.browse_output_directory)
        
        output_layout.addWidget(QLabel("Output Directory:"), 0, 0)
        output_layout.addWidget(self.output_input, 0, 1)
        output_layout.addWidget(output_browse_button, 0, 2)
        
        # Duration
        self.duration_checkbox = QCheckBox("Limit recording duration")
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setMinimum(1)
        self.duration_spinbox.setMaximum(86400)  # 24 hours in seconds
        self.duration_spinbox.setValue(3600)  # 1 hour default
        self.duration_spinbox.setSuffix(" seconds")
        self.duration_spinbox.setEnabled(False)
        
        self.duration_checkbox.toggled.connect(self.duration_spinbox.setEnabled)
        
        output_layout.addWidget(self.duration_checkbox, 1, 0)
        output_layout.addWidget(self.duration_spinbox, 1, 1, 1, 2)
        
        layout.addWidget(output_group)
        
        # Upload settings group
        upload_group = QGroupBox("Upload Settings")
        upload_layout = QVBoxLayout(upload_group)
        
        self.telegram_checkbox = QCheckBox("Upload to Telegram after recording")
        upload_layout.addWidget(self.telegram_checkbox)
        
        layout.addWidget(upload_group)
        
        layout.addStretch()
        
        return widget
    
    def create_advanced_tab(self):
        """Create the advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Proxy settings group
        proxy_group = QGroupBox("Proxy Settings")
        proxy_layout = QGridLayout(proxy_group)
        
        self.proxy_checkbox = QCheckBox("Use HTTP Proxy")
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://127.0.0.1:8080")
        self.proxy_input.setEnabled(False)
        
        self.proxy_checkbox.toggled.connect(self.proxy_input.setEnabled)
        
        proxy_layout.addWidget(self.proxy_checkbox, 0, 0)
        proxy_layout.addWidget(self.proxy_input, 1, 0, 1, 2)
        
        layout.addWidget(proxy_group)
        
        # Other settings group
        other_group = QGroupBox("Other Settings")
        other_layout = QVBoxLayout(other_group)
        
        self.update_check_checkbox = QCheckBox("Check for updates before starting")
        self.update_check_checkbox.setChecked(True)
        
        other_layout.addWidget(self.update_check_checkbox)
        
        layout.addWidget(other_group)
        
        layout.addStretch()
        
        return widget
    
    def create_output_section(self):
        """Create the output/logging section"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log output
        log_group = QGroupBox("Output Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_output)
        
        # Clear log button
        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self.log_output.clear)
        log_layout.addWidget(clear_button)
        
        layout.addWidget(log_group)
        
        return widget
    
    def apply_styles(self):
        """Apply modern styling to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin: 5px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #80bdff;
                box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
            }
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 16px;
                background-color: #e9ecef;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
            QComboBox, QSpinBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }
            QTextEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox {
                spacing: 8px;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QTabBar::tab {
                border: 1px solid #dee2e6;
                border-bottom-color: transparent;
                border-radius: 4px 4px 0 0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom-color: white;
            }
            QTabBar::tab:!selected {
                background-color: #f8f9fa;
            }
        """)
    
    def on_mode_changed(self, mode_text):
        """Handle mode change"""
        is_automatic = mode_text == "Automatic"
        self.interval_spinbox.setEnabled(is_automatic)
        self.interval_label.setEnabled(is_automatic)
    
    def browse_output_directory(self):
        """Open file dialog to select output directory"""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Output Directory",
            self.output_input.text() or os.path.expanduser("~")
        )
        if directory:
            self.output_input.setText(directory)
    
    def validate_inputs(self):
        """Validate user inputs before starting recording"""
        # Check if at least one source is provided
        url = self.url_input.text().strip() if self.url_radio.isChecked() else ""
        user = self.user_input.text().strip() if self.user_radio.isChecked() else ""
        room_id = self.room_id_input.text().strip() if self.room_id_radio.isChecked() else ""
        
        if not (url or user or room_id):
            QMessageBox.warning(self, "Input Error", "Please provide a TikTok URL, username, or room ID.")
            return False
        
        # Validate proxy format if enabled
        if self.proxy_checkbox.isChecked() and self.proxy_input.text().strip():
            proxy = self.proxy_input.text().strip()
            if not proxy.startswith(('http://', 'https://')):
                QMessageBox.warning(self, "Input Error", "Proxy URL must start with http:// or https://")
                return False
        
        return True
    
    def start_recording(self):
        """Start the recording process"""
        if not self.validate_inputs():
            return
        
        # Disable start button and enable stop button
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Clear log
        self.log_output.clear()
        self.log_output.append("Preparing to start recording...")
        
        # Update status
        self.statusbar.showMessage("Recording in progress...")
        
        # Prepare recorder arguments
        recorder_args = self.get_recorder_args()
        
        # Start worker thread
        self.recorder_worker = RecorderWorker(recorder_args)
        self.recorder_worker.finished.connect(self.on_recording_finished)
        self.recorder_worker.error.connect(self.on_recording_error)
        self.recorder_worker.status_update.connect(self.on_status_update)
        self.recorder_worker.start()
    
    def stop_recording(self):
        """Stop the recording process"""
        if self.recorder_worker and self.recorder_worker.is_running:
            self.recorder_worker.stop()
            self.log_output.append("Stopping recording...")
            self.statusbar.showMessage("Stopping recording...")
    
    def get_recorder_args(self):
        """Get recorder arguments from GUI inputs"""
        args = {}
        
        # Source
        if self.url_radio.isChecked():
            args['url'] = self.url_input.text().strip()
            args['user'] = None
            args['room_id'] = None
        elif self.user_radio.isChecked():
            args['user'] = self.user_input.text().strip().lstrip('@')
            args['url'] = None
            args['room_id'] = None
        else:  # room_id
            args['room_id'] = self.room_id_input.text().strip()
            args['url'] = None
            args['user'] = None
        
        # Mode
        mode_text = self.mode_combo.currentText()
        args['mode'] = Mode.AUTOMATIC if mode_text == "Automatic" else Mode.MANUAL
        args['automatic_interval'] = self.interval_spinbox.value()
        
        # Settings
        args['output'] = self.output_input.text().strip() or None
        args['duration'] = self.duration_spinbox.value() if self.duration_checkbox.isChecked() else None
        args['use_telegram'] = self.telegram_checkbox.isChecked()
        
        # Advanced
        args['proxy'] = self.proxy_input.text().strip() if self.proxy_checkbox.isChecked() else None
        
        return args
    
    def on_recording_finished(self):
        """Handle recording completion"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.statusbar.showMessage("Recording completed")
        self.log_output.append("\n✅ Recording finished successfully!")
    
    def on_recording_error(self, error_message):
        """Handle recording error"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.statusbar.showMessage("Recording failed")
        self.log_output.append(f"\n❌ Error: {error_message}")
        
        QMessageBox.critical(self, "Recording Error", error_message)
    
    def on_status_update(self, message):
        """Handle status updates from worker"""
        self.log_output.append(f"📝 {message}")
        self.statusbar.showMessage(message)
    
    def closeEvent(self, event):
        """Handle application close event"""
        if self.recorder_worker and self.recorder_worker.is_running:
            reply = QMessageBox.question(
                self, 
                "Recording in Progress", 
                "Recording is still in progress. Do you want to stop it and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_recording()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main function to run the GUI application"""
    app = QApplication(sys.argv)
    app.setApplicationName("TikTok Live Recorder")
    app.setApplicationVersion("6.5")
    
    # Create and show the main window
    window = TikTokRecorderGUI()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())