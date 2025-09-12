import sys
import os
import re
import html as _html
from typing import Dict, Any
import math
import random
import time
import platform

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer, Signal, QUrl, QEvent, QPoint
from PySide6.QtGui import QPalette, QColor, QFont, QPainter, QLinearGradient, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QFrame, QMessageBox, QTabWidget, QComboBox, QLineEdit,
    QToolButton, QGraphicsOpacityEffect, QSplitter
)
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWebEngineWidgets import QWebEngineView

from .file_validator import FileValidator
from .log_parser import LogParser
from .behavior_analyzer import BehaviorAnalyzer
from .cti_apis.cti_manager import CTIManager
from .report_generator import ReportGenerator
from .ai_client import AIClient
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Ensure .env is loaded for API keys and settings
load_dotenv()


class AnimatedBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._update_animation)
        self._animation_timer.start(40)  # ~25 FPS for a more dynamic feel
        
        # Animation parameters
        self._time = 0
        self._particles = []
        self._init_particles()
        
    def _init_particles(self):
        """Initialize floating particles"""
        import random
        # Clear existing particles to avoid buildup
        self._particles = []
        for _ in range(24):  # more particles for hacker vibe
            self._particles.append({
                'x': random.randint(0, 800),
                'y': random.randint(0, 600),
                'size': random.randint(2, 5),
                'speed_x': random.uniform(-0.7, 0.7),
                'speed_y': random.uniform(-0.5, 0.5),
                'opacity': random.uniform(0.25, 0.7)
            })
    
    def _update_animation(self):
        """Update animation state"""
        self._time += 0.05
        
        # Update particles
        for particle in self._particles:
            particle['x'] += particle['speed_x']
            particle['y'] += particle['speed_y']
            
            # Wrap around screen
            if particle['x'] < -10:
                particle['x'] = self.width() + 10
            elif particle['x'] > self.width() + 10:
                particle['x'] = -10
            if particle['y'] < -10:
                particle['y'] = self.height() + 10
            elif particle['y'] > self.height() + 10:
                particle['y'] = -10
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Base gradient background
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(15, 15, 25))
        gradient.setColorAt(0.5, QColor(25, 25, 40))
        gradient.setColorAt(1, QColor(35, 35, 55))
        painter.fillRect(self.rect(), gradient)
        
        # Subtle animated wave effect
        painter.setPen(Qt.NoPen)
        for i in range(2):  # Reduced wave count
            wave_color = QColor(0, 100, 150, 15)
            # Keep alpha in [0,255] using sinusoidal modulation and clamp
            alpha = 50 + int(60 * (0.5 * (1 + math.sin(self._time + i))))
            wave_color.setAlpha(max(0, min(255, alpha)))

            painter.setBrush(wave_color)

            # Create subtle wave shapes with bounded offsets
            for x in range(0, self.width(), 80):
                y_offset = int(20 * (0.5 * (1 + math.sin(self._time * 0.7 + i * 0.5))))
                y_base = self.height() // 2
                painter.drawEllipse(x - 20, (y_base - 20) + y_offset, 40, 40)
        
        # Floating particles
        painter.setPen(Qt.NoPen)
        for particle in self._particles:
            # Draw particle with glow effect
            color = QColor(0, 255, 136, int(255 * particle['opacity']))
            painter.setBrush(color)
            painter.drawEllipse(
                int(particle['x'] - particle['size']),
                int(particle['y'] - particle['size']),
                int(particle['size'] * 2),
                int(particle['size'] * 2)
            )
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reinitialize particles for new size
        self._init_particles()


