import sys
import os
import json
import datetime
from urllib.parse import quote_plus

from PyQt6.QtCore import QUrl, Qt, QPoint, QSize, QStandardPaths
from PyQt6.QtGui import QIcon, QFont, QKeySequence, QShortcut, QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QMenu, QTabBar, QStackedWidget, QSizePolicy,
    QDialog, QLabel, QListWidget, QListWidgetItem, QDialogButtonBox,
    QMessageBox, QComboBox, QFormLayout, QCheckBox, QScrollArea,
    QFrame, QSplitter, QTextEdit
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings, QWebEngineDownloadRequest
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter


SEARCH_ENGINE_FILE = r"D:\Zitx Vexaura\search-engine.html"
LOGO_FILE         = r"D:\Zitx Vexaura\vexaura-logo.png"
DATA_DIR          = r"D:\Zitx Vexaura\Zitx Vexaura"
FAVORITES_FILE    = os.path.join(DATA_DIR, "favorites.json")
HISTORY_FILE      = os.path.join(DATA_DIR, "history.json")
DOWNLOADS_FILE    = os.path.join(DATA_DIR, "downloads.json")
SETTINGS_FILE     = os.path.join(DATA_DIR, "settings.json")

HOME_URL = QUrl.fromLocalFile(SEARCH_ENGINE_FILE)


# ── JSON helpers ─────────────────────────────────────────────────────────────

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ── Web page / tab widgets ────────────────────────────────────────────────────

class BrowserWebPage(QWebEnginePage):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

    def createWindow(self, _wtype):
        return self.main_window.add_new_tab("about:blank").browser.page()


class BrowserPage(QWidget):
    def __init__(self, main_window, url=None):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.browser = QWebEngineView()
        self.browser.setPage(BrowserWebPage(main_window, self.browser))
        self.browser.setUrl(QUrl(url) if url else HOME_URL)
        layout.addWidget(self.browser)


# ── Draggable title bar ───────────────────────────────────────────────────────

