import sys
import os
import json
import threading
import time
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QProgressBar, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QFileDialog,
    QSystemTrayIcon, QMenu, QMessageBox, QSplashScreen, QDialog
)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl

# We use the popular 'yt-dlp' library for downloading.
# It needs to be installed: pip install yt-dlp
import yt_dlp

# --- Configuration ---
APP_NAME = "EchoDownload"
APP_VERSION = "2.6 (UI Refinements)"
SETTINGS_FILE = "settings.json"
HISTORY_FILE = "history.json"
MAX_HISTORY_ITEMS = 12

# --- Asset Paths (place these files in the same directory as the script) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ICON = os.path.join(BASE_DIR, "icon.png")
SPLASH_IMAGE = os.path.join(BASE_DIR, "splash.png")
NOTIFICATION_SOUND = os.path.join(BASE_DIR, "speech.wav")

# =============================================================================
# 🎯 Core Video Downloader Functionality (Implemented in DownloadThread)
# =============================================================================

class Downloader(QObject):
    """
    Handles the yt-dlp download process in a separate thread to keep the UI responsive.
    """
    progress = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url, quality_option, download_format, download_path, cookie_file=None):
        super().__init__()
        self.url = url
        self.quality_option = quality_option
        self.download_format = download_format
        self.download_path = download_path
        self.cookie_file = cookie_file
        self._is_running = True

    def _progress_hook(self, d):
        """yt-dlp hook to capture download progress."""
        if not self._is_running:
            raise yt_dlp.utils.DownloadError("Download cancelled by user.")
        self.progress.emit(d)

    def stop(self):
        """Stops the download process."""
        self._is_running = False
        # Signal an error to force the download to stop
        self.error.emit("Download cancelled by user.")

    def run(self):
        """Starts the video download."""
        try:
            ydl_opts = {
                'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self._progress_hook],
                'noplaylist': True,
                'nocheckcertificate': True,
                'postprocessors': [],
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.5',
                },
                'socket_timeout': 120,
            }
            
            if self.cookie_file and os.path.exists(self.cookie_file):
                ydl_opts['cookiefile'] = self.cookie_file

            if self.download_format == "MP3":
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                })
            else: # MP4
                format_selector = {
                    "Best Quality": "bestvideo+bestaudio/best",
                    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
                }.get(self.quality_option, "best")
                ydl_opts['format'] = format_selector
                
                # Force MP4 output by adding post-processor to convert WebM to MP4
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                })
                
                # Set output template to always use .mp4 extension
                ydl_opts['outtmpl'] = os.path.join(self.download_path, '%(title)s.mp4')

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.url, download=True)
                self.finished.emit(info_dict)

        except Exception as e:
            self.error.emit(f"Error: {str(e)}")