class StartupScreen(QWidget):
    """Animated startup screen with file selection"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setup_ui()
        
    def setup_ui(self):
        # Use minimum size instead of fixed to allow full-window startup
        self.setMinimumSize(800, 600)
        
        # Create video background if available; fallback to animated particles
        video_path = os.path.join(os.getcwd(), "27239-362518579.mp4")
        self._use_video = os.path.exists(video_path)
        if self._use_video:
            self.video_widget = QVideoWidget(self)
            self.video_widget.setGeometry(0, 0, self.width(), self.height())
            self.video_widget.lower()
            self.media_player = QMediaPlayer(self)
            self.media_player.setVideoOutput(self.video_widget)
            self.media_player.setSource(QUrl.fromLocalFile(video_path))
            # Mute and loop
            self.audio_out = QAudioOutput(self)
            self.audio_out.setMuted(True)
            self.media_player.setAudioOutput(self.audio_out)
            self.media_player.play()
            # Loop on end
            self.media_player.mediaStatusChanged.connect(
                lambda s: self.media_player.play() if s == QMediaPlayer.EndOfMedia else None
            )
        else:
            self.background = AnimatedBackground(self)
            self.background.setGeometry(0, 0, self.width(), self.height())
            self.background.lower()  # Ensure background is behind other elements
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Add spacer to center content
        layout.addStretch(2)
        
        # Title with "l0g" in Courier font
        self.title_label = QLabel("l0g")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Consolas", 72, QFont.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("""
            QLabel {
                color: rgba(0, 220, 140, 0.85);
                background: transparent;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.title_label)
        
        # Glitch effect for title
        self.glitch_timer = QTimer()
        self.glitch_timer.timeout.connect(self._apply_title_glitch)
        self.glitch_timer.start(150)  # Apply glitch every 150ms
        
        # Subtitle
        subtitle_label = QLabel("Log Analysis & CTI Intelligence")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont("Segoe UI", 16)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                background: transparent;
                margin-top: 10px;
            }
        """)
        layout.addWidget(subtitle_label)
        
        # Add spacer
        layout.addStretch(1)
        
        # Auth + File section
        button_layout = QVBoxLayout()
        
        # Main file selection button is hidden for login-only entry screen
        self.file_button = QPushButton("Choose Log File")
        self.file_button.setVisible(False)
        self.file_button.setFocusPolicy(Qt.NoFocus)
        
        # Quick start button (hidden initially)
        self.quick_start_button = QPushButton("Quick Start with Recent File")
        self.quick_start_button.setFixedSize(200, 40)
        self.quick_start_button.setFocusPolicy(Qt.NoFocus)
        self.quick_start_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a4a, stop:1 #2a2a3a);
                border: 1px solid #666666;
                border-radius: 20px;
                color: #cccccc;
                font-size: 12px;
                font-weight: normal;
                padding: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a5a, stop:1 #3a3a4a);
                border: 1px solid #888888;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a3a, stop:1 #1a1a2a);
            }
        """)
        self.quick_start_button.clicked.connect(self.quick_start)
        self.quick_start_button.setVisible(False)
        
        # Center the buttons
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        # center_layout.addWidget(self.file_button)
        center_layout.addStretch()
        
        quick_center_layout = QHBoxLayout()
        quick_center_layout.addStretch()
        quick_center_layout.addWidget(self.quick_start_button)
        quick_center_layout.addStretch()
        
        button_layout.addLayout(center_layout)
        button_layout.addLayout(quick_center_layout)
        # layout.addLayout(button_layout)
        
        # Add spacer
        layout.addStretch(1)

        # --- Auth Section ---
        auth_box = QFrame(self)
        auth_box.setStyleSheet("QFrame { background: rgba(0,0,0,0.35); border:1px solid #444; border-radius:14px; }")
        auth_box.setVisible(False)
        auth_layout = QVBoxLayout(auth_box)
        auth_layout.setContentsMargins(16, 16, 16, 16)
        auth_layout.setSpacing(8)

        auth_title = QLabel("Account")
        auth_title.setStyleSheet("color:#CFCFCF; font-weight:600; font-size:14px;")
        auth_layout.addWidget(auth_title)

        user_row = QHBoxLayout()
        user_lbl = QLabel("Username:")
        user_lbl.setStyleSheet("color:#CFCFCF;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("username")
        self.username_input.setStyleSheet("QLineEdit { background:#1f1f27; color:#E0E0E0; border:1px solid #3a3a45; border-radius:8px; padding:6px 8px; }")
        user_row.addWidget(user_lbl)
        user_row.addWidget(self.username_input)
        auth_layout.addLayout(user_row)

        pass_row = QHBoxLayout()
        pass_lbl = QLabel("Password:")
        pass_lbl.setStyleSheet("color:#CFCFCF;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("QLineEdit { background:#1f1f27; color:#E0E0E0; border:1px solid #3a3a45; border-radius:8px; padding:6px 8px; }")
        self.pass_toggle = QToolButton()
        self.pass_toggle.setText("👁")
        self.pass_toggle.setToolTip("Show/Hide password")
        self.pass_toggle.setCheckable(True)
        self.pass_toggle.clicked.connect(lambda c: self.password_input.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password))
        pass_row.addWidget(pass_lbl)
        pass_row.addWidget(self.password_input)
        pass_row.addWidget(self.pass_toggle)
        auth_layout.addLayout(pass_row)

        # Minimal header buttons only
        header_row = QHBoxLayout()
        header_row.addStretch(1)
        self.btn_login_toggle = QPushButton("Login")
        self.btn_register_toggle = QPushButton("Register")
        for b in (self.btn_login_toggle, self.btn_register_toggle):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                "QPushButton { background: rgba(0, 180, 120, 0.8); color:#ffffff; padding:12px 18px; border:none; border-radius:10px; font-weight:600; font-size:14px; }"
                "QPushButton:hover { background: rgba(0, 200, 130, 0.9); }"
            )
            b.setFocusPolicy(Qt.NoFocus)
            b.setFixedWidth(120)
        header_row.addWidget(self.btn_login_toggle)
        header_row.addWidget(self.btn_register_toggle)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        # Collapsible card that will slide open
        self.auth_card = QFrame(self)
        self.auth_card.setStyleSheet("QFrame { background: rgba(0,0,0,0.35); border:1px solid #444; border-radius:14px; }")
        self.auth_card.setFixedWidth(430)
        self.auth_card.setMaximumHeight(1)
        card_layout = QVBoxLayout(self.auth_card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        # Login form (stacked) - modern card layout
        self.login_panel = QWidget()
        lp = QVBoxLayout(self.login_panel)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.setSpacing(10)
        # Title
        title_login = QLabel("Welcome Back")
        title_login.setAlignment(Qt.AlignCenter)
        title_login.setStyleSheet("color:#EAEAEA; font-weight:700; font-size:20px;")
        lp.addWidget(title_login)
        
        # Username row with icon
        icon_style = "QLabel{color:#9a9a9a; background:#1a1a20; border:1px solid #2d2d36; border-right:none; border-radius:8px; padding:0 8px;}"
        edit_style_combo = "QLineEdit{background:#1a1a20; color:#E0E0E0; border:1px solid #2d2d36; border-left:none; border-radius:8px; padding:8px;}"
        edit_style_full = "QLineEdit{background:#1a1a20; color:#E0E0E0; border:1px solid #2d2d36; border-radius:8px; padding:8px;}"
        urow = QHBoxLayout()
        uicon = QLabel("👤")
        uicon.setFixedWidth(28)
        uicon.setAlignment(Qt.AlignCenter)
        uicon.setStyleSheet(icon_style)
        self.username_input.setPlaceholderText("username")
        self.username_input.setStyleSheet(edit_style_combo)
        urow.addWidget(uicon)
        urow.addWidget(self.username_input)
        lp.addLayout(urow)
        # Password row with icon
        prow = QHBoxLayout()
        picon = QLabel("🔒")
        picon.setFixedWidth(28)
        picon.setAlignment(Qt.AlignCenter)
        picon.setStyleSheet(icon_style)
        self.password_input.setStyleSheet(edit_style_combo)
        prow.addWidget(picon)
        prow.addWidget(self.password_input)
        lp.addLayout(prow)
        # Primary button
        self.login_submit = QPushButton("Login")
        self.login_submit.setCursor(Qt.PointingHandCursor)
        self.login_submit.setStyleSheet("QPushButton{background:#2d6cff; color:#fff; padding:10px; border:none; border-radius:8px; font-weight:600;} QPushButton:hover{background:#3b79ff;}")
        self.login_submit.setFocusPolicy(Qt.NoFocus)
        lp.addWidget(self.login_submit)
        

        # Register form – similar card look
        self.reg_user = QLineEdit(); self.reg_user.setPlaceholderText("username"); self.reg_user.setStyleSheet(edit_style_full)
        self.reg_pass = QLineEdit(); self.reg_pass.setPlaceholderText("password"); self.reg_pass.setEchoMode(QLineEdit.Password); self.reg_pass.setStyleSheet(edit_style_full)
        self.reg_panel = QWidget()
        rp = QVBoxLayout(self.reg_panel); rp.setContentsMargins(0, 0, 0, 0); rp.setSpacing(10)
        title_reg = QLabel("Create Account"); title_reg.setAlignment(Qt.AlignCenter); title_reg.setStyleSheet("color:#EAEAEA; font-weight:700; font-size:20px;")
        rp.addWidget(title_reg)
      
        rp.addWidget(self.reg_user)
        rp.addWidget(self.reg_pass)
        self.register_submit = QPushButton("Sign Up")
        self.register_submit.setCursor(Qt.PointingHandCursor)
        self.register_submit.setStyleSheet("QPushButton{background:#2d6cff; color:#fff; padding:10px; border:none; border-radius:8px; font-weight:600;} QPushButton:hover{background:#3b79ff;}")
        self.register_submit.setFocusPolicy(Qt.NoFocus)
        rp.addWidget(self.register_submit)

        # Start with login panel visible by default
        self.reg_panel.setVisible(False)
        card_layout.addWidget(self.login_panel)
        card_layout.addWidget(self.reg_panel)
        layout.addWidget(self.auth_card)
        layout.setAlignment(self.auth_card, Qt.AlignHCenter)

        # Slide animation for the card
        self.card_anim = QPropertyAnimation(self.auth_card, b"maximumHeight")
        self.card_anim.setDuration(300)
        self.card_anim.setEasingCurve(QEasingCurve.InOutCubic)

        def open_card(show_login: bool):
            self.login_panel.setVisible(show_login)
            self.reg_panel.setVisible(not show_login)
            # Measure target height
            self.auth_card.setMaximumHeight(16777215)
            self.auth_card.adjustSize()
            target = self.auth_card.sizeHint().height() + 20 # Add some padding
            self.auth_card.setMaximumHeight(1)
            self.card_anim.stop()
            self.card_anim.setStartValue(self.auth_card.maximumHeight())
            self.card_anim.setEndValue(target)
            self.card_anim.start()

        self.btn_login_toggle.clicked.connect(lambda: open_card(True))
        self.btn_register_toggle.clicked.connect(lambda: open_card(False))

        # Wire submit buttons to existing handlers
        self.login_submit.clicked.connect(self._login)
        self.register_submit.clicked.connect(self._register)
        
        # Status label
        self.status_label = QLabel("Ready to analyze your logs")
        self.status_label = QLabel("By Ali Guliyev")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888888;
                background: transparent;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Recent file info (hidden initially)
        self.recent_file_label = QLabel("")
        self.recent_file_label.setAlignment(Qt.AlignCenter)
        self.recent_file_label.setStyleSheet("""
            QLabel {
                color: #666666;
                background: transparent;
                font-size: 10px;
                margin-top: 5px;
            }
        """)
        self.recent_file_label.setVisible(False)
        layout.addWidget(self.recent_file_label)
        
        # Add spacer
        layout.addStretch(1)
        
    def select_file(self):
        """Open file dialog and transition to main screen"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Log File",
                "",
                "Log Files (*.log *.txt);;All Files (*)"
            )
            
            if file_path:
                self.status_label.setText("Loading...")
                self.file_button.setEnabled(False)
                
                # Small delay to show loading state
                QTimer.singleShot(100, lambda: self._transition_to_main(file_path))
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self.file_button.setEnabled(True)
    
    def _transition_to_main(self, file_path):
        """Transition to main screen with error handling"""
        try:
            if self.parent_app:
                self.parent_app.transition_to_main_screen(file_path)
        except Exception as e:
            self.status_label.setText(f"Error loading file: {str(e)}")
            self.file_button.setEnabled(True)

    # ---- Simple auth backed by PostgreSQL
    def _get_db_conn(self):
        # Use provided DSN; allow override via env
        dsn = os.getenv('APP_PG_DSN') or "postgresql://postgres:uUIodWMSqakMqjCinMrwPtaPLBVLqTjz@nozomi.proxy.rlwy.net:48389/railway"
        # Railway usually requires SSL; ensure sslmode=require is set
        if '://' in dsn:
            if 'sslmode=' not in dsn:
                dsn = dsn + ("?sslmode=require" if '?' not in dsn else "&sslmode=require")
            return psycopg2.connect(dsn, cursor_factory=RealDictCursor, connect_timeout=8)
        else:
            # keyword DSN format
            if 'sslmode=' not in dsn:
                dsn += ' sslmode=require'
            return psycopg2.connect(dsn, cursor_factory=RealDictCursor, connect_timeout=8)

    def _ensure_users_table(self, conn):
        try:
            with conn.cursor() as cur:
                # Single auth+settings table used by the app
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_user_settings (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        vt_key TEXT,
                        ad_key TEXT,
                        ai_url TEXT,
                        ai_key TEXT
                    );
                    """
                )
                conn.commit()
        except Exception:
            # Ignore table creation errors (e.g., insufficient privileges)
            conn.rollback()

    def _login(self):
        u = (self.username_input.text() if hasattr(self, 'username_input') else '').strip()
        p = (self.password_input.text() if hasattr(self, 'password_input') else '').strip()
        if not u or not p:
            self.status_label.setText("Enter username and password")
            self._indicate_login_result(success=False)
            return
        try:
            with self._get_db_conn() as conn:
                with conn.cursor() as cur:
                    # Ensure table exists
                    self._ensure_users_table(conn)
                    # Authenticate against app_user_settings (case-insensitive username)
                    cur.execute("SELECT id, vt_key, ad_key, ai_url, ai_key FROM app_user_settings WHERE LOWER(username)=LOWER(%s) AND password=%s LIMIT 1", (u, p))
                    s = cur.fetchone()
                    if s:
                        self.status_label.setText(f"Welcome, {u}")
                        vt_key = s['vt_key'] if isinstance(s, dict) else s[1]
                        ab_key = s['ad_key'] if isinstance(s, dict) else s[2]
                        ai_url = s['ai_url'] if isinstance(s, dict) else s[3]
                        ai_key = s['ai_key'] if isinstance(s, dict) else s[4]
                        # Only assign to env/UI if not empty
                        target = getattr(self, 'parent_app', None) or self
                        if vt_key:
                            os.environ['VIRUSTOTAL_API_KEY'] = vt_key
                            if hasattr(target, 'vt_input'): target.vt_input.setText(vt_key)
                        else:
                            if hasattr(target, 'vt_input'): target.vt_input.setText("")
                        if ab_key:
                            os.environ['ABUSEIPDB_API_KEY'] = ab_key
                            if hasattr(target, 'abuse_input'): target.abuse_input.setText(ab_key)
                        else:
                            if hasattr(target, 'abuse_input'): target.abuse_input.setText("")
                        if ai_url:
                            os.environ['AI_API_URL'] = ai_url
                            if hasattr(target, 'ai_input'): target.ai_input.setText(ai_url)
                        else:
                            if hasattr(target, 'ai_input'): target.ai_input.setText("")
                        if ai_key:
                            os.environ['AI_API_KEY'] = ai_key
                            if hasattr(target, 'ai_key_input'): target.ai_key_input.setText(ai_key)
                        else:
                            if hasattr(target, 'ai_key_input'): target.ai_key_input.setText("")
                        self._indicate_login_result(success=True)
                        # Remember logged-in user on both windows for later saves
                        self._logged_in_user = (u, p)
                        if hasattr(self, 'parent_app') and self.parent_app:
                            self.parent_app._logged_in_user = (u, p)
                        if self.parent_app:
                            self.parent_app.transition_to_main_screen("")
                            # Ensure tables exist and load history for the logged-in user
                            try:
                                with self.parent_app._get_db_conn() as conn:
                                    self.parent_app._ensure_users_table(conn)
                                self.parent_app._load_history()
                            except Exception as e:
                                print(f"Error ensuring tables: {e}")
                    else:
                        self.status_label.setText("Invalid credentials")
                        self._indicate_login_result(success=False)
        except Exception as e:
            self.status_label.setText(f"Login error: {str(e)}")
            self._indicate_login_result(success=False)

    def _register(self):
        # Use register form fields if present; fall back to login fields
        u = (self.reg_user.text() if hasattr(self, 'reg_user') and self.reg_user.text() else (self.username_input.text() if hasattr(self, 'username_input') else '')).strip()
        p = (self.reg_pass.text() if hasattr(self, 'reg_pass') and self.reg_pass.text() else (self.password_input.text() if hasattr(self, 'password_input') else '')).strip()
        if not u or not p:
            self.status_label.setText("Enter username and password")
            self._indicate_register_result(success=False)
            return
        try:
            with self._get_db_conn() as conn:
                self._ensure_users_table(conn)
                with conn.cursor() as cur:
                    # Check if username already exists in app_user_settings (case-insensitive)
                    cur.execute("SELECT id FROM app_user_settings WHERE LOWER(username)=LOWER(%s) LIMIT 1", (u,))
                    if cur.fetchone():
                        self.status_label.setText("Username already exists")
                        self._indicate_register_result(success=False)
                        return
                    # Create minimal row; keys can be added later from Settings
                    cur.execute(
                        "INSERT INTO app_user_settings (username, password) VALUES (LOWER(%s), %s) RETURNING id",
                        (u, p)
                    )
                    conn.commit()
                    self.status_label.setText("Registration successful. You can login now.")
                    self._indicate_register_result(success=True)
        except Exception as e:
            self.status_label.setText(f"Register error: {str(e)}")
            self._indicate_register_result(success=False)
    
    def quick_start(self):
        """Quick start with the most recent file"""
        if hasattr(self.parent_app, '_last_file_path') and self.parent_app._last_file_path:
            if os.path.exists(self.parent_app._last_file_path):
                self.status_label.setText("Loading recent file...")
                self.file_button.setEnabled(False)
                self.quick_start_button.setEnabled(False)
                
                # Transition to main screen with the recent file
                if self.parent_app:
                    self.parent_app.transition_to_main_screen(self.parent_app._last_file_path)
            else:
                self.status_label.setText("Recent file not found")
                self.quick_start_button.setVisible(False)

    def paintEvent(self, event):
        # StartupScreen doesn't need custom painting - the AnimatedBackground handles it
        super().paintEvent(event)

    def resizeEvent(self, event):
        # Keep background filling the widget on resize
        if getattr(self, '_use_video', False) and hasattr(self, 'video_widget'):
            self.video_widget.setGeometry(0, 0, self.width(), self.height())
        elif hasattr(self, 'background'):
            self.background.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    # --- Visual feedback helpers ---
    def _shake_widget(self, widget):
        try:
            anim = QPropertyAnimation(widget, b"pos", self)
            start = widget.pos()
            anim.setDuration(220)
            anim.setKeyValueAt(0.0, start)
            anim.setKeyValueAt(0.25, start + QPoint(-6, 0))
            anim.setKeyValueAt(0.50, start + QPoint(6, 0))
            anim.setKeyValueAt(0.75, start + QPoint(-4, 0))
            anim.setKeyValueAt(1.0, start)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
        except Exception:
            pass

    def _indicate_login_result(self, success: bool):
        try:
            ok = "QLineEdit{background:#1a1a20; color:#E0E0E0; border:1px solid #2f8f46; border-radius:8px; padding:8px;}"
            err = "QLineEdit{background:#1a1a20; color:#E0E0E0; border:1px solid #aa3333; border-radius:8px; padding:8px;}"
            if hasattr(self, 'username_input'):
                self.username_input.setStyleSheet(ok if success else err)
            if hasattr(self, 'password_input'):
                self.password_input.setStyleSheet(ok if success else err)
            if not success and hasattr(self, 'login_panel'):
                self._shake_widget(self.login_panel)
        except Exception:
            pass

    def _indicate_register_result(self, success: bool):
        try:
            ok = "QLineEdit{background:#1a1a20; color:#E0E0E0; border:1px solid #2f8f46; border-radius:8px; padding:8px;}"
            err = "QLineEdit{background:#1a1a20; color:#E0E0E0; border:1px solid #aa3333; border-radius:8px; padding:8px;}"
            if hasattr(self, 'reg_user'):
                self.reg_user.setStyleSheet(ok if success else err)
            if hasattr(self, 'reg_pass'):
                self.reg_pass.setStyleSheet(ok if success else err)
            if not success and hasattr(self, 'reg_panel'):
                self._shake_widget(self.reg_panel)
        except Exception:
            pass
    
    def _apply_title_glitch(self):
        """Apply glitch/flicker effect to title text"""
        # Random glitch intensity
        glitch_intensity = random.randint(0, 100)
        
        # Random color variations for glitch effect
        if glitch_intensity > 85:  # Strong glitch
            colors = ["rgba(0, 255, 0, 0.9)", "rgba(0, 220, 140, 0.85)", "rgba(0, 180, 100, 0.8)", "rgba(0, 200, 120, 0.9)"]
            color = random.choice(colors)
        elif glitch_intensity > 60:  # Medium glitch
            colors = ["rgba(0, 220, 140, 0.85)", "rgba(0, 200, 120, 0.8)", "rgba(0, 180, 100, 0.9)"]
            color = random.choice(colors)
        else:  # Normal color
            color = "rgba(0, 220, 140, 0.85)"
        
        # Apply glitch effect to title
        style = f"""
            QLabel {{
                color: {color};
                background: transparent;
                font-weight: bold;
            }}
        """
        self.title_label.setStyleSheet(style)
        
        # Random character corruption (rare)
        if glitch_intensity > 90:
            corrupted_text = self._corrupt_title_text("l0g")
            self.title_label.setText(corrupted_text)
        else:
            self.title_label.setText("l0g")
    
    def _corrupt_title_text(self, text):
        """Corrupt title text with random characters"""
        corrupted = list(text)
        # Randomly corrupt 1 character
        if len(corrupted) > 0:
            pos = random.randint(0, len(corrupted) - 1)
            corrupted[pos] = random.choice(['ø', '0', 'l', 'g', '█', '▓', '▒', '░'])
        
        return ''.join(corrupted)


class ModernProgressBar(QWidget):
    """Modern animated progress bar with gradient and pulsing effect"""
    
    progress_updated = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self._progress = 0
        self._max_progress = 100
        self._animation_offset = 0
        
        # Animation timer for pulsing effect
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_animation)
        self._timer.start(50)  # 20 FPS
        
        # Colors
        self._bg_color = QColor(40, 40, 50)
        self._progress_color1 = QColor(76, 175, 80)
        self._progress_color2 = QColor(139, 195, 74)
        self._glow_color = QColor(76, 175, 80, 100)
        
    def setProgress(self, value):
        """Set progress value (0-100)"""
        self._progress = max(0, min(100, value))
        self.progress_updated.emit(self._progress)
        self.update()
        
    def setMaximum(self, value):
        """Set maximum progress value"""
        self._max_progress = value
        
    def _update_animation(self):
        """Update animation offset for pulsing effect"""
        self._animation_offset += 0.1
        if self._animation_offset > 2 * 3.14159:  # Reset after full cycle
            self._animation_offset = 0
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self._bg_color)
        
        if self._progress > 0:
            # Progress bar width
            progress_width = int((self._progress / 100.0) * self.width())
            
            # Create gradient
            gradient = QLinearGradient(0, 0, progress_width, 0)
            gradient.setColorAt(0, self._progress_color1)
            gradient.setColorAt(1, self._progress_color2)
            
            # Draw progress bar
            painter.fillRect(0, 0, progress_width, self.height(), gradient)
            
            # Add pulsing glow effect
            if self._progress > 0:
                glow_intensity = int(50 + 30 * abs(1 + 0.5 * (1 + self._animation_offset)))
                glow_color = QColor(self._glow_color.red(), self._glow_color.green(), 
                                  self._glow_color.blue(), glow_intensity)
                painter.fillRect(0, 0, progress_width, self.height(), glow_color)