class TitleBar(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window  = window
        self.drag_pos = QPoint()
        self.setObjectName("titleBar")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and not self.window.isMaximized():
            self.window.move(e.globalPosition().toPoint() - self.drag_pos)
            e.accept()


# ── Helper ────────────────────────────────────────────────────────────────────

def make_btn(text, tooltip="", object_name="navButton"):
    btn = QPushButton(text)
    btn.setObjectName(object_name)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


# ── Dialogs ───────────────────────────────────────────────────────────────────

class FavoritesDialog(QDialog):
    def __init__(self, favorites, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Favorites")
        self.setMinimumSize(520, 400)
        self.favorites = list(favorites)

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        for fav in self.favorites:
            item = QListWidgetItem(f"★  {fav['title']}\n    {fav['url']}")
            item.setData(Qt.ItemDataRole.UserRole, fav)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.open_btn   = QPushButton("Open")
        self.delete_btn = QPushButton("Delete")
        self.close_btn2 = QPushButton("Close")
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.close_btn2)
        layout.addLayout(btn_row)

        self.open_btn.clicked.connect(self.open_selected)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.close_btn2.clicked.connect(self.accept)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.open_selected())

        self.selected_url = None
        self._apply_style()

    def open_selected(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_url = item.data(Qt.ItemDataRole.UserRole)["url"]
            self.accept()

    def delete_selected(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)
            self.favorites.pop(row)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog, QWidget { background:#1e1f22; color:#f3f3f3; font-family:"Segoe UI"; font-size:13px; }
            QListWidget { background:#17181a; border:1px solid #2b2d31; border-radius:6px; padding:4px; }
            QListWidget::item { padding:8px 6px; border-radius:4px; }
            QListWidget::item:selected { background:#2d7df4; }
            QPushButton { background:#2a2d33; color:#f3f3f3; border:none; border-radius:6px;
                          padding:6px 16px; min-width:70px; }
            QPushButton:hover { background:#3a3f46; }
        """)


class HistoryDialog(QDialog):
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.setWindowTitle("History")
        self.setMinimumSize(580, 440)
        self.history = list(history)

        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search history…")
        self.search_box.textChanged.connect(self._filter)
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        self.list_widget = QListWidget()
        self._populate(self.history)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.open_btn   = QPushButton("Open")
        self.clear_btn  = QPushButton("Clear all")
        self.close_btn2 = QPushButton("Close")
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.close_btn2)
        layout.addLayout(btn_row)

        self.open_btn.clicked.connect(self.open_selected)
        self.clear_btn.clicked.connect(self.clear_all)
        self.close_btn2.clicked.connect(self.accept)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.open_selected())

        self.selected_url = None
        self._apply_style()

    def _populate(self, items):
        self.list_widget.clear()
        for entry in reversed(items):
            text = f"🕐  {entry['title']}\n    {entry['url']}  —  {entry['time']}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.list_widget.addItem(item)

    def _filter(self, text):
        filtered = [e for e in self.history
                    if text.lower() in e["url"].lower() or text.lower() in e["title"].lower()]
        self._populate(filtered)

    def open_selected(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_url = item.data(Qt.ItemDataRole.UserRole)["url"]
            self.accept()

    def clear_all(self):
        self.history.clear()
        self.list_widget.clear()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog, QWidget { background:#1e1f22; color:#f3f3f3; font-family:"Segoe UI"; font-size:13px; }
            QLineEdit { background:#202329; border:1px solid #373b42; border-radius:8px;
                        padding:6px 12px; color:white; }
            QListWidget { background:#17181a; border:1px solid #2b2d31; border-radius:6px; padding:4px; }
            QListWidget::item { padding:8px 6px; border-radius:4px; }
            QListWidget::item:selected { background:#2d7df4; }
            QPushButton { background:#2a2d33; color:#f3f3f3; border:none; border-radius:6px;
                          padding:6px 16px; min-width:70px; }
            QPushButton:hover { background:#3a3f46; }
        """)


class DownloadsDialog(QDialog):
    def __init__(self, downloads, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloads")
        self.setMinimumSize(580, 420)
        self.downloads = list(downloads)

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        for dl in reversed(self.downloads):
            status = dl.get("status", "complete")
            icon   = "✓" if status == "complete" else "✕"
            item = QListWidgetItem(f"{icon}  {os.path.basename(dl['path'])}\n    {dl['path']}  —  {dl['time']}")
            item.setData(Qt.ItemDataRole.UserRole, dl)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.open_btn    = QPushButton("Open file")
        self.folder_btn  = QPushButton("Open folder")
        self.clear_btn   = QPushButton("Clear list")
        self.close_btn2  = QPushButton("Close")
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.folder_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.close_btn2)
        layout.addLayout(btn_row)

        self.open_btn.clicked.connect(self.open_file)
        self.folder_btn.clicked.connect(self.open_folder)
        self.clear_btn.clicked.connect(self.clear_all)
        self.close_btn2.clicked.connect(self.accept)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.open_file())
        self._apply_style()

    def _current_path(self):
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole)["path"] if item else None

    def open_file(self):
        path = self._current_path()
        if path and os.path.exists(path):
            os.startfile(path)

    def open_folder(self):
        path = self._current_path()
        if path:
            folder = os.path.dirname(path)
            if os.path.exists(folder):
                os.startfile(folder)

    def clear_all(self):
        self.downloads.clear()
        self.list_widget.clear()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog, QWidget { background:#1e1f22; color:#f3f3f3; font-family:"Segoe UI"; font-size:13px; }
            QListWidget { background:#17181a; border:1px solid #2b2d31; border-radius:6px; padding:4px; }
            QListWidget::item { padding:8px 6px; border-radius:4px; }
            QListWidget::item:selected { background:#2d7df4; }
            QPushButton { background:#2a2d33; color:#f3f3f3; border:none; border-radius:6px;
                          padding:6px 16px; min-width:80px; }
            QPushButton:hover { background:#3a3f46; }
        """)


class SettingsDialog(QDialog):
    def __init__(self, settings_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(480, 360)
        self.settings_data = dict(settings_data)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.search_engine = QComboBox()
        self.search_engine.addItems(["Bing", "Google", "DuckDuckGo", "Yahoo"])
        idx = {"Bing": 0, "Google": 1, "DuckDuckGo": 2, "Yahoo": 3}.get(
            self.settings_data.get("search_engine", "Bing"), 0)
        self.search_engine.setCurrentIndex(idx)
        form.addRow("Default search engine:", self.search_engine)

        self.homepage = QLineEdit(self.settings_data.get("homepage", ""))
        self.homepage.setPlaceholderText("Leave blank for built-in Vexaura page")
        form.addRow("Homepage URL:", self.homepage)

        self.js_enabled = QCheckBox("Enable JavaScript")
        self.js_enabled.setChecked(self.settings_data.get("javascript", True))
        form.addRow("", self.js_enabled)

        self.save_history = QCheckBox("Save browsing history")
        self.save_history.setChecked(self.settings_data.get("save_history", True))
        form.addRow("", self.save_history)

        self.save_downloads = QCheckBox("Track downloads")
        self.save_downloads.setChecked(self.settings_data.get("save_downloads", True))
        form.addRow("", self.save_downloads)

        layout.addLayout(form)
        layout.addStretch()

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self._apply_style()

    def _save(self):
        engine_map = {0: "Bing", 1: "Google", 2: "DuckDuckGo", 3: "Yahoo"}
        self.settings_data["search_engine"] = engine_map[self.search_engine.currentIndex()]
        self.settings_data["homepage"]       = self.homepage.text().strip()
        self.settings_data["javascript"]     = self.js_enabled.isChecked()
        self.settings_data["save_history"]   = self.save_history.isChecked()
        self.settings_data["save_downloads"] = self.save_downloads.isChecked()
        self.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog, QWidget { background:#1e1f22; color:#f3f3f3; font-family:"Segoe UI"; font-size:13px; }
            QLineEdit { background:#202329; border:1px solid #373b42; border-radius:8px;
                        padding:6px 12px; color:white; }
            QComboBox { background:#202329; border:1px solid #373b42; border-radius:8px;
                        padding:4px 10px; color:white; min-width:180px; }
            QComboBox::drop-down { border:none; }
            QCheckBox { spacing:8px; }
            QCheckBox::indicator { width:16px; height:16px; }
            QPushButton { background:#2a2d33; color:#f3f3f3; border:none; border-radius:6px;
                          padding:6px 20px; min-width:80px; }
            QPushButton:hover { background:#3a3f46; }
            QDialogButtonBox QPushButton[text="Save"] { background:#2d7df4; }
            QDialogButtonBox QPushButton[text="Save"]:hover { background:#4a8ff5; }
        """)


# ── Main window ───────────────────────────────────────────────────────────────

class ZitxVexaura(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zitx Vexaura")
        self.setGeometry(80, 60, 1400, 840)
        self.setMinimumSize(1000, 650)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        if os.path.exists(LOGO_FILE):
            self.setWindowIcon(QIcon(LOGO_FILE))

        # persistent data
        self.favorites  = load_json(FAVORITES_FILE, [])
        self.history    = load_json(HISTORY_FILE, [])
        self.downloads  = load_json(DOWNLOADS_FILE, [])
        self.settings_d = load_json(SETTINGS_FILE, {
            "search_engine": "Bing",
            "homepage": "",
            "javascript": True,
            "save_history": True,
            "save_downloads": True,
        })

        self.root = QWidget()
        self.root_layout = QVBoxLayout(self.root)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.create_title_tabs()
        self.create_navbar()

        self.pages = QStackedWidget()

        self.root_layout.addWidget(self.title_tabs)
        self.root_layout.addWidget(self.navbar)
        self.root_layout.addWidget(self.pages, 1)

        self.setCentralWidget(self.root)
        self.apply_style()
        self.add_new_tab()

        QShortcut(QKeySequence("Ctrl+F"), self, self.find_on_page)
        QShortcut(QKeySequence("Ctrl+P"), self, self.print_page)
        QShortcut(QKeySequence("Ctrl+T"), self, self.add_new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self, lambda: self.close_tab(self.tabs.currentIndex()))

    # ── Title / tab bar ───────────────────────────────────────────────────────

    def create_title_tabs(self):
        self.title_tabs = TitleBar(self)
        self.title_tabs.setFixedHeight(42)
        layout = QHBoxLayout(self.title_tabs)
        layout.setContentsMargins(8, 6, 6, 0)
        layout.setSpacing(4)

        self.tabs = QTabBar()
        self.tabs.setObjectName("browserTabs")
        self.tabs.setDrawBase(False)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setExpanding(False)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.setIconSize(QSize(16, 16))
        self.tabs.currentChanged.connect(self.change_tab)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.new_tab_btn = make_btn("+", "New tab (Ctrl+T)", "topButton")
        self.new_tab_btn.clicked.connect(self.add_new_tab)

        self.profile_btn = QPushButton()
        self.profile_btn.setObjectName("profileButton")
        self.profile_btn.setToolTip("Profile")
        self.profile_btn.clicked.connect(self.show_profile_menu)
        if os.path.exists(LOGO_FILE):
            self.profile_btn.setIcon(QIcon(LOGO_FILE))
            self.profile_btn.setIconSize(QSize(18, 18))

        self.min_btn   = make_btn("─", "Minimize", "windowButton")
        self.min_btn.clicked.connect(self.showMinimized)

        self.max_btn   = make_btn("□", "Maximize / Restore", "windowButton")
        self.max_btn.clicked.connect(self.toggle_maximize)

        self.close_btn = make_btn("✕", "Close", "closeButton")
        self.close_btn.clicked.connect(self.close)

        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.new_tab_btn)
        layout.addStretch()
        layout.addWidget(self.profile_btn)
        layout.addSpacing(4)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

    # ── Navbar ────────────────────────────────────────────────────────────────

    def create_navbar(self):
        self.navbar = QWidget()
        self.navbar.setObjectName("navbar")
        self.navbar.setFixedHeight(52)
        layout = QHBoxLayout(self.navbar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        self.back_btn    = make_btn("←", "Back (Alt+Left)")
        self.back_btn.clicked.connect(lambda: self.current_browser().back())

        self.forward_btn = make_btn("→", "Forward (Alt+Right)")
        self.forward_btn.clicked.connect(lambda: self.current_browser().forward())

        self.reload_btn  = make_btn("↻", "Reload (F5)")
        self.reload_btn.clicked.connect(lambda: self.current_browser().reload())

        self.home_btn    = make_btn("⌂", "Home")
        self.home_btn.clicked.connect(self._go_home)

        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("urlBar")
        self.url_bar.setPlaceholderText("Search or enter web address")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.fav_btn      = make_btn("☆", "Add to / view Favorites")
        self.fav_btn.clicked.connect(self.toggle_favorite)

        self.history_btn  = make_btn("🕐", "History")
        self.history_btn.clicked.connect(self.show_history_dialog)

        self.download_btn = make_btn("⬇", "Downloads")
        self.download_btn.clicked.connect(self.show_downloads_dialog)

        self.menu_btn     = make_btn("⋮", "Menu")
        self.menu_btn.clicked.connect(self.show_main_menu)

        layout.addWidget(self.back_btn)
        layout.addWidget(self.forward_btn)
        layout.addWidget(self.reload_btn)
        layout.addWidget(self.home_btn)
        layout.addSpacing(4)
        layout.addWidget(self.url_bar, 1)
        layout.addSpacing(4)
        layout.addWidget(self.fav_btn)
        layout.addWidget(self.history_btn)
        layout.addWidget(self.download_btn)
        layout.addWidget(self.menu_btn)

    # ── Tab management ────────────────────────────────────────────────────────

    def add_new_tab(self, url=None):
        if url is None and self.settings_d.get("homepage"):
            url = self.settings_d["homepage"]

        page = BrowserPage(self, url)
        self.pages.addWidget(page)
        index = self.tabs.addTab("New tab")
        self.tabs.setCurrentIndex(index)
        self.pages.setCurrentIndex(index)

        page.browser.urlChanged.connect(lambda q, p=page: self.update_url(q, p))
        page.browser.titleChanged.connect(lambda t, p=page: self.update_title(t, p))
        page.browser.iconChanged.connect(lambda i, p=page: self.update_icon(i, p))
        page.browser.loadFinished.connect(self._on_load_finished)
        page.browser.page().profile().downloadRequested.connect(self._on_download_requested)

        self.update_nav_buttons()
        return page

    def close_tab(self, index):
        if self.tabs.count() <= 1:
            return
        widget = self.pages.widget(index)
        self.tabs.removeTab(index)
        self.pages.removeWidget(widget)
        widget.deleteLater()
        new_index = min(index, self.tabs.count() - 1)
        self.tabs.setCurrentIndex(new_index)
        self.pages.setCurrentIndex(new_index)
        self.sync_url_bar()
        self.update_nav_buttons()

    def change_tab(self, index):
        if index >= 0:
            self.pages.setCurrentIndex(index)
            self.sync_url_bar()
            self.update_nav_buttons()
            self._update_fav_star()

    def current_page(self):
        return self.pages.currentWidget()

    def current_browser(self):
        return self.current_page().browser

    # ── URL bar ───────────────────────────────────────────────────────────────

    def sync_url_bar(self):
        if self.pages.count() == 0 or self.current_page() is None:
            return
        url = self.current_browser().url().toString()
        if url.startswith("file:///") and "search-engine.html" in url:
            self.url_bar.clear()
        else:
            self.url_bar.setText(url)

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text:
            self._go_home()
            return
        if "." in text and " " not in text:
            if not text.startswith(("http://", "https://")):
                text = "https://" + text
            self.current_browser().setUrl(QUrl(text))
        else:
            engine = self.settings_d.get("search_engine", "Bing")
            urls = {
                "Bing":       f"https://www.bing.com/search?q={quote_plus(text)}",
                "Google":     f"https://www.google.com/search?q={quote_plus(text)}",
                "DuckDuckGo": f"https://duckduckgo.com/?q={quote_plus(text)}",
                "Yahoo":      f"https://search.yahoo.com/search?p={quote_plus(text)}",
            }
            self.current_browser().setUrl(QUrl(urls.get(engine, urls["Bing"])))

    def _go_home(self):
        hp = self.settings_d.get("homepage", "")
        if hp:
            self.current_browser().setUrl(QUrl(hp))
        else:
            self.current_browser().setUrl(HOME_URL)

    # ── Update callbacks ──────────────────────────────────────────────────────

    def update_url(self, qurl, page):
        if page == self.current_page():
            url = qurl.toString()
            if url.startswith("file:///") and "search-engine.html" in url:
                self.url_bar.clear()
            else:
                self.url_bar.setText(url)
            self.update_nav_buttons()
            self._update_fav_star()

    def update_title(self, title, page):
        index = self.pages.indexOf(page)
        if index == -1:
            return
        clean = (title.strip() or "New tab")[:24]
        if len(title.strip()) > 24:
            clean += "..."
        self.tabs.setTabText(index, clean)

    def update_icon(self, icon, page):
        index = self.pages.indexOf(page)
        if index != -1 and not icon.isNull():
            self.tabs.setTabIcon(index, icon)

    def update_nav_buttons(self):
        if self.pages.count() == 0:
            return
        b = self.current_browser()
        self.back_btn.setEnabled(b.history().canGoBack())
        self.forward_btn.setEnabled(b.history().canGoForward())

    def _on_load_finished(self, ok):
        self.update_nav_buttons()
        if ok and self.settings_d.get("save_history", True):
            browser = self.current_browser()
            url = browser.url().toString()
            if url and not url.startswith("file:///") and url != "about:blank":
                title = browser.title() or url
                entry = {
                    "url": url,
                    "title": title,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                self.history.append(entry)
                save_json(HISTORY_FILE, self.history)

    # ── Downloads ─────────────────────────────────────────────────────────────

    def _on_download_requested(self, download: QWebEngineDownloadRequest):
        default_path = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation),
            download.suggestedFileName()
        )
        download.setDownloadFileName(default_path)
        download.accept()

        if self.settings_d.get("save_downloads", True):
            entry = {
                "path": default_path,
                "url": download.url().toString(),
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "complete"
            }
            self.downloads.append(entry)
            save_json(DOWNLOADS_FILE, self.downloads)

    # ── Window controls ───────────────────────────────────────────────────────

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText("□")
        else:
            self.showMaximized()
            self.max_btn.setText("❐")

    # ── Favorites ─────────────────────────────────────────────────────────────

    def _current_url(self):
        return self.current_browser().url().toString()

    def _current_title(self):
        return self.current_browser().title() or self._current_url()

    def _is_favorited(self):
        url = self._current_url()
        return any(f["url"] == url for f in self.favorites)

    def _update_fav_star(self):
        self.fav_btn.setText("★" if self._is_favorited() else "☆")

    def toggle_favorite(self):
        url = self._current_url()
        if not url or url == "about:blank":
            return
        if self._is_favorited():
            self.favorites = [f for f in self.favorites if f["url"] != url]
            self.fav_btn.setText("☆")
        else:
            self.favorites.append({"url": url, "title": self._current_title()})
            self.fav_btn.setText("★")
        save_json(FAVORITES_FILE, self.favorites)

    def show_favorites_dialog(self):
        dlg = FavoritesDialog(self.favorites, self)
        dlg.exec()
        self.favorites = dlg.favorites
        save_json(FAVORITES_FILE, self.favorites)
        if dlg.selected_url:
            self.current_browser().setUrl(QUrl(dlg.selected_url))
        self._update_fav_star()

    # ── History ───────────────────────────────────────────────────────────────

    def show_history_dialog(self):
        dlg = HistoryDialog(self.history, self)
        dlg.exec()
        self.history = dlg.history
        save_json(HISTORY_FILE, self.history)
        if dlg.selected_url:
            self.current_browser().setUrl(QUrl(dlg.selected_url))

    # ── Downloads dialog ──────────────────────────────────────────────────────

    def show_downloads_dialog(self):
        dlg = DownloadsDialog(self.downloads, self)
        dlg.exec()
        self.downloads = dlg.downloads
        save_json(DOWNLOADS_FILE, self.downloads)

    # ── Print ─────────────────────────────────────────────────────────────────

    def print_page(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.current_browser().page().print(printer, lambda ok: None)

    # ── Find on page ──────────────────────────────────────────────────────────

    def find_on_page(self):
        if hasattr(self, "_find_bar") and self._find_bar.isVisible():
            self._find_bar.hide()
            self.current_browser().findText("")
            return

        if not hasattr(self, "_find_bar"):
            self._find_bar = QWidget()
            self._find_bar.setObjectName("findBar")
            fl = QHBoxLayout(self._find_bar)
            fl.setContentsMargins(8, 4, 8, 4)
            fl.setSpacing(6)

            lbl = QLabel("Find:")
            lbl.setStyleSheet("color:#f3f3f3;")
            self._find_input = QLineEdit()
            self._find_input.setPlaceholderText("Search in page…")
            self._find_input.setStyleSheet(
                "background:#202329;color:white;border:1px solid #373b42;"
                "border-radius:6px;padding:4px 10px;")
            self._find_input.textChanged.connect(
                lambda t: self.current_browser().findText(t))

            prev_btn = QPushButton("▲")
            prev_btn.setFixedSize(28, 28)
            prev_btn.setToolTip("Previous")
            prev_btn.clicked.connect(lambda: self.current_browser().findText(
                self._find_input.text(),
                QWebEnginePage.FindFlag.FindBackward))

            next_btn = QPushButton("▼")
            next_btn.setFixedSize(28, 28)
            next_btn.setToolTip("Next")
            next_btn.clicked.connect(
                lambda: self.current_browser().findText(self._find_input.text()))

            close_x = QPushButton("✕")
            close_x.setFixedSize(24, 24)
            close_x.clicked.connect(self.find_on_page)

            fl.addWidget(lbl)
            fl.addWidget(self._find_input, 1)
            fl.addWidget(prev_btn)
            fl.addWidget(next_btn)
            fl.addWidget(close_x)

            self._find_bar.setStyleSheet(
                "QWidget#findBar{background:#17181a;border-top:1px solid #2b2d31;}"
                "QPushButton{background:transparent;color:#d0d4da;border:none;"
                "border-radius:4px;font-size:12px;}"
                "QPushButton:hover{background:rgba(255,255,255,0.1);}")

            self.root_layout.addWidget(self._find_bar)

        self._find_bar.show()
        self._find_input.setFocus()
        self._find_input.selectAll()

    # ── Settings ──────────────────────────────────────────────────────────────

    def show_settings(self):
        dlg = SettingsDialog(self.settings_d, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.settings_d = dlg.settings_data
            save_json(SETTINGS_FILE, self.settings_d)

    # ── Profile menu ──────────────────────────────────────────────────────────

    def show_profile_menu(self):
        menu = QMenu(self)
        menu.addAction("👤  Vexaura Profile").setEnabled(False)
        menu.addSeparator()
        menu.addAction("Manage profile")
        menu.addAction("Sign in / sync")
        menu.exec(self.profile_btn.mapToGlobal(self.profile_btn.rect().bottomLeft()))

    # ── Main menu ─────────────────────────────────────────────────────────────

    def show_main_menu(self):
        menu = QMenu(self)
        menu.addAction("New tab",              self.add_new_tab)
        menu.addAction("New window",           lambda: ZitxVexaura().show())
        menu.addSeparator()
        menu.addAction("Favorites  ★",         self.show_favorites_dialog)
        menu.addAction("History  🕐",           self.show_history_dialog)
        menu.addAction("Downloads  ⬇",         self.show_downloads_dialog)
        menu.addSeparator()
        menu.addAction("Print  🖨  Ctrl+P",     self.print_page)
        menu.addAction("Find on page  Ctrl+F",  self.find_on_page)
        menu.addSeparator()
        menu.addAction("Settings",              self.show_settings)
        menu.addAction("About Zitx Vexaura",    self._show_about)
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def _show_about(self):
        QMessageBox.about(self, "About Zitx Vexaura",
            "<b>Zitx Vexaura</b><br>A fast, clean custom browser.<br><br>"
            "Built with PyQt6 + QtWebEngine.")

    # ── Style ─────────────────────────────────────────────────────────────────

    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background: #1e1f22;
                color: #f3f3f3;
                font-family: "Segoe UI";
                font-size: 13px;
            }
            QWidget#titleBar {
                background: #17181a;
                border-bottom: 1px solid #2b2d31;
            }
            QWidget#navbar {
                background: #17181a;
                border-bottom: 1px solid #2b2d31;
            }
            QTabBar#browserTabs { background: transparent; }
            QTabBar#browserTabs::tab {
                background: #24262b;
                color: #d7dce2;
                min-width: 160px;
                max-width: 220px;
                height: 32px;
                padding: 0 14px;
                margin-top: 4px;
                margin-right: 2px;
                border: 1px solid #2e3137;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QTabBar#browserTabs::tab:selected {
                background: #2f3339;
                color: white;
                border: 1px solid #3a3f46;
                border-bottom-color: #2f3339;
            }
            QTabBar#browserTabs::tab:hover:!selected { background: #2a2d33; }

            QPushButton {
                background: transparent;
                color: #d0d4da;
                border: none;
                border-radius: 6px;
                min-width: 32px; max-width: 32px;
                min-height: 32px; max-height: 32px;
                font-size: 16px;
            }
            QPushButton:hover  { background: rgba(255,255,255,0.08); color: #ffffff; }
            QPushButton:pressed{ background: rgba(255,255,255,0.13); }
            QPushButton:disabled{ color: #44474d; background: transparent; }

            QPushButton#topButton {
                font-size: 20px; font-weight: 400;
                color: #adb3bb; border-radius: 6px;
            }
            QPushButton#topButton:hover { color: white; background: rgba(255,255,255,0.08); }

            QPushButton#profileButton {
                background: #2a2d33; border-radius: 16px;
                min-width: 32px; max-width: 32px;
                min-height: 32px; max-height: 32px;
            }

            QPushButton#windowButton {
                border-radius: 0;
                min-width: 46px; max-width: 46px;
                min-height: 36px; max-height: 36px;
                font-size: 14px; color: #c0c4cc;
            }
            QPushButton#windowButton:hover { background: rgba(255,255,255,0.10); color: white; }

            QPushButton#closeButton {
                border-radius: 0;
                min-width: 46px; max-width: 46px;
                min-height: 36px; max-height: 36px;
                font-size: 13px; color: #c0c4cc;
            }
            QPushButton#closeButton:hover { background: #c42b1c; color: white; }

            QLineEdit#urlBar {
                background: #202329;
                color: white;
                border: 1px solid #373b42;
                border-radius: 18px;
                padding: 8px 16px;
                min-height: 22px;
                font-size: 13px;
                selection-background-color: #2d7df4;
            }
            QLineEdit#urlBar:focus { background: #1f2329; border: 1px solid #5d9cff; }

            QMenu {
                background: #2a2d33;
                color: white;
                border: 1px solid #3a3f46;
                padding: 6px;
                border-radius: 8px;
            }
            QMenu::item { padding: 8px 38px 8px 16px; border-radius: 6px; }
            QMenu::item:selected { background: #3a3f46; }
            QMenu::separator { height: 1px; background: #3a3f46; margin: 4px 8px; }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Zitx Vexaura")
    if os.path.exists(LOGO_FILE):
        app.setWindowIcon(QIcon(LOGO_FILE))
    app.setStyle("Fusion")
    window = ZitxVexaura()
    window.show()
    sys.exit(app.exec())