# =============================================================================
# 🖥️ About & Donate Page
# =============================================================================
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About & Donate")
        self.setWindowIcon(QIcon(APP_ICON))
        self.setFixedSize(400, 500)

        self.setStyleSheet("""
            QDialog { background-color: #2E3440; }
            QLabel { color: #ECEFF4; font-size: 14px; }
            #TitleLabel { font-size: 24px; font-weight: bold; color: #88C0D0; }
            #CreditLabel { font-size: 16px; font-style: italic; color: #D8DEE9; }
            #EmailLabel { font-size: 14px; color: #81A1C1; }
            #PlatformLabel { font-size: 16px; font-weight: bold; color: #ECEFF4; }
            QPushButton {
                background-color: #5E81AC; color: #ECEFF4; border: none;
                border-radius: 8px; padding: 12px; font-weight: bold; font-size: 16px;
            }
            QPushButton:hover { background-color: #81A1C1; }
            #PayPalButton { background-color: #0079C1; }
            #PayPalButton:hover { background-color: #009ce8; }
            #CoffeeButton { background-color: #FFDD00; color: #000000; }
            #CoffeeButton:hover { background-color: #ffe642; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        title = QLabel(APP_NAME)
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        credit = QLabel("Developed by Leksautomate")
        credit.setObjectName("CreditLabel")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        email = QLabel("leksautomate@gmail.com")
        email.setObjectName("EmailLabel")
        email.setAlignment(Qt.AlignmentFlag.AlignCenter)

        message = QLabel("Thank you for using EchoDownload! If you find this app useful, please consider supporting its development.")
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        platform_title = QLabel("Supported Platforms:")
        platform_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        platforms = QLabel("YouTube, TikTok, Twitter, Pinterest, Facebook Reels & more")
        platforms.setObjectName("PlatformLabel")
        platforms.setAlignment(Qt.AlignmentFlag.AlignCenter)

        paypal_button = QPushButton("Support with PayPal")
        paypal_button.setObjectName("PayPalButton")
        paypal_button.clicked.connect(lambda: webbrowser.open("https://www.paypal.com/ncp/payment/Y59PQ6PXAVD6J"))

        coffee_button = QPushButton("Buy Me a Coffee")
        coffee_button.setObjectName("CoffeeButton")
        coffee_button.clicked.connect(lambda: webbrowser.open("https://buymeacoffee.com/leksidenation"))

        layout.addWidget(title)
        layout.addWidget(credit)
        layout.addWidget(email)
        layout.addSpacing(20)
        layout.addWidget(message)
        layout.addSpacing(10)
        layout.addWidget(platform_title)
        layout.addWidget(platforms)
        layout.addStretch()
        layout.addWidget(paypal_button)
        layout.addWidget(coffee_button)


# =============================================================================
# 🖥️ Main Application Window
# =============================================================================

class EchoDownloadApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = self.load_json(SETTINGS_FILE, default={
            "download_path": os.path.expanduser("~"),
            "notifications": True,
            "sounds": True,
            "cookie_file": ""
        })
        self.history = self.load_json(HISTORY_FILE, default=[])
        self.download_queue = []
        self.current_downloader = None
        self.current_thread = None

        self.init_ui()
        self.create_tray_icon()
        self.update_history_table()

        QApplication.clipboard().dataChanged.connect(self.auto_paste_url)
        self.setup_sound()

    def setup_sound(self):
        """Initializes the QSoundEffect and handles potential errors."""
        self.sound_effect = QSoundEffect()
        if os.path.exists(NOTIFICATION_SOUND):
            try:
                self.sound_effect.setSource(QUrl.fromLocalFile(NOTIFICATION_SOUND))
                self.sound_effect.setVolume(1.0)
            except Exception as e:
                print(f"Error loading sound file '{NOTIFICATION_SOUND}': {e}. Sound notifications disabled.")
                self.settings['sounds'] = False
        else:
            print(f"Warning: Notification sound '{NOTIFICATION_SOUND}' not found.")


    def init_ui(self):
        """Sets up the main application window and widgets."""
        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        if os.path.exists(APP_ICON):
            self.setWindowIcon(QIcon(APP_ICON))
        self.setGeometry(100, 100, 850, 700)
        self.setMinimumSize(700, 550)

        self.setStyleSheet("""
            QWidget {
                background-color: #2E3440; color: #ECEFF4;
                font-family: Segoe UI, Arial, sans-serif; font-size: 14px;
            }
            #TitleLabel {
                font-size: 32px; font-weight: bold; color: #88C0D0;
            }
            #SubtitleLabel {
                font-size: 15px; color: #D8DEE9; padding-bottom: 10px;
            }
            QLabel { color: #D8DEE9; }
            QLineEdit {
                background-color: #3B4252; border: 1px solid #4C566A;
                border-radius: 8px; padding: 10px;
            }
            QLineEdit:focus { border: 1px solid #88C0D0; }
            QPushButton {
                background-color: #5E81AC; color: #ECEFF4; border: none;
                border-radius: 8px; padding: 10px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #81A1C1; }
            QPushButton:pressed { background-color: #4C566A; }
            #DownloadButton {
                background-color: #88C0D0; color: #2E3440; padding: 12px 20px;
            }
            #DownloadButton:hover { background-color: #8FBCBB; }
            #DownloadButton:disabled { background-color: #4C566A; color: #6c757d; }
            #CancelButton {
                background-color: #BF616A; color: #ECEFF4; padding: 12px 20px;
            }
            #CancelButton:hover { background-color: #D08770; }
            #AboutButton { background-color: #EBCB8B; color: #2E3440; }
            #AboutButton:hover { background-color: #f0d59b; }
            QProgressBar {
                border: 1px solid #4C566A; border-radius: 8px; text-align: center;
                color: #ECEFF4; background-color: #3B4252; height: 28px;
            }
            QProgressBar::chunk { background-color: #A3BE8C; border-radius: 7px; }
            QTableWidget {
                background-color: #3B4252; gridline-color: #4C566A;
                border: 1px solid #4C566A; border-radius: 8px;
                alternate-background-color: #434C5E;
            }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #4C566A; }
            QHeaderView::section { background-color: #434C5E; padding: 8px; border: none; }
            QComboBox {
                background-color: #3B4252; border: 1px solid #4C566A;
                border-radius: 8px; padding: 10px;
            }
            QComboBox:disabled { background-color: #434C5E; color: #6c757d; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #3B4252; border: 1px solid #4C566A;
                selection-background-color: #5E81AC;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title_label = QLabel(APP_NAME)
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle_label = QLabel("Download from YouTube, TikTok, Twitter, Pinterest, Facebook Reels & More")
        subtitle_label.setObjectName("SubtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)

        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste video URL here...")
        self.url_input.textChanged.connect(self.detect_platform)
        self.platform_label = QLabel("Platform: N/A")
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.platform_label)
        main_layout.addLayout(input_layout)

        controls_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "MP3"])
        self.format_combo.currentTextChanged.connect(self.on_format_change)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best Quality", "1080p", "720p", "480p"])
        
        self.download_button = QPushButton("Download")
        self.download_button.setObjectName("DownloadButton")
        self.download_button.clicked.connect(self.add_to_queue)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("CancelButton")
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setVisible(False)  # Hidden by default
        
        controls_layout.addWidget(QLabel("Format:"))
        controls_layout.addWidget(self.format_combo)
        controls_layout.addWidget(QLabel("Quality:"))
        controls_layout.addWidget(self.quality_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(self.download_button)
        controls_layout.addWidget(self.cancel_button)
        main_layout.addLayout(controls_layout)

        self.status_label = QLabel("Ready. Add a URL to start.")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(QLabel("Download History"))
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["Title", "Platform", "Status"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setShowGrid(False)
        self.history_table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.history_table)

        bottom_layout = QHBoxLayout()
        self.folder_label = QLabel(f"Saving to: {self.settings['download_path']}")
        self.folder_button = QPushButton("Change Folder")
        self.folder_button.clicked.connect(self.select_folder)
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.clicked.connect(self.open_download_folder)
        self.about_button = QPushButton("About & Donate")
        self.about_button.setObjectName("AboutButton")
        self.about_button.clicked.connect(self.show_about_dialog)
        
        bottom_layout.addWidget(self.folder_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.folder_button)
        bottom_layout.addWidget(self.open_folder_button)
        bottom_layout.addWidget(self.about_button)
        main_layout.addLayout(bottom_layout)
        
        self.on_format_change(self.format_combo.currentText())

    def on_format_change(self, text):
        self.quality_combo.setEnabled(text == "MP4")

    def show_about_dialog(self):
        """Creates and shows the About & Donate dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def load_json(self, filename, default=None):
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f: return json.load(f)
        except json.JSONDecodeError: return default
        return default

    def save_json(self, filename, data):
        try:
            # Ensure the file is not read-only
            if os.path.exists(filename):
                os.chmod(filename, 0o666)
            with open(filename, 'w') as f: 
                json.dump(data, f, indent=4)
        except PermissionError:
            # If we can't write to the file, try creating a backup location
            backup_filename = f"{filename}.backup"
            try:
                with open(backup_filename, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"Warning: Could not write to {filename}, saved to {backup_filename}")
            except Exception as e:
                print(f"Error saving data: {e}")

    def save_settings(self): self.save_json(SETTINGS_FILE, self.settings)
    def save_history(self): self.save_json(HISTORY_FILE, self.history)

    def closeEvent(self, event):
        self.save_settings()
        self.save_history()
        event.accept()

    def create_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable(): return
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(APP_ICON): self.tray_icon.setIcon(QIcon(APP_ICON))
        tray_menu = QMenu()
        show_action = QAction("Show", self); show_action.triggered.connect(self.showNormal)
        quit_action = QAction("Quit", self); quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def auto_paste_url(self):
        if not self.url_input.text():
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text.startswith("http"): self.url_input.setText(text)

    def detect_platform(self):
        url = self.url_input.text().lower()
        platform = "N/A"
        if "youtube.com" in url or "youtu.be" in url: platform = "YouTube"
        elif "tiktok.com" in url: platform = "TikTok"
        elif "twitter.com" in url or "x.com" in url: platform = "Twitter"
        elif "pinterest.com" in url: platform = "Pinterest"
        elif "facebook.com" in url or "fb.watch" in url or "/reel/" in url or "/reels/" in url: platform = "Facebook"
        elif "instagram.com" in url: platform = "Instagram"
        elif "vimeo.com" in url: platform = "Vimeo"
        elif "dailymotion.com" in url: platform = "Dailymotion"
        else: platform = "Other"
        self.platform_label.setText(f"Platform: {platform}")
        return platform

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.settings['download_path'])
        if folder:
            self.settings['download_path'] = folder
            self.folder_label.setText(f"Saving to: {folder}")
            self.save_settings()

    def open_download_folder(self):
        path = self.settings.get("download_path", os.path.expanduser("~"))
        try:
            if sys.platform == "win32": os.startfile(path)
            elif sys.platform == "darwin": os.system(f'open "{path}"')
            else: os.system(f'xdg-open "{path}"')
        except Exception as e: QMessageBox.warning(self, "Error", f"Could not open folder: {e}")
            
    def add_to_queue(self):
        url = self.url_input.text()
        if not url.startswith("http"):
            QMessageBox.warning(self, "Input Error", "Please enter a valid video URL.")
            return

        # Detect platform and create platform-specific folder
        platform = self.detect_platform()
        base_path = self.settings['download_path']
        
        # Create platform-specific subfolder
        if platform != "N/A":
            platform_path = os.path.join(base_path, platform)
        else:
            platform_path = os.path.join(base_path, "Other")
        
        # Create the directory if it doesn't exist
        os.makedirs(platform_path, exist_ok=True)
        
        # For MP3 downloads, create an additional "MP3" subfolder within the platform folder
        download_format = self.format_combo.currentText()
        if download_format == "MP3":
            final_path = os.path.join(platform_path, "MP3")
            os.makedirs(final_path, exist_ok=True)
        else:
            final_path = platform_path

        download_item = {
            "url": url,
            "quality": self.quality_combo.currentText(),
            "format": download_format,
            "path": final_path,
            "cookies": self.settings.get('cookie_file')
        }
        self.download_queue.append(download_item)
        self.url_input.clear()
        self.status_label.setText(f"Added to queue. {len(self.download_queue)} item(s) waiting.")
        
        if not self.current_downloader:
            self.start_next_download()

    def start_next_download(self):
        if not self.download_queue or self.current_downloader: return

        item = self.download_queue.pop(0)
        
        self.current_thread = QThread()
        self.current_downloader = Downloader(
            url=item["url"],
            quality_option=item["quality"],
            download_format=item["format"],
            download_path=item["path"],
            cookie_file=item.get("cookies")
        )
        self.current_downloader.moveToThread(self.current_thread)
        
        self.current_thread.started.connect(self.current_downloader.run)
        self.current_downloader.progress.connect(self.update_progress)
        self.current_downloader.finished.connect(self.on_download_finished)
        self.current_downloader.error.connect(self.on_download_error)
        
        self.current_thread.start()
        self.download_button.setText("Downloading...")
        self.download_button.setEnabled(False)
        self.cancel_button.setVisible(True)

    def update_progress(self, data):
        if data['status'] == 'downloading':
            total_bytes = data.get('total_bytes_estimate', data.get('total_bytes', 0))
            downloaded_bytes = data.get('downloaded_bytes', 0)
            speed = data.get('speed', 0)
            eta = data.get('eta', 0)

            if total_bytes > 0:
                percent = (downloaded_bytes / total_bytes) * 100
                self.progress_bar.setValue(int(percent))
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "N/A"
                eta_str = f"{int(eta)}s" if eta else "N/A"
                self.status_label.setText(f"Downloading: {int(percent)}% | Speed: {speed_str} | ETA: {eta_str}")
        
        elif data['status'] == 'finished':
            self.status_label.setText("Processing file...")
            self.progress_bar.setValue(100)

    def on_download_finished(self, info):
        title = info.get('title', 'Unknown Title')
        platform = info.get('extractor_key', 'Unknown').capitalize()
        
        if self.settings.get("notifications", True) and self.tray_icon.isVisible():
            self.tray_icon.showMessage("Download Complete", f"'{title}' has finished.",
                QSystemTrayIcon.MessageIcon.Information, 5000)
        if self.settings.get("sounds", True):
            self.sound_effect.play()
            
        self.add_to_history(title, platform, "Completed")
        self.cleanup_after_download()

    def on_download_error(self, error_message):
        # Don't show error message for user-initiated cancellations
        if "Download cancelled by user" not in error_message:
            QMessageBox.critical(self, "Download Error", error_message)
            self.add_to_history("Failed Download", "N/A", "Error")
        
        # Always clean up after download
        self.cleanup_after_download()

    def cleanup_after_download(self):
        if self.current_thread:
            # Set a timeout for thread termination to prevent hanging
            self.current_thread.quit()
            if not self.current_thread.wait(3000):  # 3 second timeout
                # If thread doesn't terminate gracefully, terminate it forcefully
                self.current_thread.terminate()
                self.current_thread.wait()

        self.current_downloader = None
        self.current_thread = None
        
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready.")
        self.download_button.setText("Download")
        self.download_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        
        if self.download_queue:
            self.status_label.setText(f"Starting next download... {len(self.download_queue)} left.")
            time.sleep(0.5)
            self.start_next_download()

    def add_to_history(self, title, platform, status):
        self.history.insert(0, {"title": title, "platform": platform, "status": status})
        self.history = self.history[:MAX_HISTORY_ITEMS]
        self.update_history_table()
        self.save_history()

    def update_history_table(self):
        self.history_table.setRowCount(len(self.history))
        for row, item in enumerate(self.history):
            self.history_table.setItem(row, 0, QTableWidgetItem(item.get("title")))
            self.history_table.setItem(row, 1, QTableWidgetItem(item.get("platform")))
            self.history_table.setItem(row, 2, QTableWidgetItem(item.get("status")))
    
    def cancel_download(self):
        """Cancels the current download."""
        if self.current_downloader:
            # Disable the cancel button to prevent multiple clicks
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling download... Please wait.")
            
            # Stop the downloader (this will emit an error signal)
            self.current_downloader.stop()
            
            # Add to history
            self.add_to_history("Cancelled Download", "N/A", "Cancelled")
            
            # The cleanup will be triggered by the error handler

# =============================================================================
# 🚀 Application Entry Point
# =============================================================================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    if os.path.exists(SPLASH_IMAGE):
        splash_pix = QPixmap(SPLASH_IMAGE)
        splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
        splash.setMask(splash_pix.mask())
        splash.show()
        app.processEvents()
        time.sleep(1.5)
    
    main_window = EchoDownloadApp()
    main_window.show()
    
    if 'splash' in locals():
        splash.finish(main_window)
        
    sys.exit(app.exec())