class ConsoleAnimationWidget(QWidget):
    """Console-style animation widget with typing effect for hints"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(35)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                color: #00aa00;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(6)
        
        # Console prompt
        self.prompt_label = QLabel(">")
        self.prompt_label.setStyleSheet("color: #00aa00; font-weight: bold;")
        layout.addWidget(self.prompt_label)
        
        # Typing animation label
        self.text_label = QLabel("")
        self.text_label.setStyleSheet("color: #00aa00;")
        layout.addWidget(self.text_label, 1)
        
        # Cursor
        self.cursor_label = QLabel("_")
        self.cursor_label.setStyleSheet("color: #00aa00;")
        layout.addWidget(self.cursor_label)
        
        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._animate_cursor)
        self.timer.start(300)  # Blink cursor every 300ms
        
        # Typing timer
        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self._type_next_char)
        
        # Hints list
        self.hints = [
            "Use 'Choose Log File' button to load log files for analysis",
            "Select IP addresses and click 'Get CTI Data' to fetch threat intelligence",
            "Use 'AI Analysis' tab for advanced AI-powered log analysis",
            "Click 'Generate Report' to save analysis results in PDF format",
            "Open 'Map View' tab to see geographical locations of IP addresses",
            "Check 'Threat Analysis' tab to view threat levels and risk assessment",
            "First select a log file, then click 'Parse Logs' to start analysis",
            "Use 'Behavior Analysis' tab to analyze IP address behavior patterns",
            "Click 'History' button to view previous analysis sessions",
            "Click the X button in the top-right corner to close the application",
            "Use 'Export Data' to save analysis results in various formats",
            "Check 'Statistics' tab for detailed log file statistics and metrics",
            "Use 'Filter' options to narrow down analysis to specific criteria",
            "Click 'Refresh' to update CTI data with latest threat information",
            "Use keyboard shortcuts for faster navigation and operations"
        ]
        
        self.current_hint_index = 0
        self.current_text = ""
        self.target_text = ""
        self.char_index = 0
        self.is_typing = False
        self.cursor_visible = True
        
        # Start with first hint
        self._start_new_hint()
        
        # Timer to change hints
        self.hint_timer = QTimer()
        self.hint_timer.timeout.connect(self._change_hint)
        self.hint_timer.start(5000)  # Change hint every 5 seconds
    
    def _animate_cursor(self):
        """Animate cursor blinking"""
        self.cursor_visible = not self.cursor_visible
        self.cursor_label.setText("_" if self.cursor_visible else " ")
    
    def _start_new_hint(self):
        """Start typing a new hint"""
        self.target_text = self.hints[self.current_hint_index]
        self.current_text = ""
        self.char_index = 0
        self.is_typing = True
        self.typing_timer.start(30)  # Type every 30ms
    
    def _type_next_char(self):
        """Type next character"""
        if self.char_index < len(self.target_text):
            self.current_text += self.target_text[self.char_index]
            self.text_label.setText(self.current_text)
            self.char_index += 1
        else:
            self.is_typing = False
            self.typing_timer.stop()
    
    def _change_hint(self):
        """Change to next hint"""
        self.current_hint_index = (self.current_hint_index + 1) % len(self.hints)
        self._start_new_hint()


class DarkWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log Analysis & CTI - Dark Mode")
        self.setMinimumSize(1000, 700)
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "l0g_dark_green.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self._init_palette()
        # Enable custom gray title bar (frameless window)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        # Root layout with custom title bar
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(1, 1, 1, 1)
        root_layout.setSpacing(0)
        # Title bar
        self._titlebar = QWidget(self)
        self._titlebar.setFixedHeight(36)
        self._titlebar.setStyleSheet("background:#2b2b2b; border-bottom:1px solid #1f1f1f;")
        tb = QHBoxLayout(self._titlebar)
        tb.setContentsMargins(8, 4, 6, 4)
        tb.setSpacing(6)
        # Add icon to title bar
        self._title_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "l0g_dark_green.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            pixmap = icon.pixmap(20, 20)
            self._title_icon.setPixmap(pixmap)
        else:
            self._title_icon.setText("📊")
            self._title_icon.setStyleSheet("color:#00aa00; font-size:16px;")
        tb.addWidget(self._title_icon)
        
        self._title = QLabel("Log Analysis & CTI")
        self._title.setStyleSheet("color:#E6E6E6; font-weight:600;")
        tb.addWidget(self._title)
        tb.addStretch(1)
        def mk_btn(txt, tip, hover=None):
            b = QToolButton(self._titlebar)
            b.setText(txt)
            b.setToolTip(tip)
            b.setFixedSize(34, 26)
            base = "QToolButton { background:#3a3a3a; color:#E6E6E6; border:none; border-radius:4px; }"
            hov = f"QToolButton:hover {{ background:{hover or '#4a4a4a'}; }}"
            b.setStyleSheet(base + hov)
            b.setCursor(Qt.PointingHandCursor)
            return b
        self._btn_min = mk_btn("–", "Minimize")
        self._btn_max = mk_btn("□", "Maximize/Restore")
        self._btn_close = mk_btn("✕", "Close", "#d9534f")
        tb.addWidget(self._btn_min)
        tb.addWidget(self._btn_max)
        tb.addWidget(self._btn_close)
        root_layout.addWidget(self._titlebar)
        # Drag support
        self._drag_pos = None
        self._titlebar.mousePressEvent = lambda e: self._set_drag(e)
        self._titlebar.mouseMoveEvent = lambda e: self._do_drag(e)
        self._titlebar.mouseDoubleClickEvent = lambda e: self._toggle_max() if e.button()==Qt.LeftButton else None
        # Titlebar actions
        self._btn_min.clicked.connect(self.showMinimized)
        self._btn_max.clicked.connect(self._toggle_max)
        self._btn_close.clicked.connect(self.close)
        # Central container below titlebar
        self._central = QWidget(self)
        root_layout.addWidget(self._central, 1)
        
        # Console animation widget at the bottom
        self.console_widget = ConsoleAnimationWidget(self)
        root_layout.addWidget(self.console_widget)
        # Enable mouse tracking for resize cursors (global)
        self.setMouseTracking(True)
        self._central.setMouseTracking(True)
        # Only show resize cursor on edges; do not resize on drag
        self._hover_resize_only = True
        # Disable custom resizing/cursor behavior (revert to previous form)
        self._resize_disabled = True
        # Do not install edge-tracking filters when disabled
        # (leave mouse tracking enabled for other UI effects)
        # Initial size
        self.resize(1280, 800)
        
        # Start with startup screen
        self.startup_screen = StartupScreen(self)
        self.main_layout = QVBoxLayout(self._central)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.startup_screen)
        
        # Initialize main screen components (hidden initially)
        self._init_main_screen()

    def _set_ai_output(self, content: str):
        try:
            # Prefer native markdown rendering if available
            if hasattr(self.ai_output, 'setMarkdown'):
                self.ai_output.setMarkdown(content)
                return
            # Fallback: very small markdown→HTML converter
            lines_html = []
            for line in content.splitlines():
                m = re.match(r'^(#{1,6})\s*(.*)', line)
                if m:
                    level = len(m.group(1))
                    text = _html.escape(m.group(2))
                    lines_html.append(f"<h{level}>{text}</h{level}>")
                    continue
                esc = _html.escape(line)
                esc = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', esc)
                s = esc.strip()
                if s.startswith('- ') or s.startswith('* '):
                    li = s[2:].strip()
                    lines_html.append(f"<li>{li}</li>")
                else:
                    lines_html.append(f"<p>{esc}</p>")
            html_doc = "<div style='font-family: Segoe UI; color:#D0D0D0;'>" + "".join(lines_html) + "</div>"
            self.ai_output.setHtml(html_doc)
        except Exception:
            self.ai_output.setPlainText(content)
        
    def _init_main_screen(self):
        """Initialize the main analysis screen components"""
        # Create main screen widget
        self.main_screen = QWidget()
        self.main_screen.setVisible(False)
        
        # Animated background behind main content (hidden per request)
        self.bg = AnimatedBackground(self.main_screen)
        self.bg.setVisible(False)
        self.bg.lower()

        layout = QVBoxLayout(self.main_screen)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Log Analysis & CTI")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #E0E0E0;")

        # Controls
        controls = QHBoxLayout()
        self.path_label = QLabel("No file selected")
        self.path_label.setStyleSheet("color:#A0A0A0;")
        
        # Back to start button
        back_button = QPushButton("← Back to Start")
        back_button.clicked.connect(self._back_to_start)
        back_button.setStyleSheet(
            "QPushButton {"
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a4a4a, stop:1 #2a2a2a);"
            "border: 2px solid #666666; border-radius: 15px; color: #cccccc;"
            "font-size: 12px; font-weight: bold; padding: 8px 12px; }"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a5a5a, stop:1 #3a3a3a);"
            "border: 2px solid #888888; color: #ffffff; }"
            "QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a3a3a, stop:1 #1a1a1a); }"
        )
        back_button.setFocusPolicy(Qt.NoFocus)
        
        browse = QPushButton("Browse Log…")
        browse.clicked.connect(self._browse)
        browse.setFocusPolicy(Qt.NoFocus)
        run = QPushButton("▶ Run Analysis")
        run.clicked.connect(self._run)
        run.setFocusPolicy(Qt.NoFocus)
        self.progress = ModernProgressBar()
        self.progress.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color:#A0A0A0; font-size: 12px;")
        self.progress_label.setVisible(False)

        for w in (browse, run):
            w.setCursor(Qt.PointingHandCursor)
            w.setStyleSheet(self._button_style())

        # Special gradient style for Run Analysis button (blue → red)
        run.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #ef4444); color:#ffffff; padding:8px 14px; border:1px solid #3A3A45; border-radius:8px; }"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #dc2626); }"
            "QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e40af, stop:1 #b91c1c); }"
        )

        controls.addWidget(back_button)
        controls.addWidget(self.path_label)
        controls.addStretch(1)
        
        # Export button
        export_btn = QPushButton("📊 Export Reports")
        export_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 180, 120, 0.8);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(0, 200, 130, 0.9);
            }
            QPushButton:pressed {
                background: rgba(0, 160, 100, 0.9);
            }
        """)
        export_btn.clicked.connect(self._show_export_menu)
        export_btn.setFocusPolicy(Qt.NoFocus)
        controls.addWidget(export_btn)
        # Filters
        self.filter_threat = QComboBox()
        self.filter_threat.addItems(["All", "High", "Medium", "Low", "Clean", "Unknown"])
        self.filter_threat.setToolTip("Filter by threat level")
        self.filter_threat.currentIndexChanged.connect(lambda _: self._populate_table(self._last_results))

        self.sort_by = QComboBox()
        self.sort_by.addItems(["Sort by Risk (desc)", "Sort by Threat", "Sort by IP"])
        self.sort_by.setToolTip("Sorting option")
        self.sort_by.currentIndexChanged.connect(lambda _: self._populate_table(self._last_results))

        combo_style = (
            "QComboBox{background:#1a1a20; color:#E0E0E0; border:1px solid #2d2d36; border-radius:8px; padding:6px 8px;}"
            "QComboBox QAbstractItemView{background:#1a1a20; color:#E0E0E0; selection-background-color:#2d2d36; selection-color:#ffffff;}"
        )
        self.filter_threat.setStyleSheet(combo_style)
        self.sort_by.setStyleSheet(combo_style)

        labels_style = "color:#CFCFCF;"
        lbl_threat = QLabel("Threat:")
        lbl_threat.setStyleSheet(labels_style)
        lbl_sort = QLabel("Sort:")
        lbl_sort.setStyleSheet(labels_style)

        controls.addWidget(lbl_threat)
        controls.addWidget(self.filter_threat)
        controls.addSpacing(8)
        controls.addWidget(lbl_sort)
        controls.addWidget(self.sort_by)
        controls.addSpacing(8)
        controls.addWidget(browse)
        controls.addWidget(run)
        
        # Progress section
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress)
        controls.addLayout(progress_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #333; } "
            "QTabBar::tab { "
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #ef4444); "
            "  color:#ffffff; padding:8px 14px; border-radius:10px; margin-right:6px; "
            "} "
            "QTabBar::tab:selected { "
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #dc2626); "
            "} "
            "QTabBar::tab:hover { "
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e40af, stop:1 #b91c1c); "
            "}"
        )

        # Results tab
        self.results_tab = QWidget()
        results_layout = QVBoxLayout(self.results_tab)

        self.table = QTableWidget(0, 10)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(True)
        self.table.setHorizontalHeaderLabels([
            "IP", "Threat", "Priority", "Risk %", "Abuse Confidence %", "Abuse Risk Score", "VT Reputation", "Top Status", "Behavior Indicators", "Methods"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet(self._table_style())
        # Ensure vertical header (row numbers) uses dark background even below last row
        self.table.verticalHeader().setStyleSheet(
            "QHeaderView { background:#2B2B35; } QHeaderView::section { background:#2B2B35; color:#CFCFCF; }"
        )
        self.table.cellClicked.connect(self._on_table_click)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("background: rgba(0,0,0,0.35); color: #D0D0D0; border:1px solid #333; border-radius:8px;")

        # Right-side AI output pane
        self.ai_output = QTextEdit()
        self.ai_output.setReadOnly(True)
        self.ai_output.setPlaceholderText("AI output will appear here…")
        self.ai_output.setStyleSheet("background: rgba(0,0,0,0.35); color: #D0D0D0; border:1px solid #333; border-radius:8px;")

        bottom_split = QSplitter()
        bottom_split.setOrientation(Qt.Horizontal)
        bottom_split.addWidget(self.output)
        bottom_split.addWidget(self.ai_output)
        bottom_split.setSizes([700, 500])
        bottom_split.setStyleSheet(
            "QSplitter::handle:horizontal{"
            "  width:2px;"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #ef4444);"
            "  margin:0;"
            "}"
        )

        # Old export buttons removed - using new Export Reports button instead

        results_layout.addWidget(self.table, 2)
        results_layout.addWidget(bottom_split, 1)

        # Statistics tab
        self.stats_tab = QWidget()
        stats_layout = QVBoxLayout(self.stats_tab)
        self.ai_summary = QLabel("")
        self.ai_summary.setStyleSheet("color:#CFCFCF;")
        self.ai_summary.setWordWrap(True)
        self.pie_view = QChartView()
        self.bar_view = QChartView()
        for v in (self.pie_view, self.bar_view):
            v.setRenderHint(v.renderHints())
            v.setStyleSheet("background: rgba(0,0,0,0.30); border:1px solid #333; border-radius:8px;")
        stats_layout.addWidget(self.ai_summary)
        charts_row = QHBoxLayout()
        charts_row.addWidget(self.pie_view, 1)
        charts_row.addWidget(self.bar_view, 2)
        stats_layout.addLayout(charts_row, 1)

        # History tab
        self.history_tab = QWidget()
        history_layout = QVBoxLayout(self.history_tab)
        
        # History table
        self.history_table = QTableWidget(0, 4)
        self.history_table.setAlternatingRowColors(False)
        self.history_table.setShowGrid(True)
        self.history_table.setHorizontalHeaderLabels([
            "IP Address", "Threat Level", "Timestamp", "AI Analysis"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setStyleSheet(self._table_style())
        self.history_table.cellClicked.connect(self._on_history_click)
        
        # History details area
        self.history_details = QTextEdit()
        self.history_details.setReadOnly(True)
        self.history_details.setStyleSheet("background: rgba(0,0,0,0.35); color: #D0D0D0; border:1px solid #333; border-radius:8px;")
        self.history_details.setPlaceholderText("Click on a history entry to view details...")
        
        # Clear history button
        clear_history_btn = QPushButton("🗑️ Clear History")
        clear_history_btn.setStyleSheet("""
            QPushButton {
                background: rgba(220, 38, 38, 0.8);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.9);
            }
            QPushButton:pressed {
                background: rgba(185, 28, 28, 0.9);
            }
        """)
        clear_history_btn.clicked.connect(self._clear_history)
        clear_history_btn.setFocusPolicy(Qt.NoFocus)
        
        history_controls = QHBoxLayout()
        history_controls.addWidget(clear_history_btn)
        history_controls.addStretch(1)
        
        history_layout.addLayout(history_controls)
        
        # Create splitter for resizable panes
        history_splitter = QSplitter()
        history_splitter.setOrientation(Qt.Vertical)
        history_splitter.addWidget(self.history_table)
        history_splitter.addWidget(self.history_details)
        history_splitter.setSizes([400, 200])  # Initial sizes
        history_splitter.setStyleSheet(
            "QSplitter::handle:vertical{"
            "  height:2px;"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #ef4444);"
            "  margin:0;"
            "}"
        )
        
        history_layout.addWidget(history_splitter)

        # Map tab
        self.map_tab = QWidget()
        map_layout = QVBoxLayout(self.map_tab)
        self.map_view = QWebEngineView()
        self.map_view.setHtml("""
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>
  <style> html, body, #map { height:100%; margin:0; } .marker-label{font:12px Segoe UI, sans-serif;} </style>
  <script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
  <script>
    let map;
    function init() {
      map = L.map('map', { worldCopyJump: true }).setView([20,0], 2);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 6, attribution: '© OpenStreetMap'}).addTo(map);
    }
    function clearMarkers(){ if(!map) return; map.eachLayer(function(l){ if(l instanceof L.CircleMarker) map.removeLayer(l); }); }
    function addMarker(lat, lng, color, label){
      if(!map) return;
      const m = L.circleMarker([lat,lng], {radius:6, color:color, fillColor:color, fillOpacity:0.9, weight:1});
      m.bindTooltip(label, {permanent:false, direction:'top', className:'marker-label'});
      m.addTo(map);
    }
    window.addEventListener('load', init);
  </script>
  </head>
  <body><div id='map'></div></body>
  </html>
        """)
        map_layout.addWidget(self.map_view)
        self.tabs.addTab(self.results_tab, "Results")
        self.tabs.addTab(self.stats_tab, "Statistics")
        self.tabs.addTab(self.history_tab, "History")
        self.tabs.addTab(self.map_tab, "Map")

        # Settings tab
        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout(self.settings_tab)
        settings_layout.setContentsMargins(12, 12, 12, 12)

        api_title = QLabel("API Settings")
        api_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        api_title.setStyleSheet("color:#CFCFCF;")

        vt_row = QHBoxLayout()
        vt_label = QLabel("VirusTotal API Key:")
        vt_label.setStyleSheet("color:#CFCFCF;")
        self.vt_input = QLineEdit()
        self.vt_input.setPlaceholderText("Enter your VirusTotal API key")
        self.vt_input.setText("")
        self.vt_input.setEchoMode(QLineEdit.Password)
        self.vt_toggle = QToolButton()
        self.vt_toggle.setText("👁")
        self.vt_toggle.setToolTip("Show/Hide token")
        self.vt_toggle.setCheckable(True)
        self.vt_toggle.clicked.connect(lambda checked: self.vt_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        vt_row.addWidget(vt_label)
        vt_row.addWidget(self.vt_input)
        vt_row.addWidget(self.vt_toggle)

        abuse_row = QHBoxLayout()
        abuse_label = QLabel("AbuseIPDB API Key:")
        abuse_label.setStyleSheet("color:#CFCFCF;")
        self.abuse_input = QLineEdit()
        self.abuse_input.setPlaceholderText("Enter your AbuseIPDB API key")
        self.abuse_input.setText("")
        self.abuse_input.setEchoMode(QLineEdit.Password)
        self.abuse_toggle = QToolButton()
        self.abuse_toggle.setText("👁")
        self.abuse_toggle.setToolTip("Show/Hide token")
        self.abuse_toggle.setCheckable(True)
        self.abuse_toggle.clicked.connect(lambda checked: self.abuse_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        abuse_row.addWidget(abuse_label)
        abuse_row.addWidget(self.abuse_input)
        abuse_row.addWidget(self.abuse_toggle)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        save_btn = QPushButton("Save Tokens")
        save_btn.setStyleSheet(self._button_style())
        save_btn.clicked.connect(self._save_api_tokens)
        btn_row.addWidget(save_btn)

        logout_btn = QPushButton("Log out")
        logout_btn.setStyleSheet(self._button_style())
        logout_btn.clicked.connect(self._back_to_start)
        save_btn.setFocusPolicy(Qt.NoFocus)
        logout_btn.setFocusPolicy(Qt.NoFocus)
        btn_row.addWidget(logout_btn)

        note = QLabel("Tokens are kept in memory for this session only.")
        note.setStyleSheet("color:#9a9a9a;")

        settings_layout.addWidget(api_title)
        settings_layout.addLayout(vt_row)
        settings_layout.addLayout(abuse_row)
        # AI API settings
        ai_row = QHBoxLayout()
        ai_label = QLabel("AI API URL:")
        ai_label.setStyleSheet("color:#CFCFCF;")
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("https://api.mistral.ai/v1/chat/completions")
        self.ai_input.setText("")
        ai_key_label = QLabel("AI API Key:")
        ai_key_label.setStyleSheet("color:#CFCFCF;")
        self.ai_key_input = QLineEdit()
        self.ai_key_input.setPlaceholderText("paste API key")
        self.ai_key_input.setEchoMode(QLineEdit.Password)
        self.ai_key_input.setText("")
        ai_row.addWidget(ai_label)
        ai_row.addWidget(self.ai_input)
        ai_row.addWidget(ai_key_label)
        ai_row.addWidget(self.ai_key_input)
        settings_layout.addLayout(ai_row)
        
        # Scan Speed settings
        speed_title = QLabel("Scan Speed")
        speed_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        speed_title.setStyleSheet("color:#CFCFCF;")
        speed_title.setContentsMargins(0, 20, 0, 0)
        
        speed_row = QHBoxLayout()
        speed_label = QLabel("API Request Delay:")
        speed_label.setStyleSheet("color:#CFCFCF;")
        self.speed_combo = QComboBox()
        self.speed_combo.addItems([
            "Fast (0.0s delay)",
            "Normal (0.5s delay)", 
            "Slow (1.0s delay)",
            "Very Slow (2.0s delay)"
        ])
        self.speed_combo.setCurrentText("Normal (0.5s delay)")
        self.speed_combo.setStyleSheet("""
            QComboBox {
                background:#1a1a20; 
                color:#E0E0E0; 
                border:1px solid #2d2d36; 
                border-radius:8px; 
                padding:6px 8px;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #E0E0E0;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background:#1a1a20; 
                color:#E0E0E0; 
                border:1px solid #2d2d36; 
                border-radius:8px;
                selection-background-color: #2d2d36;
            }
        """)
        speed_row.addWidget(speed_label)
        speed_row.addWidget(self.speed_combo)
        speed_row.addStretch(1)
        
        settings_layout.addWidget(speed_title)
        settings_layout.addLayout(speed_row)
        settings_layout.addLayout(btn_row)
        settings_layout.addSpacing(6)
        settings_layout.addWidget(note)
        settings_layout.addStretch(1)

        self.tabs.addTab(self.settings_tab, "Settings")

        layout.addWidget(title)
        layout.addLayout(controls)
        layout.addWidget(self.tabs, 1)

        # Initial state
        self._log_path = None
        self._last_file_path = None
        self._last_results: Dict[str, Any] = {}
        self._last_stats: Dict[str, Any] = {}
        self._cti_stats: Dict[str, Any] = {}
        
        # Add main screen to main layout
        self.main_layout.addWidget(self.main_screen)

    def transition_to_main_screen(self, file_path):
        """Transition from startup screen to main analysis screen"""
        # Set the file path
        self._log_path = file_path
        self._last_file_path = file_path  # Store for recent file display
        self.path_label.setText(f"Selected: {os.path.basename(file_path)}")
        
        # Hide startup screen and show main screen
        self.startup_screen.setVisible(False)
        self.main_screen.setVisible(True)
        
        # Do not resize the window here; keep user's chosen size

    def _init_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(18, 18, 24))
        pal.setColor(QPalette.WindowText, QColor(224, 224, 224))
        pal.setColor(QPalette.Base, QColor(24, 24, 30))
        pal.setColor(QPalette.AlternateBase, QColor(28, 28, 36))
        pal.setColor(QPalette.ToolTipBase, QColor(28, 28, 36))
        pal.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
        pal.setColor(QPalette.Text, QColor(224, 224, 224))
        pal.setColor(QPalette.Button, QColor(38, 38, 48))
        pal.setColor(QPalette.ButtonText, QColor(224, 224, 224))
        pal.setColor(QPalette.Highlight, QColor(76, 175, 80))
        pal.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        self.setPalette(pal)
        
        # Platform-specific font settings
        if platform.system() == "Linux":
            # Use system fonts on Linux for better compatibility
            font = QFont("DejaVu Sans", 9)
            self.setFont(font)

    def _set_drag(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _do_drag(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
            self._btn_max.setText("□")
        else:
            self.showMaximized()
            self._btn_max.setText("❐")

    # --- DB helpers (used for saving tokens from Settings) ---
    def _get_db_conn(self):
        dsn = os.getenv('APP_PG_DSN') or "postgresql://postgres:uUIodWMSqakMqjCinMrwPtaPLBVLqTjz@nozomi.proxy.rlwy.net:48389/railway"
        if '://' in dsn:
            if 'sslmode=' not in dsn:
                dsn = dsn + ("?sslmode=require" if '?' not in dsn else "&sslmode=require")
            return psycopg2.connect(dsn, cursor_factory=RealDictCursor, connect_timeout=8)
        else:
            if 'sslmode=' not in dsn:
                dsn += ' sslmode=require'
            return psycopg2.connect(dsn, cursor_factory=RealDictCursor, connect_timeout=8)

    def _ensure_users_table(self, conn):
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_user_settings (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        vt_key TEXT,
                        ad_key TEXT,
                        ai_url TEXT,
                        ai_key TEXT
                    );
                    """
                )
                
                # Create history table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ip_history (
                        id SERIAL PRIMARY KEY,
                        username TEXT NOT NULL,
                        ip_address VARCHAR(45) NOT NULL,
                        threat_level VARCHAR(20),
                        risk_score INTEGER,
                        ai_analysis TEXT,
                        ip_details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (username) REFERENCES app_user_settings(username)
                    );
                    """
                )
                conn.commit()
        except Exception:
            conn.rollback()

    # --- Resizable frameless window ---
    _RESIZE_MARGIN = 8
    _resizing = False
    _resize_edge = None
    _start_geo = None
    _start_pos = None

    def _hit_edges(self, pos):
        x, y, w, h, m = pos.x(), pos.y(), self.width(), self.height(), self._RESIZE_MARGIN
        on_left = x <= m
        on_right = x >= w - m
        on_top = y <= m
        on_bottom = y >= h - m
        if on_top and on_left:
            return 'top_left'
        if on_top and on_right:
            return 'top_right'
        if on_bottom and on_left:
            return 'bottom_left'
        if on_bottom and on_right:
            return 'bottom_right'
        if on_top:
            return 'top'
        if on_bottom:
            return 'bottom'
        if on_left:
            return 'left'
        if on_right:
            return 'right'
        return None

    def _set_cursor_for_edge(self, edge):
        mapping = {
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor,
            'top_left': Qt.SizeFDiagCursor,
            'bottom_right': Qt.SizeFDiagCursor,
            'top_right': Qt.SizeBDiagCursor,
            'bottom_left': Qt.SizeBDiagCursor,
        }
        self.setCursor(mapping.get(edge, Qt.ArrowCursor))

    def mousePressEvent(self, event):
        if not self._hover_resize_only:
            if event.button() == Qt.LeftButton and not self.isMaximized():
                edge = self._hit_edges(event.position().toPoint())
                if edge:
                    self._resizing = True
                    self._resize_edge = edge
                    self._start_geo = self.geometry()
                    self._start_pos = event.globalPosition().toPoint()
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (not self._hover_resize_only) and self._resizing and self._resize_edge and not self.isMaximized():
            delta = event.globalPosition().toPoint() - self._start_pos
            geo = self._start_geo
            minw, minh = self.minimumWidth(), self.minimumHeight()
            x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
            dx, dy = delta.x(), delta.y()
            if 'left' in self._resize_edge:
                new_x = x + dx
                new_w = w - dx
                if new_w >= minw:
                    x = new_x
                    w = new_w
            if 'right' in self._resize_edge:
                new_w = w + dx
                if new_w >= minw:
                    w = new_w
            if 'top' in self._resize_edge:
                new_y = y + dy
                new_h = h - dy
                if new_h >= minh:
                    y = new_y
                    h = new_h
            if 'bottom' in self._resize_edge:
                new_h = h + dy
                if new_h >= minh:
                    h = new_h
            self.setGeometry(x, y, w, h)
            event.accept()
            return
        # Update cursor when hovering near edges
        if not getattr(self, '_resize_disabled', False):
            edge = self._hit_edges(event.position().toPoint()) if not self.isMaximized() else None
            self._set_cursor_for_edge(edge)
        super().mouseMoveEvent(event)

    def eventFilter(self, obj, event):
        # Update cursor when moving over any child widget (so the edge hover works everywhere)
        if event.type() == QEvent.MouseMove and not self.isMaximized() and not getattr(self, '_resize_disabled', False):
            # Map child coordinates to window coordinates
            global_pos = obj.mapToGlobal(event.position().toPoint()) if hasattr(event, 'position') else None
            if global_pos is not None:
                local = self.mapFromGlobal(global_pos)
                edge = self._hit_edges(local)
                self._set_cursor_for_edge(edge)
        return super().eventFilter(obj, event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _button_style(self) -> str:
        return (
            "QPushButton { background:#2F2F3A; color:#E0E0E0; padding:8px 14px; border:1px solid #3A3A45; border-radius:8px; }"
            "QPushButton:hover { background:#3A3A48; }"
            "QPushButton:pressed { background:#2A2A35; }"
        )

    def _table_style(self) -> str:
        return (
            "QHeaderView::section { background:#2B2B35; color:#CFCFCF; padding:6px; border: none; }"
            "QTableWidget { background: rgba(0,0,0,0.30); gridline-color:#3A3A45; color:#D0D0D0; border:1px solid #333; border-radius:8px; }"
            "QTableWidget::viewport { background: rgba(0,0,0,0.30); }"
            "QTableWidget QHeaderView { background:#2B2B35; }"
            "QHeaderView { background:#2B2B35; }"
            "QTableWidget QTableCornerButton::section { background:#2B2B35; border: none; }"
            "QTableWidget:item:selected { background: #3D503D; }"
            "QTableWidget QScrollBar:vertical { background:#1a1a20; width:8px; margin:0; }"
            "QTableWidget QScrollBar::handle:vertical { background:#3a3a45; min-height:20px; border-radius:4px; }"
            "QTableWidget QScrollBar::add-line:vertical, QTableWidget QScrollBar::sub-line:vertical { background:none; height:0; }"
        )

    def _back_to_start(self):
        """Return to the startup screen - fully recursive"""
        # Clear all current data and state
        self._log_path = None
        self._last_results = {}
        self._last_stats = {}
        self._cti_stats = {}
        # Clear logged-in user and in-memory tokens so next login doesn't inherit
        try:
            self._logged_in_user = None
            for k in ['VIRUSTOTAL_API_KEY', 'ABUSEIPDB_API_KEY', 'AI_API_URL', 'AI_API_KEY']:
                if k in os.environ:
                    os.environ.pop(k, None)
            # Also clear Settings inputs if they exist
            if hasattr(self, 'vt_input'): self.vt_input.setText("")
            if hasattr(self, 'abuse_input'): self.abuse_input.setText("")
            if hasattr(self, 'ai_input'): self.ai_input.setText("")
            if hasattr(self, 'ai_key_input'): self.ai_key_input.setText("")
        except Exception:
            pass
        
        # Clear the table and output
        self.table.setRowCount(0)
        self.output.clear()
        
        # Reset path label
        self.path_label.setText("No file selected")
        
        # Hide progress indicators
        self.progress.setVisible(False)
        self.progress_label.setVisible(False)
        
        # Hide main screen and show startup screen
        self.main_screen.setVisible(False)
        self.startup_screen.setVisible(True)
        
        # Do not resize the window; let StartupScreen fill current size
        
        # Reset startup screen state completely
        self.startup_screen.status_label.setText("Ready to analyze your logs")
        self.startup_screen.file_button.setEnabled(True)
        
        # Show recent file info and quick start button if available
        if hasattr(self, '_last_file_path') and self._last_file_path:
            self.startup_screen.recent_file_label.setText(f"Last analyzed: {os.path.basename(self._last_file_path)}")
            self.startup_screen.recent_file_label.setVisible(True)
            self.startup_screen.quick_start_button.setVisible(True)
            self.startup_screen.quick_start_button.setEnabled(True)
        else:
            self.startup_screen.recent_file_label.setVisible(False)
            self.startup_screen.quick_start_button.setVisible(False)
        
        # Ensure startup screen is on top and focused
        self.startup_screen.raise_()
        self.startup_screen.setFocus()
        
        # Restart background animation if needed
        if hasattr(self.startup_screen.background, '_animation_timer'):
            if not self.startup_screen.background._animation_timer.isActive():
                self.startup_screen.background._animation_timer.start(100)

    def _save_api_tokens(self):
        """Persist API tokens to environment for current process and inform the user."""
        vt = self.vt_input.text().strip() if hasattr(self, 'vt_input') else ''
        abuse = self.abuse_input.text().strip() if hasattr(self, 'abuse_input') else ''
        ai_url = self.ai_input.text().strip() if hasattr(self, 'ai_input') else ''
        ai_key = self.ai_key_input.text().strip() if hasattr(self, 'ai_key_input') else ''
        if vt:
            os.environ['VIRUSTOTAL_API_KEY'] = vt
        if abuse:
            os.environ['ABUSEIPDB_API_KEY'] = abuse
        if ai_url:
            os.environ['AI_API_URL'] = ai_url
        if ai_key:
            os.environ['AI_API_KEY'] = ai_key
        # Also persist to DB for current user if logged in
        try:
            # Prefer the last logged-in user stored on this window
            lp = getattr(self, '_logged_in_user', None)
            if lp and isinstance(lp, tuple) and len(lp) == 2:
                u, p = lp
            else:
                u = (self.username_input.text() if hasattr(self, 'username_input') else '').strip()
                p = (self.password_input.text() if hasattr(self, 'password_input') else '').strip()
            if u and p:
                with self._get_db_conn() as conn:
                    self._ensure_users_table(conn)
                    with conn.cursor() as cur:
                        # Update existing row for this user (case-insensitive username)
                        cur.execute(
                            "UPDATE app_user_settings SET password=%s, vt_key=%s, ad_key=%s, ai_url=%s, ai_key=%s WHERE LOWER(username)=LOWER(%s)",
                            (p, vt or None, abuse or None, ai_url or None, ai_key or None, u)
                        )
                        if cur.rowcount == 0:
                            cur.execute(
                                "INSERT INTO app_user_settings (username, password, vt_key, ad_key, ai_url, ai_key) VALUES (LOWER(%s), %s, %s, %s, %s, %s)",
                                (u, p, vt or None, abuse or None, ai_url or None, ai_key or None)
                            )
                        conn.commit()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Failed to save tokens: {str(e)}")
            return
        QMessageBox.information(self, "Saved", "Tokens saved to database for this user.")

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Log File", os.getcwd(), "Log Files (*.log *.txt *.*)")
        if path:
            self._log_path = path
            self.path_label.setText(path)

    def _run(self):
        if not self._log_path:
            QMessageBox.warning(self, "No File", "Please select a log file first.")
            return
        
        # Show progress bar and reset
        self.progress.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress.setProgress(0)
        self.progress_label.setText("Initializing analysis...")
        QApplication.processEvents()
        
        try:
            is_valid, error_msg, file_content = FileValidator.validate_file_path(self._log_path)
            if not is_valid:
                raise RuntimeError(error_msg)

            # Step 1: Parse log file
            self.progress_label.setText("Parsing log file...")
            self.progress.setProgress(10)
            QApplication.processEvents()
            
            parser = LogParser()
            # Switch to streaming mode for large logs
            try:
                if os.path.getsize(self._log_path) > 5 * 1024 * 1024:
                    parsed = parser.parse_log_file(self._log_path)
                else:
                    parsed = parser.parse_log(file_content)
            except Exception:
                parsed = parser.parse_log(file_content)
            filtered = parser.filter_and_sort_ips(parsed['ips'])
            # Keep raw log entries for AI context later
            self._raw_log_entries = parsed.get('log_entries', [])

            # Step 2: Analyze behavior
            self.progress_label.setText("Analyzing behavior patterns...")
            self.progress.setProgress(25)
            QApplication.processEvents()
            
            behavior = BehaviorAnalyzer()
            behavior_results = behavior.analyze(parsed['log_entries'])

            enriched = {}
            cti_stats = {
                'total_ips': 0,
                'threat_levels': {'high': 0, 'medium': 0, 'low': 0, 'clean': 0, 'unknown': 0},
                'risk_distribution': {'high_risk': 0, 'medium_risk': 0, 'low_risk': 0, 'no_risk': 0},
                'source_availability': {'virustotal': 0, 'abuseipdb': 0},
                'suspicious_ips': [],
                'clean_ips': []
            }

            if filtered['public_ips']:
                # Step 3: CTI enrichment
                self.progress_label.setText(f"Enriching {len(filtered['public_ips'])} IPs with threat intelligence...")
                self.progress.setProgress(40)
                QApplication.processEvents()
                
                # Read keys from Settings tab first, then fallback to environment
                vt_key = (self.vt_input.text().strip() if hasattr(self, 'vt_input') else None) or os.getenv('VIRUSTOTAL_API_KEY')
                abuse_key = (self.abuse_input.text().strip() if hasattr(self, 'abuse_input') else None) or os.getenv('ABUSEIPDB_API_KEY')
                
                # VirusTotal API key will be used as provided by user
                if vt_key:
                    print(f"DEBUG: Using VirusTotal API key from Settings")
                else:
                    print(f"DEBUG: No VirusTotal API key provided")
                def append_console(msg: str):
                    try:
                        if hasattr(self, 'output'):
                            current = self.output.toPlainText()
                            self.output.setPlainText((current + "\n" + msg).strip())
                            self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())
                            QApplication.processEvents()
                    except Exception:
                        pass
                # Get scan speed setting
                speed_text = self.speed_combo.currentText()
                if "Fast" in speed_text:
                    delay = 0.0
                elif "Normal" in speed_text:
                    delay = 0.5
                elif "Slow" in speed_text:
                    delay = 1.0
                elif "Very Slow" in speed_text:
                    delay = 2.0
                else:
                    delay = 0.5
                
                cti = CTIManager(virustotal_key=vt_key, abuseipdb_key=abuse_key, progress_cb=append_console, rate_limit_delay=delay)
                enriched = cti.enrich_ips(filtered['public_ips'], behavior_results)
                cti_stats = cti.get_summary_statistics(enriched)
            else:
                            enriched = {ip: {
                'ip': ip,
                'virustotal': {},
                'abuseipdb': {},
                'behavior': behavior_results.get(ip, {}),
                'overall_threat_level': behavior_results.get(ip, {}).get('threat_level', 'unknown'),
                'risk_score': behavior_results.get(ip, {}).get('risk_score', 0)
            } for ip in parsed['ips']}
            cti_stats['total_ips'] = len(enriched)

            # Step 4: Generate statistics
            self.progress_label.setText("Generating statistics and reports...")
            self.progress.setProgress(70)
            QApplication.processEvents()
            
            log_stats = parser.get_statistics(parsed['log_entries'])
            log_stats.update(filtered)

            self._last_results = enriched
            self._last_stats = log_stats
            self._cti_stats = cti_stats
            
            # Store the enriched data
            done_msg = f"✅ Analysis complete: {len(enriched)} IPs enriched with CTI data"
            print(done_msg)
            if hasattr(self, 'output'):
                current = self.output.toPlainText()
                self.output.setPlainText((current + "\n" + done_msg).strip())

            # Step 5: Update UI
            self.progress_label.setText("Updating interface...")
            self.progress.setProgress(90)
            QApplication.processEvents()
            
            self._populate_table(enriched)
            self._write_summary(log_stats, cti_stats)
            self._update_charts_and_summary(log_stats, cti_stats, enriched)

            # Complete
            self.progress_label.setText("Analysis complete!")
            self.progress.setProgress(100)
            QApplication.processEvents()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            # Hide progress after a short delay
            QTimer.singleShot(1000, lambda: (self.progress.setVisible(False), self.progress_label.setVisible(False)))

    # Configure APIs dialog removed per request; keys are read from .env

    def _populate_table(self, enriched: Dict[str, Any]):
        # Show all public IPs (or all if public set is missing)
        public_ips = set(self._last_stats.get('public_ips', [])) if self._last_stats else set()
        candidates = [(ip, data) for ip, data in enriched.items() if (not public_ips or ip in public_ips)]

        # Apply threat filter
        filter_val = (self.filter_threat.currentText() if hasattr(self, 'filter_threat') else 'All').lower()
        if filter_val != 'all':
            candidates = [(ip, d) for ip, d in candidates if d.get('overall_threat_level', 'unknown') == filter_val]

        # Sorting
        def threat_rank(level: str) -> int:
            order = {'high': 0, 'medium': 1, 'low': 2, 'clean': 3, 'unknown': 4}
            return order.get(level or 'unknown', 4)

        sort_choice = self.sort_by.currentText() if hasattr(self, 'sort_by') else 'Sort by Risk (desc)'
        if sort_choice.startswith('Sort by Risk'):
            items = sorted(candidates, key=lambda x: int(x[1].get('risk_score', 0)), reverse=True)
        elif sort_choice == 'Sort by Threat':
            items = sorted(candidates, key=lambda x: threat_rank(x[1].get('overall_threat_level')))
        else:
            items = sorted(candidates, key=lambda x: x[0])
        self.table.setRowCount(len(items))
        for row, (ip, data) in enumerate(items):
            behavior = data.get('behavior', {})
            indicators = ", ".join(behavior.get('indicators', [])[:5])
            methods = ", ".join(behavior.get('methods', [])[:5])
            # Priority derived from threat level
            priority = {
                'high': 'P1',
                'medium': 'P2',
                'low': 'P3',
                'clean': 'P4'
            }.get(data.get('overall_threat_level', 'unknown'), 'P4')
            # AbuseIPDB confidence (if available) - format with context
            abuse_conf = data.get('abuse_confidence')
            if abuse_conf is not None:
                if abuse_conf == 0:
                    abuse_conf_str = "0% (Clean)"
                else:
                    abuse_conf_str = f"{abuse_conf}%"
            else:
                abuse_conf_str = 'N/A'
            # AbuseIPDB risk score (if available)
            abuse_data = data.get('abuseipdb', {})
            abuse_risk_score = abuse_data.get('risk_score') if abuse_data.get('status') == 'success' else 'N/A'
            # Reputation from VirusTotal if available
            vt = data.get('virustotal', {})
            reputation = vt.get('reputation') if vt.get('status') == 'success' else 'N/A'
            # Top status code from behavior statuses
            statuses = behavior.get('statuses', {})
            top_status = max(statuses.items(), key=lambda x: x[1])[0] if statuses else 'N/A'
            values = [
                ip,
                data.get('overall_threat_level', 'unknown'),
                priority,
                str(data.get('risk_score', 0)),
                abuse_conf_str,
                str(abuse_risk_score),
                str(reputation),
                top_status,
                indicators,
                methods
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

            # Row coloring based on threat level
            level = data.get('overall_threat_level', 'unknown')
            if level == 'high':
                bg = QColor(220, 20, 60, 50)
            elif level == 'medium':
                bg = QColor(255, 165, 0, 40)
            elif level == 'clean':
                bg = QColor(60, 179, 113, 40)
            else:
                bg = QColor(128, 128, 128, 25)
            for col in range(self.table.columnCount()):
                it = self.table.item(row, col)
                if it:
                    it.setBackground(bg)

    def _update_charts_and_summary(self, log_stats: Dict[str, Any], cti_stats: Dict[str, Any], enriched: Dict[str, Any]):
        # Pie chart for threat levels
        series = QPieSeries()
        tl = cti_stats.get('threat_levels', {})
        for label, color in [("high", QColor(220, 20, 60)), ("medium", QColor(255, 165, 0)), ("low", QColor(255, 215, 0)), ("clean", QColor(60, 179, 113)), ("unknown", QColor(128, 128, 128))]:
            count = int(tl.get(label, 0))
            if count > 0:
                sl = series.append(f"{label.capitalize()} ({count})", count)
                sl.setBrush(color)
                sl.setLabelVisible(True)
        series.setPieSize(0.8)
        series.setHoleSize(0.35)
        pie_chart = QChart()
        pie_chart.addSeries(series)
        pie_chart.setTitle("Threat Levels Distribution")
        title_font = QFont("Segoe UI", 12, QFont.Bold)
        pie_chart.setTitleFont(title_font)
        pie_chart.setBackgroundBrush(QColor(24, 24, 30))
        self.pie_view.setChart(pie_chart)

        # Bar chart for top IP frequency (from log)
        freq = log_stats.get('ip_frequency', {}) or {}
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
        bar_set = QBarSet("Requests")
        categories = []
        for ip, count in top:
            categories.append(ip)
            bar_set.append(int(count))
        bar_series = QBarSeries()
        bar_series.append(bar_set)
        bar_chart = QChart()
        bar_chart.addSeries(bar_series)
        bar_chart.setTitle("Top IPs by Request Count")
        bar_chart.setTitleFont(title_font)
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_y = QValueAxis()
        axis_y.setTitleText("Requests")
        axis_y.setLabelFormat("%d")
        bar_set.setLabel("Requests")
        bar_series.setLabelsVisible(True)
        bar_chart.addAxis(axis_x, Qt.AlignBottom)
        bar_chart.addAxis(axis_y, Qt.AlignLeft)
        bar_series.attachAxis(axis_x)
        bar_series.attachAxis(axis_y)
        bar_chart.setBackgroundBrush(QColor(24, 24, 30))
        self.bar_view.setChart(bar_chart)

        # One-sentence AI-style summary
        high_ips = [ip for ip, d in enriched.items() if d.get('overall_threat_level') == 'high']
        if high_ips:
            # Summarize common indicators
            indicator_counts = {}
            for ip in high_ips:
                for ind in enriched[ip].get('behavior', {}).get('indicators', []):
                    indicator_counts[ind] = indicator_counts.get(ind, 0) + 1
            top_inds = sorted(indicator_counts.items(), key=lambda x: x[1], reverse=True)
            ind_phrase = ", ".join([k.replace('_', ' ') for k, _ in top_inds[:2]]) if top_inds else "malicious behavior"
            text = f"Detected {len(high_ips)} high-risk IP(s) exhibiting {ind_phrase}; immediate containment is recommended."
        else:
            text = "No high-risk IPs detected; continue monitoring for anomalies."
        self.ai_summary.setText(text)

        # Update map markers based on enriched data
        try:
            if hasattr(self, 'map_view'):
                self.map_view.page().runJavaScript("clearMarkers();")
                
                # Country coordinates mapping with multiple cities per country
                country_cities = {
                    'US': [(40.7128, -74.0060), (34.0522, -118.2437), (41.8781, -87.6298), (29.7604, -95.3698), (33.4484, -112.0740)],
                    'CN': [(39.9042, 116.4074), (31.2304, 121.4737), (22.3193, 114.1694), (23.1291, 113.2644), (30.5728, 104.0668)],
                    'DE': [(52.5200, 13.4050), (53.5511, 9.9937), (48.1351, 11.5820), (50.1109, 8.6821), (51.2277, 6.7735)],
                    'GB': [(51.5074, -0.1278), (53.4808, -2.2426), (52.4862, -1.8904), (55.9533, -3.1883), (50.8225, -0.1372)],
                    'FR': [(48.8566, 2.3522), (45.7640, 4.8357), (43.2965, 5.3698), (50.6292, 3.0573), (47.2184, -1.5536)],
                    'JP': [(35.6762, 139.6503), (34.6937, 135.5023), (35.0116, 135.7681), (43.0642, 141.3469), (26.2124, 127.6792)],
                    'RU': [(55.7558, 37.6176), (59.9311, 30.3609), (56.8431, 60.6454), (53.2001, 50.1500), (43.1056, 131.8735)],
                    'BR': [(-23.5505, -46.6333), (-22.9068, -43.1729), (-12.9714, -38.5014), (-8.0476, -34.8770), (-25.4244, -49.2654)],
                    'IN': [(28.6139, 77.2090), (19.0760, 72.8777), (12.9716, 77.5946), (22.5726, 88.3639), (13.0827, 80.2707)],
                    'CA': [(43.6532, -79.3832), (45.5017, -73.5673), (49.2827, -123.1207), (51.0447, -114.0719), (44.6488, -63.5752)],
                    'AU': [(-33.8688, 151.2093), (-37.8136, 144.9631), (-27.4698, 153.0251), (-34.9285, 138.6007), (-31.9505, 115.8605)],
                    'IT': [(41.9028, 12.4964), (45.4642, 9.1900), (40.8518, 14.2681), (45.0703, 7.6869), (43.7696, 11.2558)],
                    'ES': [(40.4168, -3.7038), (41.3851, 2.1734), (36.7213, -4.4214), (43.2627, -2.9253), (37.3891, -5.9845)],
                    'NL': [(52.3676, 4.9041), (51.9244, 4.4777), (52.0116, 4.3571), (51.2194, 4.4025), (52.0907, 5.1214)],
                    'SE': [(59.3293, 18.0686), (57.7089, 11.9746), (55.6059, 13.0007), (59.8586, 17.6389), (63.8258, 20.2630)],
                    'NO': [(59.9139, 10.7522), (60.3913, 5.3221), (63.4305, 10.3951), (58.1467, 7.9956), (69.6492, 18.9553)],
                    'DK': [(55.6761, 12.5683), (56.1572, 10.2107), (55.4038, 10.4024), (57.0488, 9.9217), (55.3959, 10.3883)],
                    'FI': [(60.1699, 24.9384), (61.4991, 23.7871), (65.0121, 25.4651), (60.4518, 22.2666), (62.2415, 25.7209)],
                    'PL': [(52.2297, 21.0122), (50.0755, 19.9445), (51.1079, 17.0385), (54.3520, 18.6466), (50.2649, 19.0238)],
                    'CZ': [(50.0755, 14.4378), (49.1951, 16.6068), (49.7437, 13.3771), (50.2092, 15.8328), (49.5946, 17.2509)],
                    'HU': [(47.4979, 19.0402), (46.2530, 20.1414), (47.5316, 21.6273), (46.9069, 19.6898), (47.1625, 19.5033)],
                    'RO': [(44.4268, 26.1025), (46.7712, 23.6236), (45.6427, 25.5887), (47.0465, 21.9190), (45.7472, 21.2087)],
                    'BG': [(42.6977, 23.3219), (42.1354, 24.7453), (43.8564, 25.9569), (42.5048, 27.4626), (43.0757, 25.6172)],
                    'GR': [(37.9755, 23.7348), (40.6401, 22.9444), (35.3080, 25.0776), (38.2466, 21.7346), (39.0742, 21.8243)],
                    'TR': [(41.0082, 28.9784), (39.9334, 32.8597), (38.4192, 27.1287), (36.8969, 30.7133), (37.0662, 37.3833)],
                    'UA': [(50.4501, 30.5234), (49.9935, 36.2304), (46.4825, 30.7233), (48.4647, 35.0462), (49.5883, 34.5514)],
                    'BY': [(53.9006, 27.5590), (52.4345, 30.9754), (53.7098, 27.9534), (52.0884, 23.7341), (53.8930, 27.5674)],
                    'LT': [(54.6872, 25.2797), (55.1694, 23.8813), (54.8985, 23.9036), (55.7108, 21.1318), (54.8985, 23.9036)],
                    'LV': [(56.9496, 24.1052), (56.8796, 24.6032), (56.9677, 24.1052), (57.5400, 25.4242), (56.8796, 24.6032)],
                    'EE': [(59.4370, 24.7536), (58.5953, 25.0136), (59.3772, 28.1903), (58.3808, 26.7291), (58.5953, 25.0136)],
                    'IE': [(53.3498, -6.2603), (51.8985, -8.4756), (52.2689, -9.0518), (53.2707, -9.0568), (54.5973, -5.9301)],
                    'PT': [(38.7223, -9.1393), (41.1579, -8.6291), (40.6405, -8.6538), (37.0194, -7.9322), (39.7436, -8.8071)],
                    'CH': [(46.9481, 7.4474), (47.3769, 8.5417), (46.2044, 6.1432), (47.0502, 8.3093), (46.5197, 6.6323)],
                    'AT': [(48.2082, 16.3738), (47.0707, 15.4395), (47.8095, 13.0550), (46.6249, 14.3059), (48.3069, 14.2858)],
                    'BE': [(50.8503, 4.3517), (51.2194, 4.4025), (50.6292, 3.0573), (51.2086, 3.2242), (50.8503, 4.3517)],
                    'LU': [(49.6116, 6.1319), (49.8153, 6.1296), (49.6116, 6.1319), (49.8153, 6.1296), (49.6116, 6.1319)],
                    'SK': (48.6690, 19.6990), 'SI': (46.1512, 14.9955), 'HR': (45.1000, 15.2000),
                    'RS': (44.0165, 21.0059), 'BA': (43.9159, 17.6791), 'ME': (42.7087, 19.3744),
                    'MK': (41.6086, 21.7453), 'AL': (41.1533, 20.1683), 'XK': (42.6026, 20.9030),
                    'MD': (47.4116, 28.3699), 'IS': (64.9631, -19.0208), 'MT': (35.9375, 14.3754),
                    'CY': (35.1264, 33.4299), 'IL': (31.0461, 34.8516), 'LB': (33.8547, 35.8623),
                    'SY': (34.8021, 38.9968), 'IQ': (33.2232, 43.6793), 'IR': (32.4279, 53.6880),
                    'AF': (33.9391, 67.7100), 'PK': (30.3753, 69.3451), 'BD': (23.6850, 90.3563),
                    'LK': (7.8731, 80.7718), 'MV': (3.2028, 73.2207), 'NP': (28.3949, 84.1240),
                    'BT': (27.5142, 90.4336), 'MM': (21.9162, 95.9560), 'TH': (15.8700, 100.9925),
                    'LA': (19.8563, 102.4955), 'VN': (14.0583, 108.2772), 'KH': (12.5657, 104.9910),
                    'MY': (4.2105, 101.9758), 'SG': (1.3521, 103.8198), 'BN': (4.5353, 114.7277),
                    'ID': (-0.7893, 113.9213), 'PH': (12.8797, 121.7740), 'TW': (23.6978, 120.9605),
                    'KR': (35.9078, 127.7669), 'KP': (40.3399, 127.5101), 'MN': (46.8625, 103.8467),
                    'KZ': (48.0196, 66.9237), 'UZ': (41.3775, 64.5853), 'TM': (38.9697, 59.5563),
                    'TJ': (38.8610, 71.2761), 'KG': (41.2044, 74.7661), 'GE': (42.3154, 43.3569),
                    'AM': (40.0691, 45.0382), 'AZ': (40.1431, 47.5769), 'SA': (23.8859, 45.0792),
                    'AE': (23.4241, 53.8478), 'QA': (25.3548, 51.1839), 'BH': (25.9304, 50.6378),
                    'KW': (29.3117, 47.4818), 'OM': (21.4735, 55.9754), 'YE': (15.5527, 48.5164),
                    'JO': (30.5852, 36.2384), 'PS': (31.9522, 35.2332), 'EG': (26.0975, 30.0444),
                    'LY': (26.3351, 17.2283), 'TN': (33.8869, 9.5375), 'DZ': (28.0339, 1.6596),
                    'MA': (31.6295, -7.9811), 'SD': (12.8628, 30.2176), 'SS': (6.8770, 31.3070),
                    'ET': (9.1450, 40.4897), 'ER': (15.1794, 39.7823), 'DJ': (11.8251, 42.5903),
                    'SO': (5.1521, 46.1996), 'KE': (-0.0236, 37.9062), 'UG': (1.3733, 32.2903),
                    'TZ': (-6.3690, 34.8888), 'RW': (-1.9403, 29.8739), 'BI': (-3.3731, 29.9189),
                    'CD': (-4.0383, 21.7587), 'CF': (6.6111, 20.9394), 'TD': (15.4542, 18.7322),
                    'CM': (7.3697, 12.3547), 'NG': (9.0820, 8.6753), 'NE': (17.6078, 8.0817),
                    'BF': (12.2383, -1.5616), 'ML': (17.5707, -3.9962), 'SN': (14.4974, -14.4524),
                    'GM': (13.4432, -15.3101), 'GW': (11.8037, -15.1804), 'GN': (9.6412, -9.6966),
                    'SL': (8.4606, -11.7799), 'LR': (6.4281, -9.4295), 'CI': (7.5400, -5.5471),
                    'GH': (7.9465, -1.0232), 'TG': (8.6195, 0.8248), 'BJ': (9.3077, 2.3158),
                    'NG': (9.0820, 8.6753), 'GA': (-0.8037, 11.6094), 'CG': (-0.2280, 15.8277),
                    'AO': (-11.2027, 17.8739), 'ZM': (-13.1339, 27.8493), 'ZW': (-19.0154, 29.1549),
                    'BW': (-22.3285, 24.6849), 'NA': (-22.9576, 18.4904), 'ZA': (-30.5595, 22.9375),
                    'LS': (-29.6100, 28.2336), 'SZ': (-26.5225, 31.4659), 'MZ': (-18.6657, 35.5296),
                    'MG': (-18.7669, 46.8691), 'MU': (-20.3484, 57.5522), 'SC': (-4.6796, 55.4919),
                    'KM': (-11.8750, 43.8722), 'YT': (-12.8275, 45.1662), 'RE': (-21.1151, 55.5364),
                    'MX': (23.6345, -102.5528), 'GT': (15.7835, -90.2308), 'BZ': (17.1899, -88.4976),
                    'SV': (13.7942, -88.8965), 'HN': (15.2000, -86.2419), 'NI': (12.8654, -85.2072),
                    'CR': (9.7489, -83.7534), 'PA': (8.5380, -80.7821), 'CU': (21.5218, -77.7812),
                    'JM': (18.1096, -77.2975), 'HT': (18.9712, -72.2852), 'DO': (18.7357, -70.1627),
                    'PR': (18.2208, -66.5901), 'VI': (18.3358, -64.8963), 'AG': (17.0608, -61.7964),
                    'KN': (17.3578, -62.7830), 'LC': (13.9094, -60.9789), 'VC': (12.9843, -61.2872),
                    'BB': (13.1939, -59.5432), 'GD': (12.2626, -61.6049), 'TT': (10.6918, -61.2225),
                    'AR': (-38.4161, -63.6167), 'UY': (-32.5228, -55.7658), 'PY': (-23.4425, -58.4438),
                    'BO': (-16.2902, -63.5887), 'PE': (-9.1900, -75.0152), 'EC': (-1.8312, -78.1834),
                    'CO': (4.5709, -74.2973), 'VE': (6.4238, -66.5897), 'GY': (4.8604, -58.9302),
                    'SR': (3.9193, -56.0278), 'GF': (3.9339, -53.1258), 'CL': (-35.6751, -71.5430),
                    'FK': (-51.7963, -59.5236), 'GS': (-54.4296, -36.5879), 'NZ': (-40.9006, 174.8860),
                    'NC': (-20.9043, 165.6180), 'VU': (-15.3767, 166.9592), 'SB': (-9.6457, 160.1562),
                    'PG': (-6.3150, 143.9555), 'FJ': (-16.5785, 179.4144), 'TO': (-21.1789, -175.1982),
                    'WS': (-13.7590, -172.1046), 'AS': (-14.2710, -170.1322), 'CK': (-21.2367, -159.7777),
                    'NU': (-19.0544, -169.8672), 'TK': (-8.9674, -171.8559), 'TV': (-7.1095, 177.6493),
                    'KI': (-3.3704, -168.7340), 'NR': (-0.5228, 166.9315), 'PW': (7.5150, 134.5825),
                    'FM': (7.4256, 150.5508), 'MH': (7.1315, 171.1845), 'MP': (17.3308, 145.3846),
                    'GU': (13.4443, 144.7937), 'VI': (18.3358, -64.8963), 'PR': (18.2208, -66.5901)
                }
                
                import requests
                import time
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                # Debug: Print enriched data info
                print(f"DEBUG: Processing {len(enriched)} IPs for map markers")
                
                def get_ip_location(ip):
                    """Get geolocation for a single IP"""
                    try:
                        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
                        if response.status_code == 200:
                            geo_data = response.json()
                            if geo_data.get('status') == 'success':
                                return {
                                    'ip': ip,
                                    'lat': geo_data.get('lat'),
                                    'lng': geo_data.get('lon'),
                                    'city': geo_data.get('city', ''),
                                    'country': geo_data.get('country', ''),
                                    'success': True
                                }
                        return {'ip': ip, 'success': False}
                    except Exception as e:
                        return {'ip': ip, 'success': False, 'error': str(e)}
                
                # Process IPs in parallel (max 5 concurrent requests to avoid rate limits)
                markers_added = 0
                with ThreadPoolExecutor(max_workers=5) as executor:
                    # Submit all IP lookups
                    future_to_ip = {executor.submit(get_ip_location, ip): ip for ip in enriched.keys()}
                    
                    for future in as_completed(future_to_ip):
                        result = future.result()
                        ip = result['ip']
                        data = enriched[ip]
                        
                        if result.get('success'):
                            lat = result['lat']
                            lng = result['lng']
                            city = result['city']
                            country = result['country']
                            
                            print(f"DEBUG: IP {ip} -> {city}, {country} ({lat}, {lng})")
                            
                            threat = (data.get('overall_threat_level') or 'unknown').lower()
                            color = '#22c55e'
                            if threat == 'high':
                                color = '#ef4444'
                            elif threat == 'medium':
                                color = '#f59e0b'
                            elif threat == 'low':
                                color = '#3b82f6'
                            
                            label = f"{ip} - {city}, {country}"
                            js = f"addMarker({lat}, {lng}, '{color}', '{label}');"
                            self.map_view.page().runJavaScript(js)
                            markers_added += 1
                            print(f"DEBUG: Added marker for {ip}")
                        else:
                            print(f"DEBUG: Geolocation failed for {ip}")
                
                print(f"DEBUG: Total markers added: {markers_added}")
        except Exception:
            pass

    def _write_summary(self, log_stats: Dict[str, Any], cti_stats: Dict[str, Any]):
        lines = []
        lines.append(f"Total entries: {log_stats.get('total_entries', 0)}")
        lines.append(f"Unique IPs: {log_stats.get('total_count', 0)} (public {log_stats.get('public_count', 0)}, private {log_stats.get('private_count', 0)})")
        tl = cti_stats.get('threat_levels', {})
        lines.append(f"Threat levels - High:{tl.get('high',0)} Medium:{tl.get('medium',0)} Low:{tl.get('low',0)} Clean:{tl.get('clean',0)} Unknown:{tl.get('unknown',0)}")
        self.output.setPlainText("\n".join(lines))

    def _on_table_click(self, row: int, col: int):
        try:
            ip_item = self.table.item(row, 0)
            if not ip_item:
                return
            ip = ip_item.text()
            data = self._last_results.get(ip, {})
            if not data:
                # Try to find the IP in a different way
                for stored_ip, stored_data in self._last_results.items():
                    if stored_ip == ip:
                        data = stored_data
                        break
                if not data:
                    return
            
            # Data found, proceed with display
            # Fetch detailed VirusTotal information
            self.progress_label.setText(f"Fetching detailed analysis for {ip}...")
            self.progress.setVisible(True)
            self.progress_label.setVisible(True)
            QApplication.processEvents()

            def h(text: str) -> str:
                return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            threat = data.get('overall_threat_level', 'unknown')
            risk_score = data.get('risk_score', 0)
            risk = str(risk_score)
            
            # Override threat level if risk > 70%
            if risk_score > 70:
                threat = 'high'
                threat_display = 'HIGH THREAT'
            else:
                threat_display = threat.upper()
            behavior = data.get('behavior', {})
            indicators = ", ".join(behavior.get('indicators', [])) or '—'
            methods = ", ".join(behavior.get('methods', [])) or '—'
            statuses = behavior.get('statuses', {})
            statuses_html = ''.join([f"<li>{h(k)}: {h(str(v))}</li>" for k, v in sorted(statuses.items())]) or '<li>—</li>'

            # Fetch detailed VirusTotal analysis
            vt_detailed = {}
            vt_key = os.getenv('VIRUSTOTAL_API_KEY')
            if vt_key:
                from cti_apis.virustotal import VirusTotalAPI
                vt_api = VirusTotalAPI(vt_key)
                vt_detailed = vt_api.get_detailed_analysis(ip)
            
            vt = data.get('virustotal', {})
            vt_stats = vt.get('analysis_stats', {})
            
            # Use detailed VT data if available, otherwise fall back to basic data
            if vt_detailed.get('status') == 'success':
                # Format detailed VirusTotal information
                last_analysis = vt_detailed.get('last_analysis_date', 0)
                analysis_date = f"{last_analysis}" if last_analysis else 'Unknown'
                
                stats = vt_detailed.get('last_analysis_stats', {})
                malicious = stats.get('malicious', 0)
                suspicious = stats.get('suspicious', 0)
                harmless = stats.get('harmless', 0)
                undetected = stats.get('undetected', 0)
                
                # Format crowdsourced context
                context = vt_detailed.get('crowdsourced_context', [])
                context_html = ""
                if context:
                    context_items = []
                    for item in context[:5]:  # Show first 5 items
                        title = item.get('title', 'Unknown')
                        severity = item.get('severity', 'unknown')
                        context_items.append(f"{h(title)} ({h(severity)})")
                    context_html = f"<li>Recent Context: {h(', '.join(context_items))}</li>"
                
                vt_html = (
                    f"<li>Reputation Score: {h(str(vt_detailed.get('reputation', 'N/A')))}</li>"
                    f"<li>Last Analysis: {h(analysis_date)}</li>"
                    f"<li>Analysis Stats - Malicious: {h(str(malicious))}, Suspicious: {h(str(suspicious))}, Harmless: {h(str(harmless))}, Undetected: {h(str(undetected))}</li>"
                    f"<li>Network: {h(vt_detailed.get('network', 'Unknown'))}</li>"
                    f"<li>ASN: {h(str(vt_detailed.get('asn', 'Unknown')))} - {h(vt_detailed.get('as_owner', 'Unknown'))}</li>"
                    f"<li>Country: {h(vt_detailed.get('country', 'Unknown'))} ({h(vt_detailed.get('continent', 'Unknown'))})</li>"
                    f"<li>Registry: {h(vt_detailed.get('regional_internet_registry', 'Unknown'))}</li>"
                    f"{context_html}"
                )
            elif vt.get('status') == 'success' or (vt.get('status') is None and vt.get('reputation') is not None):
                vt_html = (
                    f"<li>Reputation: {h(str(vt.get('reputation', 'N/A')))}</li>"
                    f"<li>Threat: {h(vt.get('threat_level', 'unknown'))}</li>"
                    f"<li>Analysis - Malicious: {h(str(vt_stats.get('malicious', 0)))}, Suspicious: {h(str(vt_stats.get('suspicious', 0)))}, Harmless: {h(str(vt_stats.get('harmless', 0)))}</li>"
                )
            else:
                error_msg = vt.get('message', 'Unknown error')
                vt_html = f'<li>No VT data - {h(error_msg)}</li>'

            abuse = data.get('abuseipdb', {})
            # Check if we have AbuseIPDB data (status can be 'success' or None if data exists)
            if abuse.get('status') == 'success' or (abuse.get('status') is None and abuse.get('abuse_confidence') is not None):
                risk_assessment = abuse.get('risk_assessment', {})
                categories = abuse.get('categories', {})
                categories_html = ', '.join([f"{h(k)} ({v})" for k, v in categories.items()]) if categories else 'None'
                
                # Format abuse confidence with better context
                abuse_conf = abuse.get('abuse_confidence', 0)
                if abuse_conf == 0:
                    abuse_conf_text = "0% (Clean - No abuse reports)"
                else:
                    abuse_conf_text = f"{abuse_conf}%"
                
                abuse_html = (
                    f"<li>Abuse Confidence: {h(abuse_conf_text)}</li>"
                    f"<li>Risk Score: {h(str(abuse.get('risk_score', 'N/A')))}/100</li>"
                    f"<li>Severity: {h(risk_assessment.get('severity', 'Unknown'))}</li>"
                    f"<li>Total Reports: {h(str(abuse.get('total_reports', 0)))}</li>"
                    f"<li>Distinct Users: {h(str(abuse.get('distinct_users', 0)))}</li>"
                    f"<li>Threat Categories: {h(categories_html)}</li>"
                    f"<li>Risk Factors: {h(', '.join(risk_assessment.get('risk_factors', [])) or 'None')}</li>"
                    f"<li>Recommendations: {h(', '.join(risk_assessment.get('recommendations', [])) or 'None')}</li>"
                )
            else:
                abuse_html = f'<li>No AbuseIPDB data - {h(abuse.get("message", "Unknown error"))}</li>'

            # Talos removed - no longer used

            vt_link = f"https://www.virustotal.com/gui/ip-address/{h(ip)}"
            abuse_link = f"https://www.abuseipdb.com/check/{h(ip)}"

            # Get additional network information from CTI data
            vt_metadata = vt.get('metadata', {})
            abuse_metadata = abuse.get('metadata', {})
            
            # Network information
            country_code = abuse_metadata.get('country_code') or vt_metadata.get('country_code', 'Unknown')
            country_name = abuse_metadata.get('country_name') or vt_metadata.get('country_name', 'Unknown')
            isp = abuse_metadata.get('isp') or vt_metadata.get('isp', 'Unknown')
            domain = abuse_metadata.get('domain') or vt_metadata.get('domain', 'Unknown')
            usage_type = abuse_metadata.get('usage_type') or vt_metadata.get('usage_type', 'Unknown')
            
            html = f"""
<div style='font-family: Segoe UI, sans-serif; color:#D0D0D0;'>
  <h3 style='margin:0 0 8px 0;'>IP Details: {h(ip)}</h3>
  <p style='margin:0 0 6px 0;'>Threat: <b>{h(threat_display)}</b> &nbsp; • &nbsp; Risk: <b>{h(risk)}%</b></p>
  
  <p style='margin:6px 0 4px 0;'><b>Network Information</b></p>
  <ul style='margin:0 0 10px 16px;'>
    <li>Country: {h(country_name)} ({h(country_code)})</li>
    <li>ISP: {h(isp)}</li>
    <li>Domain: {h(domain)}</li>
    <li>Usage Type: {h(usage_type)}</li>
  </ul>
  
  <p style='margin:6px 0 4px 0;'><b>Behavioral Analysis</b></p>
  <ul style='margin:0 0 10px 16px;'>
    <li>Indicators: {h(indicators)}</li>
    <li>Methods: {h(methods)}</li>
  </ul>
  
  <p style='margin:6px 0 4px 0;'><b>Status Codes</b></p>
  <ul style='margin:0 0 10px 16px;'>
    {statuses_html}
  </ul>
  
  <p style='margin:6px 0 4px 0;'><b>VirusTotal Analysis</b></p>
  <ul style='margin:0 0 10px 16px;'>
    {vt_html}
  </ul>
  
  <p style='margin:6px 0 4px 0;'><b>AbuseIPDB Analysis</b></p>
  <ul style='margin:0 0 10px 16px;'>
    {abuse_html}
  </ul>
  
  <p style='margin:10px 0 0 0;'>External Links: 
    <a href='{vt_link}' target='_blank'>VirusTotal Report</a> &nbsp;|&nbsp; 
    <a href='{abuse_link}' target='_blank'>AbuseIPDB Report</a>
  </p>
</div>
"""
            self.output.setHtml(html)
            # Send relevant log lines for this IP to AI (if configured)
            try:
                ai_url = os.getenv('AI_API_URL')
                if ai_url:
                    client = AIClient()
                    # Collect exact raw log lines that contain this IP
                    lines = []
                    entries_source = getattr(self, '_raw_log_entries', None) or self._last_stats.get('log_entries', []) or []
                    for entry in entries_source:
                        content = entry.get('content') if isinstance(entry, dict) else None
                        if content and ip in content:
                            lines.append(content)
                    logs_text = "\n".join(lines) if lines else f"No raw log lines captured for {ip}."
                    self.ai_output.setPlainText("Sending logs to AI…")
                    QApplication.processEvents()
                    ai_resp = client.summarize_ip_logs(ip, logs_text)
                    self._set_ai_output(ai_resp)
                    
                    # Save to history
                    self._save_to_history(ip, threat, risk_score, ai_resp, html)
                else:
                    self._set_ai_output("AI_API_URL is not set. Configure your AI endpoint to enable this pane.")
                    # Save to history even without AI
                    self._save_to_history(ip, threat, risk_score, "No AI analysis available", html)
            except Exception as e:
                self._set_ai_output(f"AI error: {str(e)}")
                # Save to history even with AI error
                self._save_to_history(ip, threat, risk_score, f"AI error: {str(e)}", html)
            
            # Hide progress bar after completion
            self.progress.setVisible(False)
            self.progress_label.setVisible(False)
            
        except Exception as e:
            self.output.setPlainText(str(e))
            # Hide progress bar on error
            self.progress.setVisible(False)
            self.progress_label.setVisible(False)

    def _show_export_menu(self):
        """Show export format selection menu"""
        if not self._last_results:
            QMessageBox.information(self, "No Data", "Run analysis before exporting.")
            return
        
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        # Add export options
        excel_action = menu.addAction("📊 Excel (.xlsx)")
        excel_action.triggered.connect(lambda: self._export_report('excel'))
        
        markdown_action = menu.addAction("📝 Markdown (.md)")
        markdown_action.triggered.connect(lambda: self._export_report('markdown'))
        
        docx_action = menu.addAction("📄 Word Document (.docx)")
        docx_action.triggered.connect(lambda: self._export_report('docx'))
        
        txt_action = menu.addAction("📋 Text File (.txt)")
        txt_action.triggered.connect(lambda: self._export_report('txt'))
        
        pdf_action = menu.addAction("📑 PDF Document (.pdf)")
        pdf_action.triggered.connect(lambda: self._export_report('pdf'))
        
        # Show menu at cursor position
        menu.exec(self.cursor().pos())
    
    def _export_report(self, format_type: str):
        """Export report in specified format"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # File dialog for save location
            file_dialog = QFileDialog()
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)
            
            # Set default filename and filter based on format
            if format_type == 'excel':
                file_dialog.setNameFilter("Excel Files (*.xlsx)")
                default_name = f"cti_report_{timestamp}.xlsx"
            elif format_type == 'markdown':
                file_dialog.setNameFilter("Markdown Files (*.md)")
                default_name = f"cti_report_{timestamp}.md"
            elif format_type == 'docx':
                file_dialog.setNameFilter("Word Documents (*.docx)")
                default_name = f"cti_report_{timestamp}.docx"
            elif format_type == 'txt':
                file_dialog.setNameFilter("Text Files (*.txt)")
                default_name = f"cti_report_{timestamp}.txt"
            elif format_type == 'pdf':
                file_dialog.setNameFilter("PDF Files (*.pdf)")
                default_name = f"cti_report_{timestamp}.pdf"
            else:
                default_name = f"cti_report_{timestamp}.txt"
            
            file_dialog.selectFile(default_name)
            
            if file_dialog.exec():
                file_path = file_dialog.selectedFiles()[0]
                self._generate_report_file(file_path, format_type)
                QMessageBox.information(self, "Export Successful", f"Report exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export report:\n{str(e)}")
    
    def _generate_report_file(self, file_path: str, format_type: str):
        """Generate report file in specified format"""
        from report_generator import ReportGenerator
        from ai_client import AIClient
        
        # Collect all tab data
        tab_data = {
            'results_data': self._last_results,
            'statistics_data': {
                'ai_summary': self.ai_summary.text() if hasattr(self, 'ai_summary') else '',
                'log_stats': self._last_stats,
                'cti_stats': self._cti_stats
            },
            'ai_output': self.ai_output.toPlainText() if hasattr(self, 'ai_output') else '',
            'map_data': self._get_map_data() if hasattr(self, 'map_view') else {}
        }
        
        # Generate comprehensive AI report
        try:
            client = AIClient()
            ai_comprehensive_report = client.generate_comprehensive_report(
                log_stats=self._last_stats,
                enriched_data=self._last_results,
                cti_stats=self._cti_stats,
                statistics_data=tab_data['statistics_data'],
                map_data=tab_data['map_data'],
                ai_output=tab_data['ai_output']
            )
            
            # Add AI comprehensive report to tab_data
            tab_data['ai_comprehensive_report'] = ai_comprehensive_report
            
        except Exception as e:
            print(f"AI report generation failed: {e}")
            tab_data['ai_comprehensive_report'] = "AI report generation failed. Using standard report format."
        
        rg = ReportGenerator()
        
        if format_type == 'excel':
            rg.generate_excel_report(self._last_stats, self._last_results, self._cti_stats, file_path, tab_data)
        elif format_type == 'markdown':
            rg.generate_markdown_report(self._last_stats, self._last_results, self._cti_stats, file_path, tab_data)
        elif format_type == 'docx':
            rg.generate_docx_report(self._last_stats, self._last_results, self._cti_stats, file_path, tab_data)
        elif format_type == 'txt':
            rg.generate_text_report(self._last_stats, self._last_results, self._cti_stats, file_path, tab_data)
        elif format_type == 'pdf':
            rg.generate_pdf_report(self._last_stats, self._last_results, self._cti_stats, file_path, tab_data)
    
    def _get_map_data(self):
        """Extract map data for reports"""
        try:
            # Get map markers data from JavaScript
            map_data = {
                'markers': [],
                'total_markers': 0
            }
            
            # Try to get marker count from the map
            if hasattr(self, 'map_view'):
                # This would require JavaScript execution to get actual marker data
                # For now, we'll estimate based on enriched data
                map_data['total_markers'] = len(self._last_results) if self._last_results else 0
                
                # Add marker information based on enriched data
                for ip, data in self._last_results.items():
                    threat = data.get('overall_threat_level', 'unknown')
                    map_data['markers'].append({
                        'ip': ip,
                        'threat_level': threat,
                        'risk_score': data.get('risk_score', 0)
                    })
            
            return map_data
        except Exception:
            return {'markers': [], 'total_markers': 0}
    
    def _convert_markdown_to_html(self, text: str) -> str:
        """Convert basic markdown to HTML"""
        if not text:
            return text
        
        # Convert headers (# ## ###)
        text = re.sub(r'^### (.*)$', r'<h3 style="color:#E6E6E6; margin:8px 0 4px 0;">\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*)$', r'<h2 style="color:#E6E6E6; margin:10px 0 6px 0;">\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.*)$', r'<h1 style="color:#E6E6E6; margin:12px 0 8px 0;">\1</h1>', text, flags=re.MULTILINE)
        
        # Convert bold text (**text** or __text__)
        text = re.sub(r'\*\*(.*?)\*\*', r'<b style="color:#F59E0B;">\1</b>', text)
        text = re.sub(r'__(.*?)__', r'<b style="color:#F59E0B;">\1</b>', text)
        
        # Convert italic text (*text* or _text_)
        text = re.sub(r'\*(.*?)\*', r'<i style="color:#D1D5DB;">\1</i>', text)
        text = re.sub(r'_(.*?)_', r'<i style="color:#D1D5DB;">\1</i>', text)
        
        # Convert bullet points (- or *)
        text = re.sub(r'^- (.*)$', r'<li style="margin:2px 0;">\1</li>', text, flags=re.MULTILINE)
        text = re.sub(r'^\* (.*)$', r'<li style="margin:2px 0;">\1</li>', text, flags=re.MULTILINE)
        
        # Wrap consecutive list items in <ul>
        text = re.sub(r'(<li.*?</li>\s*)+', lambda m: f'<ul style="margin:4px 0; padding-left:20px;">{m.group()}</ul>', text)
        
        # Convert line breaks to <br>
        text = text.replace('\n', '<br>')
        
        return text
    
    def _save_to_history(self, ip: str, threat_level: str, risk_score: int, ai_analysis: str, ip_details: str):
        """Save IP analysis to history database - update if exists, insert if new"""
        try:
            if not hasattr(self, '_logged_in_user') or not self._logged_in_user:
                return
            
            username = self._logged_in_user[0] if isinstance(self._logged_in_user, tuple) else str(self._logged_in_user)
            
            with self._get_db_conn() as conn:
                with conn.cursor() as cur:
                    # Check if entry already exists for this user and IP
                    cur.execute("""
                        SELECT id FROM ip_history 
                        WHERE username = %s AND ip_address = %s
                        ORDER BY timestamp DESC LIMIT 1
                    """, (username, ip))
                    existing = cur.fetchone()
                    
                    if existing:
                        # Update existing entry
                        cur.execute("""
                            UPDATE ip_history 
                            SET threat_level = %s, risk_score = %s, ai_analysis = %s, ip_details = %s, timestamp = CURRENT_TIMESTAMP
                            WHERE username = %s AND ip_address = %s
                        """, (threat_level, risk_score, ai_analysis, ip_details, username, ip))
                        print(f"DEBUG: Updated history for {ip}")
                    else:
                        # Insert new entry
                        cur.execute("""
                            INSERT INTO ip_history (username, ip_address, threat_level, risk_score, ai_analysis, ip_details)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (username, ip, threat_level, risk_score, ai_analysis, ip_details))
                        print(f"DEBUG: Created new history entry for {ip}")
                    
                    conn.commit()
            
            # Refresh history table
            self._load_history()
            
        except Exception as e:
            print(f"Error saving to history: {e}")
    
    def _load_history(self):
        """Load history from database and populate table"""
        try:
            if not hasattr(self, '_logged_in_user') or not self._logged_in_user:
                print("DEBUG: No logged in user found")
                return
            
            username = self._logged_in_user[0] if isinstance(self._logged_in_user, tuple) else str(self._logged_in_user)
            print(f"DEBUG: Loading history for user: {username}")
            
            with self._get_db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT ip_address, threat_level, risk_score, ai_analysis, timestamp
                        FROM ip_history 
                        WHERE username = %s 
                        ORDER BY timestamp DESC
                    """, (username,))
                    history_data = cur.fetchall()
            
            print(f"DEBUG: Found {len(history_data)} history entries")
            
            # Clear and populate table
            self.history_table.setRowCount(len(history_data))
            
            for row_idx, record in enumerate(history_data):
                ip = record['ip_address'] if isinstance(record, dict) else record[0]
                threat = record['threat_level'] if isinstance(record, dict) else record[1]
                risk = record['risk_score'] if isinstance(record, dict) else record[2]
                ai_analysis = record['ai_analysis'] if isinstance(record, dict) else record[3]
                timestamp = record['timestamp'] if isinstance(record, dict) else record[4]
                
                # Format timestamp
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "Unknown"
                
                # Truncate AI analysis for display
                ai_preview = ai_analysis[:50] + "..." if ai_analysis and len(ai_analysis) > 50 else (ai_analysis or "No analysis")
                
                self.history_table.setItem(row_idx, 0, QTableWidgetItem(ip))
                self.history_table.setItem(row_idx, 1, QTableWidgetItem(threat or "Unknown"))
                self.history_table.setItem(row_idx, 2, QTableWidgetItem(timestamp_str))
                self.history_table.setItem(row_idx, 3, QTableWidgetItem(ai_preview))
                
        except Exception as e:
            print(f"Error loading history: {e}")
    
    def _on_history_click(self, row: int, column: int):
        """Handle history table click to show details"""
        try:
            if row < 0 or row >= self.history_table.rowCount():
                return
            
            ip = self.history_table.item(row, 0).text()
            threat = self.history_table.item(row, 1).text()
            timestamp_str = self.history_table.item(row, 2).text()
            
            print(f"DEBUG: Clicked on row {row}, IP: {ip}, Timestamp: {timestamp_str}")
            
            # Get full details from database
            username = self._logged_in_user[0] if isinstance(self._logged_in_user, tuple) else str(self._logged_in_user)
            
            with self._get_db_conn() as conn:
                with conn.cursor() as cur:
                    # Use a simpler query - just get the most recent entry for this IP
                    cur.execute("""
                        SELECT ip_details, ai_analysis, risk_score, timestamp
                        FROM ip_history 
                        WHERE username = %s AND ip_address = %s
                        ORDER BY timestamp DESC LIMIT 1
                    """, (username, ip))
                    record = cur.fetchone()
            
            if record:
                ip_details = record['ip_details'] if isinstance(record, dict) else record[0]
                ai_analysis = record['ai_analysis'] if isinstance(record, dict) else record[1]
                risk_score = record['risk_score'] if isinstance(record, dict) else record[2]
                db_timestamp = record['timestamp'] if isinstance(record, dict) else record[3]
                
                print(f"DEBUG: Found record with details length: {len(ip_details) if ip_details else 0}")
                
                # Convert AI analysis from markdown to HTML
                ai_html = self._convert_markdown_to_html(ai_analysis) if ai_analysis else '<p style="color:#9CA3AF;">No AI analysis available</p>'
                
                # Format details for display with HTML styling
                details_text = f"""
<div style='font-family: Segoe UI, sans-serif; color:#D0D0D0; padding: 10px;'>
  <h3 style='margin:0 0 8px 0; color:#E6E6E6;'>IP Address: {ip}</h3>
  <p style='margin:0 0 6px 0;'>Threat Level: <b style='color:#ef4444;'>{threat.upper()}</b> &nbsp; • &nbsp; Risk Score: <b style='color:#f59e0b;'>{risk_score}%</b></p>
  <p style='margin:0 0 10px 0; color:#9CA3AF;'>Timestamp: {timestamp_str}</p>
  
  <div style='margin:15px 0;'>
    <h4 style='margin:0 0 8px 0; color:#E6E6E6; border-bottom: 1px solid #374151; padding-bottom: 4px;'>IP DETAILS</h4>
    <div style='background: rgba(0,0,0,0.2); padding: 10px; border-radius: 6px; margin: 8px 0;'>
      {ip_details or '<p style="color:#9CA3AF;">No details available</p>'}
    </div>
  </div>
  
  <div style='margin:15px 0;'>
    <h4 style='margin:0 0 8px 0; color:#E6E6E6; border-bottom: 1px solid #374151; padding-bottom: 4px;'>AI ANALYSIS</h4>
    <div style='background: rgba(0,0,0,0.2); padding: 10px; border-radius: 6px; margin: 8px 0;'>
      {ai_html}
    </div>
  </div>
</div>
"""
                
                # Use setHtml instead of setPlainText to render HTML properly
                self.history_details.setHtml(details_text)
                print("DEBUG: Details set in history_details widget")
            else:
                print("DEBUG: No record found in database")
                self.history_details.setPlainText("No details found for this entry.")
            
        except Exception as e:
            print(f"Error loading history details: {e}")
            self.history_details.setPlainText(f"Error loading details: {str(e)}")
    
    def _clear_history(self):
        """Clear all history for current user"""
        try:
            if not hasattr(self, '_logged_in_user') or not self._logged_in_user:
                return
            
            reply = QMessageBox.question(
                self, 
                "Clear History", 
                "Are you sure you want to clear all history entries? This action cannot be undone.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                username = self._logged_in_user[0] if isinstance(self._logged_in_user, tuple) else str(self._logged_in_user)
                
                with self._get_db_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM ip_history WHERE username = %s", (username,))
                        conn.commit()
                
                # Clear table and details
                self.history_table.setRowCount(0)
                self.history_details.setPlainText("History cleared.")
                
                QMessageBox.information(self, "History Cleared", "All history entries have been cleared.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear history: {str(e)}")


def launch_gui():
    app = QApplication(sys.argv)
    win = DarkWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    launch_gui()


