"""
Tools Suite V2 - A tabbed interface for clipboard and shell command management

VERSION 2.0 ENHANCEMENTS:
- Menu bar with File, View, Edit, and Help menus
- Light and dark themes (View menu, Properties, Ctrl+T toggle)
- Modern ttk styling with improved fonts and colors
- Properties window for customizing:
  * Color theme (light / dark)
  * Number of columns for button layouts (Clipboard Paster and Shell Commands)
  * Font for buttons
  * Font for labels and text boxes
- Help and About moved to separate windows accessible from menu
- All settings persisted across sessions

The main window contains tabs for different functionality:

Tab 1 - Clipboard Paster: variable number of buttons which write text strings to the windows clipboard.
The text strings, category, and button labels are loaded from an sqlite3 database named tools_suite.db.
The name of the sqlite3 table is CLIPBOARD_PASTE.
The number of buttons equals the number of current records in the database table.
Each category of button has a different pastel background color.
Buttons are arranged in configurable columns (default: 2).
A button at the bottom opens the Manage Clipboard window.

Tab 2 - Shell Commands: variable number of buttons which execute shell commands.
The category, shell command, command line arguments, and button LABEL are loaded from tools_suite.db.
The name of the sqlite3 table is SHELL_COMMANDS.
Each category of button has a different pastel background color.
Buttons are arranged in configurable columns (default: 2).
If the shell command contains spaces then it is enclosed in quotes.
A button at the bottom opens the Manage Shell Commands window.

Tab 3 - Clipboard List Formatter: reformats clipboard text into bracketed or bulleted lists.
Users can customize the output delimiter which is saved for subsequent sessions.

Child Windows (accessed via menu):
- Help: comprehensive help documentation for all features
- About: information about the application
- Properties: customize column count and fonts
- Manage Clipboard Items: functionality to add, edit, or delete clipboard records
- Manage Shell Commands: functionality to add, edit, or delete shell command records

All functionality is organized in tabs on the main window with management functions in separate windows for easy access.
"""



from __future__ import annotations


import os
import sqlite3
import threading
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont, filedialog
from enum import Enum
from typing import List, Tuple, Optional, Dict
import re
import json


DB_FILENAME = "tools_suite.db"

# Default settings (can be overridden in Properties)
DEFAULT_COLUMNS = 2
DEFAULT_BUTTON_FONT = ("Segoe UI", 10)
DEFAULT_LABEL_FONT = ("Segoe UI", 10)
DEFAULT_THEME = "light"
THEME_LIGHT = "light"
THEME_DARK = "dark"

PASTEL_PALETTE = [
    "#FFCDD2",  # red 100
    "#F8BBD0",  # pink 100
    "#E1BEE7",  # purple 100
    "#D1C4E9",  # deep purple 100
    "#C5CAE9",  # indigo 100
    "#BBDEFB",  # blue 100
    "#B3E5FC",  # light blue 100
    "#B2EBF2",  # cyan 100
    "#B2DFDB",  # teal 100
    "#C8E6C9",  # green 100
    "#DCEDC8",  # light green 100
    "#F0F4C3",  # lime 100
    "#FFF9C4",  # yellow 100
    "#FFECB3",  # amber 100
    "#FFE0B2",  # orange 100
    "#FFCCBC",  # deep orange 100
]

DARK_PASTEL_PALETTE = [
    "#6d4548", "#6d4558", "#554868", "#4a4568", "#454a68",
    "#3d5268", "#3d5a6d", "#3d5a68", "#3d6868", "#456854",
    "#526848", "#686848", "#686848", "#6d6845", "#6d5a45",
    "#6d5045", "#6d4845",
]


def get_theme_name(geometry_store: Optional["WindowGeometryStore"] = None) -> str:
    """Return persisted theme name ('light' or 'dark')."""
    if geometry_store is not None:
        try:
            stored = geometry_store.get("theme")
            if isinstance(stored, str) and stored in (THEME_LIGHT, THEME_DARK):
                return stored
        except Exception:
            pass
    return DEFAULT_THEME


def _hex_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return 128.0
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def get_button_foreground(bg_color: str) -> str:
    """Pick readable text color for a category button background."""
    return "#1e1e1e" if _hex_luminance(bg_color) > 145 else "#f5f5f5"


def get_pastel_color_for_category(
    category_name: Optional[str], theme: str = THEME_LIGHT
) -> str:
    name = (category_name or "General").strip().lower()
    if not name:
        name = "general"
    palette = DARK_PASTEL_PALETTE if theme == THEME_DARK else PASTEL_PALETTE
    idx = abs(hash(name)) % len(palette)
    return palette[idx]


class AppTheme:
    """Central light/dark theming for ttk and classic tk widgets."""

    def __init__(self, root: tk.Misc, geometry_store: "WindowGeometryStore") -> None:
        self.root = root
        self.geometry_store = geometry_store
        self.name = get_theme_name(geometry_store)
        self.style = ttk.Style(root)
        self._ttk_base = self._select_ttk_base()
        self._apply_palette()
        self.configure_ttk()

    def _select_ttk_base(self) -> str:
        available = set(self.style.theme_names())
        if self.name == THEME_DARK:
            return "clam" if "clam" in available else next(iter(available))
        for candidate in ("vista", "xpnative", "clam", "default"):
            if candidate in available:
                return candidate
        return "default"

    def _apply_palette(self) -> None:
        if self.name == THEME_DARK:
            self.bg = "#1e1e1e"
            self.fg = "#e8e8e8"
            self.surface = "#2d2d2d"
            self.surface_alt = "#383838"
            self.border = "#4a4a4a"
            self.accent = "#4a9eff"
            self.accent_hover = "#6eb1ff"
            self.muted = "#9a9a9a"
            self.text_bg = "#252526"
            self.text_fg = "#e8e8e8"
            self.text_insert = "#ffffff"
            self.scroll_trough = "#2d2d2d"
            self.selection_bg = "#264f78"
            self.status_fg = "#9a9a9a"
        else:
            self.bg = "#f3f3f3"
            self.fg = "#1e1e1e"
            self.surface = "#ffffff"
            self.surface_alt = "#fafafa"
            self.border = "#d4d4d4"
            self.accent = "#0078d4"
            self.accent_hover = "#106ebe"
            self.muted = "#6e6e6e"
            self.text_bg = "#ffffff"
            self.text_fg = "#1e1e1e"
            self.text_insert = "#0078d4"
            self.scroll_trough = "#ebebeb"
            self.selection_bg = "#cce8ff"
            self.status_fg = "#6e6e6e"

    def ui_font(self) -> Tuple[str, int]:
        return get_label_font(self.geometry_store)

    def heading_font(self) -> Tuple[str, int, str]:
        family, size = self.ui_font()
        return (family, size + 1, "bold")

    def configure_ttk(self) -> None:
        try:
            self.style.theme_use(self._ttk_base)
        except tk.TclError:
            pass

        ui = self.ui_font()
        heading = self.heading_font()
        pad_btn = (12, 6)
        pad_tab = (14, 7)

        common = {
            "background": self.bg,
            "foreground": self.fg,
            "font": ui,
            "bordercolor": self.border,
        }
        for widget in (
            ".", "TFrame", "TLabel", "TButton", "TRadiobutton", "TCheckbutton",
            "TSpinbox", "TLabelframe", "TLabelframe.Label",
        ):
            self.style.configure(widget, **common)

        self.style.configure("TButton", padding=pad_btn)
        self.style.map(
            "TButton",
            background=[("active", self.surface_alt), ("pressed", self.border)],
            foreground=[("disabled", self.muted)],
        )

        self.style.configure(
            "TNotebook", background=self.bg, borderwidth=0, tabmargins=(2, 5, 2, 0)
        )
        self.style.configure(
            "TNotebook.Tab",
            background=self.surface_alt,
            foreground=self.fg,
            padding=pad_tab,
            font=ui,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", self.surface), ("active", self.surface_alt)],
            expand=[("selected", [1, 1, 1, 0])],
        )

        self.style.configure(
            "TEntry", fieldbackground=self.text_bg, foreground=self.text_fg, padding=4
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=self.text_bg,
            foreground=self.text_fg,
            arrowcolor=self.fg,
            padding=4,
        )
        self.style.map("TCombobox", fieldbackground=[("readonly", self.text_bg)])

        self.style.configure(
            "Treeview",
            background=self.text_bg,
            fieldbackground=self.text_bg,
            foreground=self.text_fg,
            rowheight=26,
            font=ui,
        )
        self.style.configure(
            "Treeview.Heading", background=self.surface_alt, foreground=self.fg, font=heading
        )
        self.style.map(
            "Treeview",
            background=[("selected", self.selection_bg)],
            foreground=[("selected", self.text_fg)],
        )

        self.style.configure(
            "Vertical.TScrollbar", background=self.scroll_trough, troughcolor=self.bg
        )
        self.style.configure(
            "Horizontal.TScrollbar", background=self.scroll_trough, troughcolor=self.bg
        )

        self.style.configure("Status.TLabel", foreground=self.status_fg, font=ui)
        self.style.configure("Muted.TLabel", foreground=self.muted, font=(ui[0], max(8, ui[1] - 1)))
        self.style.configure("Heading.TLabel", font=heading, foreground=self.fg)
        self.style.configure("Title.TLabel", font=(ui[0], ui[1] + 4, "bold"))

    def set_theme(self, name: str, *, persist: bool = True, refresh_tabs: bool = True) -> None:
        if name not in (THEME_LIGHT, THEME_DARK):
            name = THEME_LIGHT
        if name == self.name and persist:
            pass
        self.name = name
        self._ttk_base = self._select_ttk_base()
        self._apply_palette()
        self.configure_ttk()
        if persist:
            self.geometry_store.set_value("theme", name)
        self.apply_to_window(self.root)
        if refresh_tabs and hasattr(self.root, "tabs"):
            for tab_name in ("clipboard", "shell"):
                tab = self.root.tabs.get(tab_name)
                if tab is not None and hasattr(tab, "refresh_items"):
                    tab.refresh_items()

    def toggle_theme(self) -> str:
        next_theme = THEME_DARK if self.name == THEME_LIGHT else THEME_LIGHT
        self.set_theme(next_theme)
        return next_theme

    def apply_to_window(self, window: tk.Misc) -> None:
        try:
            if isinstance(window, (tk.Tk, tk.Toplevel)):
                window.configure(bg=self.bg)
        except Exception:
            pass
        self._walk_widgets(window)

    def _walk_widgets(self, widget: tk.Misc) -> None:
        try:
            self._style_widget(widget)
        except Exception:
            pass
        try:
            children = widget.winfo_children()
        except Exception:
            return
        for child in children:
            self._walk_widgets(child)

    def _style_widget(self, widget: tk.Misc) -> None:
        cls = widget.winfo_class()
        if cls == "Text":
            self.style_text(widget)
        elif cls == "Canvas":
            self.style_canvas(widget)
        elif cls == "Listbox":
            self.style_listbox(widget)
        elif cls == "Button" and hasattr(widget, "_theme_category"):
            self.style_category_button(widget, widget._theme_category)
        elif cls == "Menu":
            self.style_menu(widget)

    def style_text(self, widget: tk.Text, *, readonly: bool = False) -> None:
        font = self.ui_font()
        opts = {
            "bg": self.text_bg,
            "fg": self.text_fg,
            "insertbackground": self.text_insert,
            "selectbackground": self.selection_bg,
            "selectforeground": self.text_fg,
            "relief": "flat",
            "bd": 1,
            "highlightthickness": 1,
            "highlightbackground": self.border,
            "highlightcolor": self.accent,
            "font": font,
        }
        if readonly:
            opts["state"] = "disabled"
        try:
            widget.configure(**opts)
        except Exception:
            pass

    def style_canvas(self, widget: tk.Canvas) -> None:
        try:
            widget.configure(
                bg=self.bg, highlightthickness=0, bd=0, relief="flat"
            )
        except Exception:
            pass

    def style_listbox(self, widget: tk.Listbox) -> None:
        try:
            widget.configure(
                bg=self.text_bg,
                fg=self.text_fg,
                selectbackground=self.selection_bg,
                selectforeground=self.text_fg,
                highlightthickness=1,
                highlightbackground=self.border,
                highlightcolor=self.accent,
                relief="flat",
                bd=0,
                font=self.ui_font(),
            )
        except Exception:
            pass

    def style_category_button(
        self, widget: tk.Button, category: Optional[str], font: Optional[Tuple] = None
    ) -> None:
        color = get_pastel_color_for_category(category, self.name)
        fg = get_button_foreground(color)
        btn_font = font or get_button_font(self.geometry_store)
        try:
            widget.configure(
                bg=color,
                activebackground=color,
                fg=fg,
                activeforeground=fg,
                relief="flat",
                bd=0,
                padx=10,
                pady=8,
                cursor="hand2",
                font=btn_font,
                highlightthickness=1,
                highlightbackground=self.border,
                highlightcolor=self.accent,
            )
            widget._theme_category = category
        except Exception:
            pass

    def style_menu(self, menu: tk.Menu) -> None:
        try:
            menu.configure(
                bg=self.surface,
                fg=self.fg,
                activebackground=self.accent,
                activeforeground="#ffffff",
                borderwidth=0,
                relief="flat",
            )
        except Exception:
            pass
        try:
            end = menu.index("end")
            if end is None:
                return
            for i in range(end + 1):
                if menu.type(i) == "cascade":
                    sub = menu.nametowidget(menu.entrycget(i, "menu"))
                    self.style_menu(sub)
        except Exception:
            pass


def get_column_count(geometry_store: "WindowGeometryStore") -> int:
    """Get the configured number of columns for button layouts."""
    try:
        columns = geometry_store.get("button_columns")
        if isinstance(columns, int) and 1 <= columns <= 10:
            return columns
    except Exception:
        pass
    return DEFAULT_COLUMNS


def get_button_font(geometry_store: "WindowGeometryStore") -> Tuple[str, int]:
    """Get the configured button font."""
    try:
        font_setting = geometry_store.get("button_font")
        if isinstance(font_setting, (list, tuple)) and len(font_setting) >= 2:
            return tuple(font_setting[:2])
    except Exception:
        pass
    return DEFAULT_BUTTON_FONT


def get_label_font(geometry_store: "WindowGeometryStore") -> Tuple[str, int]:
    """Get the configured label/text font."""
    try:
        font_setting = geometry_store.get("label_font")
        if isinstance(font_setting, (list, tuple)) and len(font_setting) >= 2:
            return tuple(font_setting[:2])
    except Exception:
        pass
    return DEFAULT_LABEL_FONT


def _is_cursor_command(command_line: str) -> bool:
    """Return True when the command appears to invoke the Cursor CLI."""
    if not command_line:
        return False
    # Match common forms like: cursor, cursor.exe, "C:\...\cursor.cmd"
    return bool(re.search(r'(^|[\\/\s"])cursor(\.cmd|\.exe|\.bat)?(?=$|[\s"])', command_line, re.IGNORECASE))


class WindowPosition(Enum):
    CENTER = "CENTER"
    UPPER_RIGHT = "UPPER_RIGHT"
    UPPER_LEFT = "UPPER_LEFT"
    LOWER_RIGHT = "LOWER_RIGHT"
    LOWER_LEFT = "LOWER_LEFT"


def place_window(window: tk.Toplevel, width: int, height: int, position: WindowPosition) -> None:
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    margin = 10

    if position == WindowPosition.CENTER:
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
    elif position == WindowPosition.UPPER_RIGHT:
        x = screen_width - width - margin
        y = margin
    elif position == WindowPosition.UPPER_LEFT:
        x = margin
        y = margin
    elif position == WindowPosition.LOWER_RIGHT:
        x = screen_width - width - margin
        y = screen_height - height - margin
    elif position == WindowPosition.LOWER_LEFT:
        x = margin
        y = screen_height - height - margin
    else:
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

    geometry = f"{width}x{height}+{x}+{y}"
    window.geometry(geometry)


class WindowGeometryStore:
    def __init__(self, base_dir: str) -> None:
        self.file_path = os.path.join(base_dir, "tools_suite_positions.json")
        self._data: Dict = {}
        self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._data = loaded
        except Exception:
            self._data = {}

    def save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def get(self, key: str) -> Optional[Dict]:
        return self._data.get(key)

    def set(self, key: str, x: int, y: int, w: int, h: int) -> None:
        if key not in self._data:
            self._data[key] = {}
        self._data[key].update({"x": x, "y": y, "w": w, "h": h})
        # Save on each set to be resilient to crashes
        self.save()
    
    def set_value(self, key: str, value) -> None:
        """Set a general value in the store (not just geometry)."""
        self._data[key] = value
        self.save()


class DatabaseManager:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_database()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_database(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS CLIPBOARD_PASTE (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    label TEXT NOT NULL,
                    content TEXT NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS SHELL_COMMANDS (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    label TEXT NOT NULL,
                    command TEXT NOT NULL,
                    args TEXT,
                    archived INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.commit()

        # Migrate: ensure category columns exist (for existing DBs)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(CLIPBOARD_PASTE);")
            clip_cols = [r[1] for r in cur.fetchall()]
            if "category" not in clip_cols:
                cur.execute("ALTER TABLE CLIPBOARD_PASTE ADD COLUMN category TEXT;")
                cur.execute("UPDATE CLIPBOARD_PASTE SET category = 'General' WHERE category IS NULL;")
            if "archived" not in clip_cols:
                cur.execute("ALTER TABLE CLIPBOARD_PASTE ADD COLUMN archived INTEGER DEFAULT 0;")
                cur.execute("UPDATE CLIPBOARD_PASTE SET archived = 0 WHERE archived IS NULL;")
            cur.execute("PRAGMA table_info(SHELL_COMMANDS);")
            shell_cols = [r[1] for r in cur.fetchall()]
            if "category" not in shell_cols:
                cur.execute("ALTER TABLE SHELL_COMMANDS ADD COLUMN category TEXT;")
                cur.execute("UPDATE SHELL_COMMANDS SET category = 'General' WHERE category IS NULL;")
            if "archived" not in shell_cols:
                cur.execute("ALTER TABLE SHELL_COMMANDS ADD COLUMN archived INTEGER DEFAULT 0;")
                cur.execute("UPDATE SHELL_COMMANDS SET archived = 0 WHERE archived IS NULL;")
            conn.commit()

        # Seed if empty
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM CLIPBOARD_PASTE;")
            clip_count = cur.fetchone()[0]
            if clip_count == 0:
                categories = ["General", "Notes", "Dev", "Ops", "Misc"]
                items = [(categories[i % len(categories)], f"Copy Text {i}", f"Sample clipboard text {i}") for i in range(1, 11)]
                cur.executemany("INSERT INTO CLIPBOARD_PASTE (category, label, content) VALUES (?, ?, ?);", items)

            cur.execute("SELECT COUNT(*) FROM SHELL_COMMANDS;")
            cmd_count = cur.fetchone()[0]
            if cmd_count == 0:
                # Seed with harmless echo commands via cmd.exe so it works reliably on Windows
                categories = ["General", "Tools", "System", "Net", "Misc"]
                items = [(categories[i % len(categories)], f"Echo {i}", "cmd", f"/c echo Launched command {i}") for i in range(1, 11)]
                cur.executemany("INSERT INTO SHELL_COMMANDS (category, label, command, args) VALUES (?, ?, ?, ?);", items)

            conn.commit()

    def get_clipboard_items(self) -> List[Tuple[int, Optional[str], str, str, int]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, category, label, content, archived FROM CLIPBOARD_PASTE ORDER BY CATEGORY, id  ASC;"
            )
            return cur.fetchall()

    def get_clipboard_items_active(self) -> List[Tuple[int, Optional[str], str, str]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, category, label, content FROM CLIPBOARD_PASTE WHERE archived = 0 OR archived IS NULL ORDER BY CATEGORY, id ASC;"
            )
            return cur.fetchall()

    def add_clipboard_item(self, category: Optional[str], label: str, content: str, archived: bool = False) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO CLIPBOARD_PASTE (category, label, content, archived) VALUES (?, ?, ?, ?);",
                (category, label, content, 1 if archived else 0),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_clipboard_item(self, item_id: int, category: Optional[str], label: str, content: str, archived: bool) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE CLIPBOARD_PASTE SET category = ?, label = ?, content = ?, archived = ? WHERE id = ?;",
                (category, label, content, 1 if archived else 0, item_id),
            )
            conn.commit()

    def delete_clipboard_item(self, item_id: int) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM CLIPBOARD_PASTE WHERE id = ?;", (item_id,))
            conn.commit()

    def add_shell_command(self, category: Optional[str], label: str, command: str, args: Optional[str], archived: bool = False) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO SHELL_COMMANDS (category, label, command, args, archived) VALUES (?, ?, ?, ?, ?);",
                (category, label, command, args, 1 if archived else 0),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_shell_command(self, item_id: int, category: Optional[str], label: str, command: str, args: Optional[str], archived: bool) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE SHELL_COMMANDS SET category = ?, label = ?, command = ?, args = ?, archived = ? WHERE id = ?;",
                (category, label, command, args, 1 if archived else 0, item_id),
            )
            conn.commit()

    def delete_shell_command(self, item_id: int) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM SHELL_COMMANDS WHERE id = ?;", (item_id,))
            conn.commit()

    def get_shell_commands(self) -> List[Tuple[int, Optional[str], str, str, Optional[str], int]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, category, label, command, args, archived FROM SHELL_COMMANDS ORDER BY CATEGORY, id ASC;"
            )
            return cur.fetchall()

    def get_shell_commands_active(self) -> List[Tuple[int, Optional[str], str, str, Optional[str]]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, category, label, command, args FROM SHELL_COMMANDS WHERE archived = 0 OR archived IS NULL ORDER BY CATEGORY, id ASC;"
            )
            return cur.fetchall()

    def get_distinct_categories(self, table_name: str) -> List[str]:
        safe_table = "CLIPBOARD_PASTE" if table_name.upper().startswith("CLIP") else "SHELL_COMMANDS"
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT DISTINCT category FROM {safe_table} WHERE category IS NOT NULL AND category <> '' ORDER BY category ASC;")
            rows = cur.fetchall()
            return [r[0] for r in rows]


class ClipboardTab(ttk.Frame):
    def __init__(self, parent: ttk.Frame, db: DatabaseManager, master_app: tk.Tk) -> None:
        super().__init__(parent)
        self.db = db
        self.master_app = master_app

        self.button_widgets: List[tk.Button] = []
        self.status_var = tk.StringVar(value="")
        
        # Get column count and button font from settings
        self._max_columns = self._get_max_columns()
        self._button_font = self._get_button_font()

        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        grid_container = ttk.Frame(container)
        grid_container.pack(fill="both", expand=True)

        self.grid_canvas = tk.Canvas(grid_container, highlightthickness=0)
        self.grid_scrollbar = ttk.Scrollbar(
            grid_container, orient="vertical", command=self.grid_canvas.yview
        )
        self.grid_canvas.configure(yscrollcommand=self.grid_scrollbar.set)
        self.grid_scrollbar.pack(side="right", fill="y")
        self.grid_canvas.pack(side="left", fill="both", expand=True)
        if hasattr(master_app, "theme"):
            master_app.theme.style_canvas(self.grid_canvas)

        self.grid_frame = ttk.Frame(self.grid_canvas)
        self._grid_canvas_window = self.grid_canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")

        for c in range(self._max_columns):
            self.grid_frame.columnconfigure(c, weight=1)

        # Status bar
        status = ttk.Label(container, textvariable=self.status_var, anchor="w", style="Status.TLabel")
        status.pack(fill="x", pady=(8, 0))
        
        # Button to open Manage Clipboard window
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_frame, text="Manage Clipboard Items", 
                   command=self._open_manage_window).pack(side="left")

        # Refresh data
        self.items: List[Tuple[int, Optional[str], str, str]] = []
        
        # Bind resize event to update button wraplengths and scrolling region
        self.grid_frame.bind("<Configure>", self._on_grid_content_configure)
        self.grid_canvas.bind("<Configure>", self._on_grid_canvas_configure)
        self.grid_frame.bind("<Configure>", self._on_frame_resize, add="+")
        self.grid_canvas.bind("<Enter>", self._bind_mousewheel)
        self.grid_canvas.bind("<Leave>", self._unbind_mousewheel)
        
        self.refresh_items()
    
    def _get_max_columns(self) -> int:
        """Get the column count setting."""
        if hasattr(self.master_app, 'geometry_store'):
            return get_column_count(self.master_app.geometry_store)
        return DEFAULT_COLUMNS
    
    def _get_button_font(self) -> Tuple[str, int]:
        """Get the button font setting."""
        if hasattr(self.master_app, 'geometry_store'):
            return get_button_font(self.master_app.geometry_store)
        return DEFAULT_BUTTON_FONT

    def refresh_items(self) -> None:
        # Reload settings in case they changed
        self._max_columns = self._get_max_columns()
        self._button_font = self._get_button_font()
        
        self.items = self.db.get_clipboard_items_active()
        self._rebuild_buttons()

    def _rebuild_buttons(self) -> None:
        # Clear existing content
        try:
            for child in self.grid_frame.winfo_children():
                try:
                    child.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        self.button_widgets = []

        # Group items by category and render a header per category
        def _norm(cat: Optional[str]) -> str:
            name = (cat or "General").strip()
            return name if name else "General"

        items_indexed = list(enumerate(self.items))
        category_order = []
        grouped = {}
        for idx, item in items_indexed:
            _, cat, _, _ = item
            key = _norm(cat)
            if key not in grouped:
                grouped[key] = []
                category_order.append(key)
            grouped[key].append((idx, item))

        theme = getattr(self.master_app, "theme", None)
        heading_font = theme.heading_font() if theme else ("Segoe UI", 11, "bold")
        current_row = 0
        for cat in category_order:
            header = ttk.Label(
                self.grid_frame, text=cat, anchor="w", style="Heading.TLabel", font=heading_font
            )
            header.grid(row=current_row, column=0, columnspan=self._max_columns, sticky="ew", pady=(4, 2))
            current_row += 1

            buttons = grouped.get(cat, [])
            for i, (idx, (_id, category, label, _content)) in enumerate(buttons):
                r = current_row + (i // self._max_columns)
                c = i % self._max_columns
                btn = tk.Button(
                    self.grid_frame,
                    text=label,
                    command=lambda i=idx: self._on_copy(i),
                    justify="center",
                )
                if theme:
                    theme.style_category_button(btn, category, self._button_font)
                else:
                    color = get_pastel_color_for_category(category)
                    btn.configure(
                        bg=color,
                        activebackground=color,
                        font=self._button_font,
                        relief="flat",
                    )
                btn.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
                self.button_widgets.append(btn)
            rows_used = (len(buttons) + self._max_columns - 1) // self._max_columns
            current_row += max(rows_used, 0)
            current_row += 1

        # Ensure columns expand
        for c in range(self._max_columns):
            self.grid_frame.columnconfigure(c, weight=1)
        
        # Update wraplengths after building
        self.after(50, self._update_button_wraplengths)
    
    def _on_frame_resize(self, event=None) -> None:
        """Handle grid frame resize to update button wraplengths."""
        self._update_button_wraplengths()

    def _on_grid_content_configure(self, event=None) -> None:
        try:
            self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all"))
        except Exception:
            pass

    def _on_grid_canvas_configure(self, event=None) -> None:
        try:
            if event is not None:
                self.grid_canvas.itemconfigure(self._grid_canvas_window, width=event.width)
        except Exception:
            pass

    def _on_mousewheel(self, event) -> None:
        try:
            delta = int(-1 * (event.delta / 120))
            if delta == 0:
                return
            lo, hi = self.grid_canvas.yview()
            if (delta < 0 and lo <= 0.0) or (delta > 0 and hi >= 1.0):
                return
            self.grid_canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    def _on_mousewheel_up(self, _event) -> None:
        try:
            lo, _ = self.grid_canvas.yview()
            if lo <= 0.0:
                return
            self.grid_canvas.yview_scroll(-1, "units")
        except Exception:
            pass

    def _on_mousewheel_down(self, _event) -> None:
        try:
            _, hi = self.grid_canvas.yview()
            if hi >= 1.0:
                return
            self.grid_canvas.yview_scroll(1, "units")
        except Exception:
            pass

    def _bind_mousewheel(self, _event=None) -> None:
        self.grid_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.grid_canvas.bind_all("<Button-4>", self._on_mousewheel_up)
        self.grid_canvas.bind_all("<Button-5>", self._on_mousewheel_down)

    def _unbind_mousewheel(self, _event=None) -> None:
        self.grid_canvas.unbind_all("<MouseWheel>")
        self.grid_canvas.unbind_all("<Button-4>")
        self.grid_canvas.unbind_all("<Button-5>")
    
    def _update_button_wraplengths(self) -> None:
        """Update wraplength for all buttons based on current frame width."""
        try:
            # Get current frame width
            frame_width = self.grid_frame.winfo_width()
            if frame_width <= 1:
                # Frame not yet sized, try again later
                return
            
            # Calculate wraplength per button (account for padding and margins)
            button_width = (frame_width // self._max_columns) - 20
            # Ensure minimum wraplength
            wraplength = max(80, button_width)
            
            # Update all button widgets
            for btn in self.button_widgets:
                try:
                    btn.configure(wraplength=wraplength, font=self._button_font)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_copy(self, idx: int) -> None:
        if idx >= len(self.items):
            return
        _, category, label, content = self.items[idx]
        try:
            self.master_app.clipboard_clear()
            self.master_app.clipboard_append(content)
            self.master_app.update()  # Ensure clipboard keeps content after window loses focus
            self.status_var.set(f"Copied: {label}")
        except Exception as exc:
            messagebox.showerror("Clipboard Error", f"Failed to copy text:\n{exc}")
    
    def _open_manage_window(self) -> None:
        """Open the Manage Clipboard window."""
        if hasattr(self.master_app, 'open_manage_clipboard_window'):
            self.master_app.open_manage_clipboard_window()


class ShellCommandsTab(ttk.Frame):
    def __init__(self, parent: ttk.Frame, db: DatabaseManager, master_app: tk.Tk) -> None:
        super().__init__(parent)
        self.db = db
        self.master_app = master_app

        self.button_widgets: List[tk.Button] = []
        self.status_var = tk.StringVar(value="")
        
        # Get column count and button font from settings
        self._max_columns = self._get_max_columns()
        self._button_font = self._get_button_font()

        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        grid_container = ttk.Frame(container)
        grid_container.pack(fill="both", expand=True)

        self.grid_canvas = tk.Canvas(grid_container, highlightthickness=0)
        self.grid_scrollbar = ttk.Scrollbar(
            grid_container, orient="vertical", command=self.grid_canvas.yview
        )
        self.grid_canvas.configure(yscrollcommand=self.grid_scrollbar.set)
        self.grid_scrollbar.pack(side="right", fill="y")
        self.grid_canvas.pack(side="left", fill="both", expand=True)
        if hasattr(master_app, "theme"):
            master_app.theme.style_canvas(self.grid_canvas)

        self.grid_frame = ttk.Frame(self.grid_canvas)
        self._grid_canvas_window = self.grid_canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")

        for c in range(self._max_columns):
            self.grid_frame.columnconfigure(c, weight=1)

        # Status bar
        status = ttk.Label(container, textvariable=self.status_var, anchor="w", style="Status.TLabel")
        status.pack(fill="x", pady=(8, 0))
        
        # Button to open Manage Shell Commands window
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_frame, text="Manage Shell Commands", 
                   command=self._open_manage_window).pack(side="left")

        # Refresh data
        self.items: List[Tuple[int, Optional[str], str, str, Optional[str]]] = []
        
        # Bind resize event to update button wraplengths and scrolling region
        self.grid_frame.bind("<Configure>", self._on_grid_content_configure)
        self.grid_canvas.bind("<Configure>", self._on_grid_canvas_configure)
        self.grid_frame.bind("<Configure>", self._on_frame_resize, add="+")
        self.grid_canvas.bind("<Enter>", self._bind_mousewheel)
        self.grid_canvas.bind("<Leave>", self._unbind_mousewheel)
        
        self.refresh_items()
    
    def _get_max_columns(self) -> int:
        """Get the column count setting."""
        if hasattr(self.master_app, 'geometry_store'):
            return get_column_count(self.master_app.geometry_store)
        return DEFAULT_COLUMNS
    
    def _get_button_font(self) -> Tuple[str, int]:
        """Get the button font setting."""
        if hasattr(self.master_app, 'geometry_store'):
            return get_button_font(self.master_app.geometry_store)
        return DEFAULT_BUTTON_FONT

    def refresh_items(self) -> None:
        # Reload settings in case they changed
        self._max_columns = self._get_max_columns()
        self._button_font = self._get_button_font()
        
        self.items = self.db.get_shell_commands_active()
        self._rebuild_buttons()

    def _rebuild_buttons(self) -> None:
        # Clear existing content
        try:
            for child in self.grid_frame.winfo_children():
                try:
                    child.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        self.button_widgets = []

        # Group items by category and render a header per category
        def _norm(cat: Optional[str]) -> str:
            name = (cat or "General").strip()
            return name if name else "General"

        items_indexed = list(enumerate(self.items))
        category_order = []
        grouped = {}
        for idx, item in items_indexed:
            _, cat, _, _, _ = item
            key = _norm(cat)
            if key not in grouped:
                grouped[key] = []
                category_order.append(key)
            grouped[key].append((idx, item))

        theme = getattr(self.master_app, "theme", None)
        heading_font = theme.heading_font() if theme else ("Segoe UI", 11, "bold")
        current_row = 0
        for cat in category_order:
            header = ttk.Label(
                self.grid_frame, text=cat, anchor="w", style="Heading.TLabel", font=heading_font
            )
            header.grid(row=current_row, column=0, columnspan=self._max_columns, sticky="ew", pady=(4, 2))
            current_row += 1

            buttons = grouped.get(cat, [])
            for i, (idx, (_id, category, label, _cmd, _args)) in enumerate(buttons):
                r = current_row + (i // self._max_columns)
                c = i % self._max_columns
                btn = tk.Button(
                    self.grid_frame,
                    text=label,
                    command=lambda i=idx: self._on_execute(i),
                    justify="center",
                )
                if theme:
                    theme.style_category_button(btn, category, self._button_font)
                else:
                    color = get_pastel_color_for_category(category)
                    btn.configure(
                        bg=color,
                        activebackground=color,
                        font=self._button_font,
                        relief="flat",
                    )
                btn.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
                self.button_widgets.append(btn)
            rows_used = (len(buttons) + self._max_columns - 1) // self._max_columns
            current_row += max(rows_used, 0)
            current_row += 1

        for c in range(self._max_columns):
            self.grid_frame.columnconfigure(c, weight=1)
        
        # Update wraplengths after building
        self.after(50, self._update_button_wraplengths)
    
    def _on_frame_resize(self, event=None) -> None:
        """Handle grid frame resize to update button wraplengths."""
        self._update_button_wraplengths()

    def _on_grid_content_configure(self, event=None) -> None:
        try:
            self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all"))
        except Exception:
            pass

    def _on_grid_canvas_configure(self, event=None) -> None:
        try:
            if event is not None:
                self.grid_canvas.itemconfigure(self._grid_canvas_window, width=event.width)
        except Exception:
            pass

    def _on_mousewheel(self, event) -> None:
        try:
            delta = int(-1 * (event.delta / 120))
            if delta == 0:
                return
            lo, hi = self.grid_canvas.yview()
            if (delta < 0 and lo <= 0.0) or (delta > 0 and hi >= 1.0):
                return
            self.grid_canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    def _on_mousewheel_up(self, _event) -> None:
        try:
            lo, _ = self.grid_canvas.yview()
            if lo <= 0.0:
                return
            self.grid_canvas.yview_scroll(-1, "units")
        except Exception:
            pass

    def _on_mousewheel_down(self, _event) -> None:
        try:
            _, hi = self.grid_canvas.yview()
            if hi >= 1.0:
                return
            self.grid_canvas.yview_scroll(1, "units")
        except Exception:
            pass

    def _bind_mousewheel(self, _event=None) -> None:
        self.grid_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.grid_canvas.bind_all("<Button-4>", self._on_mousewheel_up)
        self.grid_canvas.bind_all("<Button-5>", self._on_mousewheel_down)

    def _unbind_mousewheel(self, _event=None) -> None:
        self.grid_canvas.unbind_all("<MouseWheel>")
        self.grid_canvas.unbind_all("<Button-4>")
        self.grid_canvas.unbind_all("<Button-5>")
    
    def _update_button_wraplengths(self) -> None:
        """Update wraplength for all buttons based on current frame width."""
        try:
            # Get current frame width
            frame_width = self.grid_frame.winfo_width()
            if frame_width <= 1:
                # Frame not yet sized, try again later
                return
            
            # Calculate wraplength per button (account for padding and margins)
            button_width = (frame_width // self._max_columns) - 20
            # Ensure minimum wraplength
            wraplength = max(80, button_width)
            
            # Update all button widgets
            for btn in self.button_widgets:
                try:
                    btn.configure(wraplength=wraplength, font=self._button_font)
                except Exception:
                    pass
        except Exception:
            pass

    def _run_command_thread(self, label: str, command: str, args: Optional[str]) -> None:
        try:
            cmd = (command or "").strip()
            # Quote command path if it contains spaces and isn't already quoted
            if " " in cmd and not (cmd.startswith('"') and cmd.endswith('"')):
                cmd = f'"{cmd}"'
            if args and args.strip():
                cmdline = f"{cmd} {args.strip()}"
            else:
                cmdline = cmd
            env = None
            if _is_cursor_command(cmdline):
                env = os.environ.copy()
                # Cursor CLI is Node-based and currently emits a punycode deprecation warning.
                # Suppress only deprecation warnings for this launched process.
                env["NODE_OPTIONS"] = "--no-deprecation"
            # Use shell=True for Windows built-ins (e.g., echo, dir). Run non-blocking.
            subprocess.Popen(cmdline, shell=True, env=env)  # nosec - intended for user-provided commands
            self.status_var.set(f"Launched: {label}")
        except Exception as exc:
            messagebox.showerror("Command Error", f"Failed to launch '{label}':\n{exc}")

    def _on_execute(self, idx: int) -> None:
        if idx >= len(self.items):
            return
        _, category, label, command, args = self.items[idx]
        t = threading.Thread(target=self._run_command_thread, args=(label, command, args), daemon=True)
        t.start()
    
    def _open_manage_window(self) -> None:
        """Open the Manage Shell Commands window."""
        if hasattr(self.master_app, 'open_manage_shell_commands_window'):
            self.master_app.open_manage_shell_commands_window()


class AboutTab(ttk.Frame):
    def __init__(self, parent: ttk.Frame, master_app: tk.Tk) -> None:
        super().__init__(parent)

        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="Tools Suite\nA handy little time and typing saver", 
                 font=("Segoe UI", 12)).pack(pady=20)
        ttk.Label(container, text="Version 2.0\n\nOrganize your clipboard snippets and shell commands\nwith an easy-to-use tabbed interface.",
                 justify="center").pack()


class HelpCenterTab(ttk.Frame):
    def __init__(self, parent: ttk.Frame, master_app: tk.Tk, initial_tab: Optional[str] = None) -> None:
        super().__init__(parent)
        self.master_app = master_app

        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        # Tabs
        self.help_notebook = ttk.Notebook(container)
        self.help_notebook.pack(fill="both", expand=True)

        self.tabs = {}
        def add_tab(key: str, title: str, text: str) -> None:
            frame = ttk.Frame(self.help_notebook)
            self.help_notebook.add(frame, text=title)
            # Scrollable text
            text_frame = ttk.Frame(frame)
            text_frame.pack(fill="both", expand=True, padx=6, pady=6)
            vsb = ttk.Scrollbar(text_frame, orient="vertical")
            txt = tk.Text(text_frame, wrap="word", height=18)
            txt.configure(state="normal")
            txt.insert("1.0", text.strip() + "\n")
            txt.configure(state="disabled")
            if hasattr(self.master_app, "theme"):
                self.master_app.theme.style_text(txt, readonly=True)
            txt.pack(side="left", fill="both", expand=True)
            vsb.config(command=txt.yview)
            txt.configure(yscrollcommand=vsb.set)
            vsb.pack(side="right", fill="y")
            self.tabs[key] = frame

        add_tab(
            "overview",
            "Overview",
            """
            Tools Suite lets you:
            - Copy predefined snippets to the clipboard (Clipboard Paster).
            - Launch common tools/commands (Shell Commands).
            - Manage both sets of items (add/edit/delete/archive).
            - Reformat clipboard lists (Clipboard List Formatter).

            Color and grouping:
            - Items are grouped by Category with a header per category.
            - Each category gets a pastel background color for quick scanning.
            - Buttons are arranged in two columns.

            Archived items:
            - Mark an item as Archived in its management screen to hide it from selection windows.
            - Archived items remain visible and editable in management screens.
            """
        )

        add_tab(
            "clipboard",
            "Clipboard Paster",
            """
            Clipboard Paster shows buttons for active (non-archived) clipboard snippets from the database.
            - Click a button to copy its text to the Windows clipboard.
            - Items are grouped by Category; headers appear above each group.
            - Only non-archived items are shown here.

            To add, edit, or archive items, use Manage Clipboard Items.
            """
        )

        add_tab(
            "shell",
            "Shell Commands",
            """
            Shell Commands shows buttons that launch predefined commands.
            - Commands and optional arguments come from the database.
            - If a command path contains spaces, it is quoted automatically.
            - Items are grouped by Category; only non-archived items are shown.
            - Launches in a separate process using Windows shell.

            To add, edit, or archive commands, use Manage Shell Commands.
            """
        )

        add_tab(
            "manage_clipboard",
            "Manage Clipboard Items",
            """
            Use this screen to add, edit, delete, refresh, and archive clipboard items.
            - Category: optional grouping name (used for color and headers).
            - Label: button text shown in Clipboard Paster.
            - Content: the text copied to clipboard when clicked.
            - Archived: when checked, the item is hidden from Clipboard Paster but remains here.

            Actions:
            - New: clears the form for a new item.
            - Save: inserts or updates the item.
            - Delete: removes the selected item (confirmation required).
            - Refresh: reloads data and propagates changes to Clipboard Paster.
            """
        )

        add_tab(
            "manage_shell",
            "Manage Shell Commands",
            """
            Use this screen to add, edit, delete, refresh, and archive shell commands.
            - Category: optional grouping name (used for color and headers).
            - Label: button text shown in Shell Commands.
            - Command: the executable or built-in command to run.
            - Args: optional arguments added after the command.
            - Archived: when checked, the command is hidden from Shell Commands but remains here.

            Actions:
            - New: clears the form for a new command.
            - Save: inserts or updates the command.
            - Delete: removes the selected command (confirmation required).
            - Refresh: reloads data and propagates changes to Shell Commands.
            """
        )

        add_tab(
            "list_formatter",
            "Clipboard List Formatter",
            """
            Reformat arbitrary clipboard text into a bracketed or bulleted list.
            - Choose bracket type: (), [], {}, or None.
            - Choose quote style for items: double, single, or none.
            - Choose output style: Bracketed list, Bulleted list, or Single column.
            - For bulleted lists, select bullet character.
            - For single column, items are listed one per line (no bullets/brackets).
            - Option to sort items alphabetically before formatting.
            - Customize the delimiter between items (saved for next use).

            Workflow:
            1. Clipboard content is loaded automatically when you switch to this tab.
            2. Click "Reload from Clipboard" to manually reload clipboard content.
            3. Adjust formatting options (brackets, quotes, delimiter, sorting, etc.).
            4. Click "Format → Copy" to format and copy result to clipboard.
            5. The original clipboard text is preserved, so you can adjust options
               and reformat multiple times without losing the original.

            The preview shows the final formatted content.
            """
        )

        # Select initial tab if provided
        self._select_initial_tab(initial_tab)

    def _select_initial_tab(self, initial_tab: Optional[str]) -> None:
        key = (initial_tab or "").strip().lower()
        mapping = {
            "overview": "overview",
            "clipboard": "clipboard",
            "shell": "shell",
            "manage_clipboard": "manage_clipboard",
            "manage_shell": "manage_shell",
            "list_formatter": "list_formatter",
        }
        tab_key = mapping.get(key, "overview")
        frame = self.tabs.get(tab_key)
        if frame is not None:
            idx = self.help_notebook.index(frame)
            self.help_notebook.select(idx)


class ListFormatterTab(ttk.Frame):
    def __init__(self, parent: ttk.Frame, master_app: tk.Tk) -> None:
        super().__init__(parent)
        self.master_app = master_app

        self.status_var = tk.StringVar(value="")
        
        # Store original clipboard text for iterative formatting
        self.original_text: str = ""
        
        # Load saved delimiter
        saved_delimiter = self._load_delimiter()

        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        # Options
        options_frame = ttk.Frame(container)
        options_frame.pack(fill="x")

        # Brackets option
        ttk.Label(options_frame, text="Brackets:").grid(row=0, column=0, sticky="w")
        self.bracket_var = tk.StringVar(value="square")
        self.brackets_row = ttk.Frame(options_frame)
        self.brackets_row.grid(row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Radiobutton(self.brackets_row, text="()", value="paren", variable=self.bracket_var).pack(side="left")
        ttk.Radiobutton(self.brackets_row, text="[]", value="square", variable=self.bracket_var).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(self.brackets_row, text="{}", value="curly", variable=self.bracket_var).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(self.brackets_row, text="None", value="none", variable=self.bracket_var).pack(side="left", padx=(8, 0))

        # Quotes option
        ttk.Label(options_frame, text="Quotes:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.quote_var = tk.StringVar(value="double")
        quotes_row = ttk.Frame(options_frame)
        quotes_row.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(6, 0))
        ttk.Radiobutton(quotes_row, text='Double (")', value="double", variable=self.quote_var).pack(side="left")
        ttk.Radiobutton(quotes_row, text="Single (')", value="single", variable=self.quote_var).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(quotes_row, text="None", value="none", variable=self.quote_var).pack(side="left", padx=(8, 0))

        # Output style
        ttk.Label(options_frame, text="Output:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.output_var = tk.StringVar(value="bracketed")
        output_row = ttk.Frame(options_frame)
        output_row.grid(row=2, column=1, sticky="w", padx=(6, 0), pady=(6, 0))
        ttk.Radiobutton(output_row, text="Bracketed list", value="bracketed", variable=self.output_var, command=self._update_option_states).pack(side="left")
        ttk.Radiobutton(output_row, text="Bulleted list", value="bulleted", variable=self.output_var, command=self._update_option_states).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(output_row, text="Single column", value="single_column", variable=self.output_var, command=self._update_option_states).pack(side="left", padx=(8, 0))

        # Bullet style (only for bulleted output)
        ttk.Label(options_frame, text="Bullet style:").grid(row=3, column=0, sticky="w")
        self.bullet_var = tk.StringVar(value="-")
        self.bullets_row = ttk.Frame(options_frame)
        self.bullets_row.grid(row=3, column=1, sticky="w", padx=(6, 0))
        ttk.Radiobutton(self.bullets_row, text="-", value="-", variable=self.bullet_var).pack(side="left")
        ttk.Radiobutton(self.bullets_row, text="*", value="*", variable=self.bullet_var).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(self.bullets_row, text="•", value="•", variable=self.bullet_var).pack(side="left", padx=(8, 0))
        
        # Output delimiter
        ttk.Label(options_frame, text="Delimiter:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.delimiter_var = tk.StringVar(value=saved_delimiter)
        delimiter_entry = ttk.Entry(options_frame, textvariable=self.delimiter_var, width=15)
        delimiter_entry.grid(row=4, column=1, sticky="w", padx=(6, 0), pady=(6, 0))
        # Bind to save delimiter when changed
        self.delimiter_var.trace_add("write", lambda *args: self._save_delimiter())

        # Sort option
        ttk.Label(options_frame, text="Sort items:").grid(row=5, column=0, sticky="w", pady=(6, 0))
        self.sort_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Sort alphabetically", variable=self.sort_var).grid(row=5, column=1, sticky="w", padx=(6, 0), pady=(6, 0))

        # Actions
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Reload from Clipboard", command=self._reload_from_clipboard).pack(side="left")
        ttk.Button(actions, text="Format → Copy", command=self._on_format).pack(side="left", padx=(6, 0))

        # Output preview
        preview_frame = ttk.Frame(container)
        preview_frame.pack(fill="both", expand=True, pady=(10, 0))
        ttk.Label(preview_frame, text="Preview:").pack(anchor="w")
        self.preview_text = tk.Text(preview_frame, height=6, wrap="word")
        self.preview_text.pack(fill="both", expand=True)
        if hasattr(master_app, "theme"):
            master_app.theme.style_text(self.preview_text)

        # Status
        ttk.Label(
            container, textvariable=self.status_var, anchor="w", style="Status.TLabel"
        ).pack(fill="x", pady=(6, 0))

        self._update_option_states()
        
        # Load initial clipboard content
        self.after(100, self._reload_from_clipboard)

    def _set_children_state(self, frame: ttk.Frame, state: str) -> None:
        try:
            for child in frame.winfo_children():
                try:
                    child.configure(state=state)
                except Exception:
                    pass
        except Exception:
            pass

    def _update_option_states(self) -> None:
        out = self.output_var.get()
        if out == "bulleted":
            self._set_children_state(self.brackets_row, "disabled")
            self._set_children_state(self.bullets_row, "normal")
        elif out == "single_column":
            # Disable both brackets and bullets for single column
            self._set_children_state(self.brackets_row, "disabled")
            self._set_children_state(self.bullets_row, "disabled")
        else:
            self._set_children_state(self.brackets_row, "normal")
            self._set_children_state(self.bullets_row, "disabled")

    def _reload_from_clipboard(self) -> None:
        """Load text from clipboard into memory for formatting."""
        try:
            self.original_text = self.master_app.clipboard_get()
            self.status_var.set("Loaded from clipboard. Ready to format.")
            self._set_preview("")  # Clear preview
        except Exception:
            # Silently fail if clipboard is empty on initial load
            self.original_text = ""
            self.status_var.set("Ready to format.")
    
    def _on_format(self) -> None:
        # Use stored original text instead of reading from clipboard
        if not self.original_text:
            messagebox.showwarning("Format", "No text loaded. Click 'Reload from Clipboard' first.")
            return

        formatted = self._format_list_from_text(self.original_text)
        if not formatted:
            messagebox.showinfo("Formatter", "No items found to format.")
            return

        # Write to clipboard and show preview
        try:
            self.master_app.clipboard_clear()
            self.master_app.clipboard_append(formatted)
            self.master_app.update()
            self.status_var.set("Formatted list copied to clipboard.")
            self._set_preview(formatted)
        except Exception as exc:
            messagebox.showerror("Clipboard Error", f"Failed to copy to clipboard:\n{exc}")

    def _set_preview(self, text: str) -> None:
        try:
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", text)
            self.preview_text.configure(state="disabled")
        except Exception:
            pass

    def _format_list_from_text(self, text: str) -> str:
        cleaned = self._purge_existing_formatting(text or "")
        items = self._split_items(cleaned)
        items = [i for i in (s.strip() for s in items) if i]
        if not items:
            return ""

        # Apply sorting if requested
        if self.sort_var.get():
            items = sorted(items, key=str.lower)  # Case-insensitive sort

        quote_style = self.quote_var.get()
        if quote_style == "double":
            items_out = [f"\"{i}\"" for i in items]
        elif quote_style == "single":
            items_out = [f"'{i}'" for i in items]
        else:
            items_out = items

        # Output style
        output_type = self.output_var.get()
        
        if output_type == "bulleted":
            bullet = self.bullet_var.get() or "-"
            lines = [f"{bullet} {i}" for i in items_out]
            return "\n".join(lines)
        elif output_type == "single_column":
            # Single column: one item per line, no bullets or brackets
            return "\n".join(items_out)
        else:
            # Bracketed list
            # Get delimiter, ensure it has a value
            delimiter = self.delimiter_var.get() if hasattr(self, 'delimiter_var') and self.delimiter_var.get() else ", "
            inner = delimiter.join(items_out)
            bracket_style = self.bracket_var.get()
            if bracket_style == "none":
                # No brackets, just return the delimited items
                return inner
            elif bracket_style == "paren":
                left, right = "(", ")"
            elif bracket_style == "curly":
                left, right = "{", "}"
            else:
                left, right = "[", "]"
            return f"{left}{inner}{right}"

    def _purge_existing_formatting(self, text: str) -> str:
        s = text.strip()
        # Remove enclosing brackets repeatedly if they wrap the whole string
        pairs = {("(", ")"), ("[", "]"), ("{", "}")}
        changed = True
        while changed and len(s) >= 2:
            changed = False
            first, last = s[0], s[-1]
            if (first, last) in pairs:
                s = s[1:-1].strip()
                changed = True

        # Split lines and preserve as newlines (don't convert to spaces)
        # This allows _split_items to properly recognize line breaks as delimiters
        lines = [ln.strip() for ln in s.splitlines()]
        # Join with newline instead of space so _split_items can split properly
        s = "\n".join(lines).strip()

        # Remove outermost quotes if the entire string is quoted
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1].strip()

        return s

    def _split_items(self, text: str) -> List[str]:
        # Split by common delimiters: comma, semicolon, pipe, newline, tab
        # Avoid splitting plain spaces to preserve multi-word items
        tokens = re.split(r"[,\;\|\n\r\t]+", text)
        out: List[str] = []
        for tok in tokens:
            t = tok.strip().rstrip(",")
            # Remove bullet markers or numbering prefixes like "-", "*", "•", "1.", "1)", "a.", "a)"
            t = re.sub(r"^\s*(?:[\-\*\u2022]\s+|[0-9]+\s*[.)]\s+|[A-Za-z]\s*[.)]\s+)", "", t)
            t = t.strip().rstrip(",")
            # Strip surrounding single/double quotes from each item
            if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
                t = t[1:-1].strip()
            # Also strip any leftover bracket chars around individual tokens
            if len(t) >= 2 and ((t[0], t[-1]) in {("(", ")"), ("[", "]"), ("{", "}")}):
                t = t[1:-1].strip()
            if t:
                out.append(t)
        return out
    
    def _load_delimiter(self) -> str:
        """Load saved delimiter from geometry store."""
        try:
            if hasattr(self.master_app, 'geometry_store'):
                data = self.master_app.geometry_store.get("list_formatter_delimiter")
                if isinstance(data, str):
                    return data
        except Exception:
            pass
        return ", "  # default delimiter
    
    def _save_delimiter(self) -> None:
        """Save delimiter to geometry store."""
        try:
            if hasattr(self.master_app, 'geometry_store'):
                delimiter = self.delimiter_var.get()
                self.master_app.geometry_store.set_value("list_formatter_delimiter", delimiter)
        except Exception:
            pass


class ClipboardManagerTab(ttk.Frame):
    def __init__(self, parent: ttk.Frame, db: DatabaseManager, master_app: tk.Tk) -> None:
        super().__init__(parent)
        self.db = db
        self.master_app = master_app

        self.current_id: Optional[int] = None

        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        # Top: table
        table_frame = ttk.Frame(container)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "category", "label", "content", "archived")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        self.tree.heading("id", text="ID")
        self.tree.heading("category", text="Category")
        self.tree.heading("label", text="Label")
        self.tree.heading("content", text="Content")
        self.tree.heading("archived", text="Archived")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("category", width=120, anchor="w")
        self.tree.column("label", width=160, anchor="w")
        self.tree.column("content", width=320, anchor="w")
        self.tree.column("archived", width=80, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Form
        form = ttk.Frame(container)
        form.pack(fill="x", pady=(10, 0))

        ttk.Label(form, text="Category:").grid(row=0, column=0, sticky="w")
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form, textvariable=self.category_var, width=32)
        self.category_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(form, text="Label:").grid(row=1, column=0, sticky="w")
        self.label_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.label_var, width=40).grid(row=1, column=1, sticky="ew", padx=(6, 0))

        # Shift rows down by one to make room for Category
        ttk.Label(form, text="Content:").grid(row=2, column=0, sticky="nw", pady=(6, 0))
        self.content_text = tk.Text(form, width=60, height=5, wrap="word")
        self.content_text.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
        if hasattr(master_app, "theme"):
            master_app.theme.style_text(self.content_text)

        # Archived checkbox
        ttk.Label(form, text="Archived:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.archived_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, variable=self.archived_var).grid(row=3, column=1, sticky="w", padx=(6, 0), pady=(6, 0))

        form.columnconfigure(1, weight=1)

        # Actions
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(10, 0))

        ttk.Button(actions, text="New", command=self._on_new).pack(side="left")
        ttk.Button(actions, text="Save", command=self._on_save).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Delete", command=self._on_delete).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Refresh", command=self._refresh_table).pack(side="left", padx=(6, 0))
        self.status_var = tk.StringVar(value="")
        ttk.Label(actions, textvariable=self.status_var, style="Status.TLabel").pack(side="right")

        self._refresh_table()

    def _on_new(self) -> None:
        self.current_id = None
        self.category_var.set("")
        self.label_var.set("")
        self.content_text.delete("1.0", "end")
        self.archived_var.set(False)
        self.tree.selection_remove(self.tree.selection())
        self.status_var.set("New item")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        item_id, category, label, content, archived = item["values"]
        self.current_id = int(item_id)
        self.category_var.set(category or "")
        self.label_var.set(label)
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", content)
        try:
            self.archived_var.set(bool(int(archived)))
        except Exception:
            self.archived_var.set(bool(archived))

    def _refresh_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        for row in self.db.get_clipboard_items():
            self.tree.insert("", "end", values=row)
        self.status_var.set("Refreshed")
        # Refresh category choices
        try:
            cats = self.db.get_distinct_categories("CLIPBOARD_PASTE")
            self.category_combo["values"] = cats
        except Exception:
            pass
        self._refresh_peer_windows()

    def _on_save(self) -> None:
        category = self.category_var.get().strip() or None
        label = self.label_var.get().strip()
        content = self.content_text.get("1.0", "end").strip()
        if not label or not content:
            messagebox.showwarning("Validation", "Label and Content are required.")
            return
        archived = self.archived_var.get()
        if self.current_id is None:
            self.db.add_clipboard_item(category, label, content, archived)
            self.status_var.set("Added")
        else:
            self.db.update_clipboard_item(self.current_id, category, label, content, archived)
            self.status_var.set("Updated")
        self._refresh_table()

    def _on_delete(self) -> None:
        if self.current_id is None:
            messagebox.showinfo("Delete", "Select an item to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this item?"):
            return
        self.db.delete_clipboard_item(self.current_id)
        self._on_new()
        self._refresh_table()
        self.status_var.set("Deleted")

    def _refresh_peer_windows(self) -> None:
        try:
            tab = getattr(self.master_app, "tabs", {}).get("clipboard")
            if tab is not None:
                tab.refresh_items()
        except Exception:
            pass


class ShellCommandsManagerTab(ttk.Frame):
    def __init__(self, parent: ttk.Frame, db: DatabaseManager, master_app: tk.Tk) -> None:
        super().__init__(parent)
        self.db = db
        self.master_app = master_app

        self.current_id: Optional[int] = None

        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        # Top: table
        table_frame = ttk.Frame(container)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "category", "label", "command", "args", "archived")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        self.tree.heading("id", text="ID")
        self.tree.heading("category", text="Category")
        self.tree.heading("label", text="Label")
        self.tree.heading("command", text="Command")
        self.tree.heading("args", text="Args")
        self.tree.heading("archived", text="Archived")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("category", width=120, anchor="w")
        self.tree.column("label", width=160, anchor="w")
        self.tree.column("command", width=180, anchor="w")
        self.tree.column("args", width=180, anchor="w")
        self.tree.column("archived", width=80, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Form
        form = ttk.Frame(container)
        form.pack(fill="x", pady=(10, 0))

        ttk.Label(form, text="Category:").grid(row=0, column=0, sticky="w")
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form, textvariable=self.category_var, width=32)
        self.category_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(form, text="Label:").grid(row=1, column=0, sticky="w")
        self.label_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.label_var, width=40).grid(row=1, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(form, text="Command:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.command_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.command_var, width=40).grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))

        ttk.Label(form, text="Args:").grid(row=3, column=0, sticky="w")
        self.args_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.args_var, width=60).grid(row=3, column=1, sticky="ew", padx=(6, 0))

        # Archived checkbox
        ttk.Label(form, text="Archived:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.archived_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, variable=self.archived_var).grid(row=4, column=1, sticky="w", padx=(6, 0), pady=(6, 0))

        form.columnconfigure(1, weight=1)

        # Actions
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(10, 0))

        ttk.Button(actions, text="New", command=self._on_new).pack(side="left")
        ttk.Button(actions, text="Save", command=self._on_save).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Delete", command=self._on_delete).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Refresh", command=self._refresh_table).pack(side="left", padx=(6, 0))
        self.status_var = tk.StringVar(value="")
        ttk.Label(actions, textvariable=self.status_var, style="Status.TLabel").pack(side="right")

        self._refresh_table()

    def _on_new(self) -> None:
        self.current_id = None
        self.category_var.set("")
        self.label_var.set("")
        self.command_var.set("")
        self.args_var.set("")
        self.archived_var.set(False)
        self.tree.selection_remove(self.tree.selection())
        self.status_var.set("New command")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        item_id, category, label, command, args, archived = item["values"]
        self.current_id = int(item_id)
        self.category_var.set(category or "")
        self.label_var.set(label)
        self.command_var.set(command)
        self.args_var.set(args if args is not None else "")
        try:
            self.archived_var.set(bool(int(archived)))
        except Exception:
            self.archived_var.set(bool(archived))

    def _refresh_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        for row in self.db.get_shell_commands():
            self.tree.insert("", "end", values=row)
        self.status_var.set("Refreshed")
        # Refresh category choices
        try:
            cats = self.db.get_distinct_categories("SHELL_COMMANDS")
            self.category_combo["values"] = cats
        except Exception:
            pass
        self._refresh_peer_windows()

    def _on_save(self) -> None:
        category = self.category_var.get().strip() or None
        label = self.label_var.get().strip()
        command = self.command_var.get().strip()
        args = self.args_var.get().strip()
        if not label or not command:
            messagebox.showwarning("Validation", "Label and Command are required.")
            return
        archived = self.archived_var.get()
        if self.current_id is None:
            self.db.add_shell_command(category, label, command, args if args else None, archived)
            self.status_var.set("Added")
        else:
            self.db.update_shell_command(self.current_id, category, label, command, args if args else None, archived)
            self.status_var.set("Updated")
        self._refresh_table()

    def _on_delete(self) -> None:
        if self.current_id is None:
            messagebox.showinfo("Delete", "Select a command to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this command?"):
            return
        self.db.delete_shell_command(self.current_id)
        self._on_new()
        self._refresh_table()
        self.status_var.set("Deleted")

    def _refresh_peer_windows(self) -> None:
        try:
            tab = getattr(self.master_app, "tabs", {}).get("shell")
            if tab is not None:
                tab.refresh_items()
        except Exception:
            pass


class ManageClipboardWindow(tk.Toplevel):
    """Child window for managing clipboard items."""
    def __init__(self, parent: tk.Tk, db: DatabaseManager) -> None:
        super().__init__(parent)
        self.parent = parent
        self.db = db
        
        self.title("Manage Clipboard Items")
        self.resizable(True, True)
        self.geometry("900x600")
        
        # Create the management tab content
        self.manager_tab = ClipboardManagerTab(self, self.db, self.parent)
        self.manager_tab.pack(fill="both", expand=True)
        
        # Restore geometry if saved
        if hasattr(parent, 'geometry_store'):
            self._restore_geometry_if_saved("manage_clipboard_window")
        
        # Save geometry on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if hasattr(parent, "theme"):
            parent.theme.apply_to_window(self)
    
    def _restore_geometry_if_saved(self, key: str) -> bool:
        try:
            data = self.parent.geometry_store.get(key)
            if not data:
                return False
            x, y, w, h = data.get("x"), data.get("y"), data.get("w"), data.get("h")
            if None in (x, y, w, h):
                return False
            self.update_idletasks()
            self.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
            return True
        except Exception:
            return False
    
    def _save_geometry_for(self, key: str) -> None:
        try:
            self.update_idletasks()
            x = int(self.winfo_x())
            y = int(self.winfo_y())
            w = int(self.winfo_width())
            h = int(self.winfo_height())
            if w <= 1 or h <= 1:
                geom = str(self.winfo_geometry())
                parts = geom.split("+")
                size = parts[0].split("x") if parts else []
                if len(size) == 2:
                    try:
                        w = max(w, int(size[0]))
                        h = max(h, int(size[1]))
                    except Exception:
                        pass
            self.parent.geometry_store.set(key, x, y, w, h)
        except Exception:
            pass
    
    def _on_close(self) -> None:
        try:
            self._save_geometry_for("manage_clipboard_window")
        except Exception:
            pass
        self.destroy()


class ManageShellCommandsWindow(tk.Toplevel):
    """Child window for managing shell commands."""
    def __init__(self, parent: tk.Tk, db: DatabaseManager) -> None:
        super().__init__(parent)
        self.parent = parent
        self.db = db
        
        self.title("Manage Shell Commands")
        self.resizable(True, True)
        self.geometry("900x600")
        
        # Create the management tab content
        self.manager_tab = ShellCommandsManagerTab(self, self.db, self.parent)
        self.manager_tab.pack(fill="both", expand=True)
        
        # Restore geometry if saved
        if hasattr(parent, 'geometry_store'):
            self._restore_geometry_if_saved("manage_shell_commands_window")
        
        # Save geometry on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if hasattr(parent, "theme"):
            parent.theme.apply_to_window(self)
    
    def _restore_geometry_if_saved(self, key: str) -> bool:
        try:
            data = self.parent.geometry_store.get(key)
            if not data:
                return False
            x, y, w, h = data.get("x"), data.get("y"), data.get("w"), data.get("h")
            if None in (x, y, w, h):
                return False
            self.update_idletasks()
            self.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
            return True
        except Exception:
            return False
    
    def _save_geometry_for(self, key: str) -> None:
        try:
            self.update_idletasks()
            x = int(self.winfo_x())
            y = int(self.winfo_y())
            w = int(self.winfo_width())
            h = int(self.winfo_height())
            if w <= 1 or h <= 1:
                geom = str(self.winfo_geometry())
                parts = geom.split("+")
                size = parts[0].split("x") if parts else []
                if len(size) == 2:
                    try:
                        w = max(w, int(size[0]))
                        h = max(h, int(size[1]))
                    except Exception:
                        pass
            self.parent.geometry_store.set(key, x, y, w, h)
        except Exception:
            pass
    
    def _on_close(self) -> None:
        try:
            self._save_geometry_for("manage_shell_commands_window")
        except Exception:
            pass
        self.destroy()


class HelpWindow(tk.Toplevel):
    """Separate window for Help documentation."""
    def __init__(self, parent: tk.Tk, initial_tab: Optional[str] = None) -> None:
        super().__init__(parent)
        self.parent = parent
        
        self.title("Help - Tools Suite")
        self.resizable(True, True)
        self.geometry("800x600")
        
        # Create the help tab content
        self.help_tab = HelpCenterTab(self, self.parent, initial_tab)
        self.help_tab.pack(fill="both", expand=True)
        
        # Restore geometry if saved
        if hasattr(parent, 'geometry_store'):
            self._restore_geometry_if_saved("help_window")
        
        # Save geometry on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if hasattr(parent, "theme"):
            parent.theme.apply_to_window(self)
    
    def _restore_geometry_if_saved(self, key: str) -> bool:
        try:
            data = self.parent.geometry_store.get(key)
            if not data:
                return False
            x, y, w, h = data.get("x"), data.get("y"), data.get("w"), data.get("h")
            if None in (x, y, w, h):
                return False
            self.update_idletasks()
            self.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
            return True
        except Exception:
            return False
    
    def _save_geometry_for(self, key: str) -> None:
        try:
            self.update_idletasks()
            x = int(self.winfo_x())
            y = int(self.winfo_y())
            w = int(self.winfo_width())
            h = int(self.winfo_height())
            if w <= 1 or h <= 1:
                geom = str(self.winfo_geometry())
                parts = geom.split("+")
                size = parts[0].split("x") if parts else []
                if len(size) == 2:
                    try:
                        w = max(w, int(size[0]))
                        h = max(h, int(size[1]))
                    except Exception:
                        pass
            self.parent.geometry_store.set(key, x, y, w, h)
        except Exception:
            pass
    
    def _on_close(self) -> None:
        try:
            self._save_geometry_for("help_window")
        except Exception:
            pass
        self.destroy()


class AboutWindow(tk.Toplevel):
    """Separate window for About information."""
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.parent = parent
        
        self.title("About - Tools Suite")
        self.resizable(False, False)
        self.geometry("400x300")
        
        # Create the about content
        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)
        
        ttk.Label(container, text="Tools Suite", style="Title.TLabel").pack(pady=(10, 5))
        ttk.Label(container, text="A handy little time and typing saver").pack(pady=5)
        ttk.Label(container, text="Version 2.0\n", style="Heading.TLabel").pack(pady=10)
        ttk.Label(
            container,
            text="Organize your clipboard snippets and shell commands\n"
            "with an easy-to-use tabbed interface.\n\n"
            "Features:\n"
            "• Light and dark themes\n"
            "• Customizable button columns and fonts\n"
            "• Menu bar with management windows",
            justify="center",
            wraplength=350,
        ).pack(pady=10)
        
        # Close button
        ttk.Button(container, text="Close", command=self.destroy).pack(pady=15)
        
        if hasattr(parent, "theme"):
            parent.theme.apply_to_window(self)
        
        # Restore geometry if saved (center if not)
        if hasattr(parent, 'geometry_store'):
            if not self._restore_geometry_if_saved("about_window"):
                place_window(self, 400, 300, WindowPosition.CENTER)
        else:
            place_window(self, 400, 300, WindowPosition.CENTER)
        
        # Save geometry on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _restore_geometry_if_saved(self, key: str) -> bool:
        try:
            data = self.parent.geometry_store.get(key)
            if not data:
                return False
            x, y, w, h = data.get("x"), data.get("y"), data.get("w"), data.get("h")
            if None in (x, y, w, h):
                return False
            self.update_idletasks()
            self.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
            return True
        except Exception:
            return False
    
    def _save_geometry_for(self, key: str) -> None:
        try:
            self.update_idletasks()
            x = int(self.winfo_x())
            y = int(self.winfo_y())
            w = int(self.winfo_width())
            h = int(self.winfo_height())
            if w <= 1 or h <= 1:
                geom = str(self.winfo_geometry())
                parts = geom.split("+")
                size = parts[0].split("x") if parts else []
                if len(size) == 2:
                    try:
                        w = max(w, int(size[0]))
                        h = max(h, int(size[1]))
                    except Exception:
                        pass
            self.parent.geometry_store.set(key, x, y, w, h)
        except Exception:
            pass
    
    def _on_close(self) -> None:
        try:
            self._save_geometry_for("about_window")
        except Exception:
            pass
        self.destroy()


class PropertiesWindow(tk.Toplevel):
    """Properties window for configuring application settings."""
    def __init__(self, parent: "CommandBarApp") -> None:
        super().__init__(parent)
        self.parent = parent
        
        self.title("Properties - Tools Suite")
        self.resizable(False, False)
        self.geometry("550x600")
        
        # Main container with vertical scrolling support
        scroll_container = ttk.Frame(self)
        scroll_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(scroll_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        if hasattr(parent, "theme"):
            parent.theme.style_canvas(canvas)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        container = ttk.Frame(canvas, padding=20)
        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_container_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_up(_event):
            canvas.yview_scroll(-1, "units")

        def _on_mousewheel_down(_event):
            canvas.yview_scroll(1, "units")

        def _bind_mousewheel(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel_up)
            canvas.bind_all("<Button-5>", _on_mousewheel_down)

        def _unbind_mousewheel(_event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        container.bind("<Configure>", _on_container_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        container.bind("<Enter>", _bind_mousewheel)
        container.bind("<Leave>", _unbind_mousewheel)
        
        ttk.Label(container, text="Application Properties", style="Heading.TLabel").pack(
            pady=(0, 15)
        )

        # Appearance
        appearance_frame = ttk.LabelFrame(container, text="Appearance", padding=15)
        appearance_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(appearance_frame, text="Color theme:").grid(row=0, column=0, sticky="w", pady=5)
        self.theme_var = tk.StringVar(value=parent.theme.name)
        theme_combo = ttk.Combobox(
            appearance_frame,
            textvariable=self.theme_var,
            values=[THEME_LIGHT, THEME_DARK],
            state="readonly",
            width=14,
        )
        theme_combo.grid(row=0, column=1, padx=(10, 0), sticky="w")
        
        # Database location setting
        db_frame = ttk.LabelFrame(container, text="Database Location", padding=15)
        db_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(db_frame, text="Database file path:").grid(row=0, column=0, sticky="w", pady=5)
        self.db_path_var = tk.StringVar()
        # Get current database path
        current_db_path = parent.geometry_store.get("database_path")
        if current_db_path and isinstance(current_db_path, str):
            self.db_path_var.set(current_db_path)
        else:
            self.db_path_var.set(parent._resolve_db_path())
        
        db_path_frame = ttk.Frame(db_frame)
        db_path_frame.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        db_frame.columnconfigure(1, weight=1)
        
        ttk.Entry(db_path_frame, textvariable=self.db_path_var, width=40).pack(side="left", fill="x", expand=True)
        ttk.Button(db_path_frame, text="Browse...", command=self._browse_database).pack(side="left", padx=(5, 0))
        
        ttk.Label(
            db_frame,
            text="Note: Changing the database requires restarting the application.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
        
        # Column count setting
        columns_frame = ttk.LabelFrame(container, text="Button Layout", padding=15)
        columns_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(columns_frame, text="Number of columns for buttons:").grid(row=0, column=0, sticky="w", pady=5)
        self.columns_var = tk.IntVar(value=get_column_count(parent.geometry_store))
        columns_spinbox = ttk.Spinbox(columns_frame, from_=1, to=10, textvariable=self.columns_var, width=10)
        columns_spinbox.grid(row=0, column=1, padx=(10, 0), sticky="w")
        ttk.Label(columns_frame, text="(1-10)").grid(row=0, column=2, padx=(5, 0), sticky="w")
        
        # Button font setting
        font_frame = ttk.LabelFrame(container, text="Font Settings", padding=15)
        font_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(font_frame, text="Button font:").grid(row=0, column=0, sticky="w", pady=5)
        self.button_font_var = tk.StringVar()
        self.button_font_size_var = tk.IntVar()
        current_button_font = get_button_font(parent.geometry_store)
        self.button_font_var.set(current_button_font[0])
        self.button_font_size_var.set(current_button_font[1])
        
        button_font_frame = ttk.Frame(font_frame)
        button_font_frame.grid(row=0, column=1, padx=(10, 0), sticky="w")
        ttk.Entry(button_font_frame, textvariable=self.button_font_var, width=20).pack(side="left")
        ttk.Label(button_font_frame, text="Size:").pack(side="left", padx=(10, 5))
        ttk.Spinbox(button_font_frame, from_=6, to=24, textvariable=self.button_font_size_var, width=5).pack(side="left")
        ttk.Button(button_font_frame, text="Choose...", command=self._choose_button_font).pack(side="left", padx=(5, 0))
        
        ttk.Label(font_frame, text="Label/Text font:").grid(row=1, column=0, sticky="w", pady=5)
        self.label_font_var = tk.StringVar()
        self.label_font_size_var = tk.IntVar()
        current_label_font = get_label_font(parent.geometry_store)
        self.label_font_var.set(current_label_font[0])
        self.label_font_size_var.set(current_label_font[1])
        
        label_font_frame = ttk.Frame(font_frame)
        label_font_frame.grid(row=1, column=1, padx=(10, 0), sticky="w")
        ttk.Entry(label_font_frame, textvariable=self.label_font_var, width=20).pack(side="left")
        ttk.Label(label_font_frame, text="Size:").pack(side="left", padx=(10, 5))
        ttk.Spinbox(label_font_frame, from_=6, to=24, textvariable=self.label_font_size_var, width=5).pack(side="left")
        ttk.Button(label_font_frame, text="Choose...", command=self._choose_label_font).pack(side="left", padx=(5, 0))
        
        # Action buttons
        button_frame = ttk.Frame(container)
        button_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(button_frame, text="Apply", command=self._apply_settings).pack(side="left", padx=(0, 5))
        ttk.Button(button_frame, text="OK", command=self._ok_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", command=self._reset_defaults).pack(side="right")
        
        # Center window
        place_window(self, 550, 600, WindowPosition.CENTER)
        parent.theme.apply_to_window(self)
        
        # Save geometry on close
        self.protocol("WM_DELETE_WINDOW", self.destroy)
    
    def _browse_database(self) -> None:
        """Browse for database file location."""
        # Get current path or default directory
        current_path = self.db_path_var.get()
        initial_dir = os.path.dirname(current_path) if current_path else self.parent._resolve_base_dir()
        initial_file = os.path.basename(current_path) if current_path else DB_FILENAME
        
        # Open file dialog
        filename = filedialog.asksaveasfilename(
            parent=self,
            title="Select Database File",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=".db",
            filetypes=[
                ("SQLite Database", "*.db"),
                ("All Files", "*.*")
            ]
        )
        
        if filename:
            self.db_path_var.set(filename)
    
    def _choose_button_font(self) -> None:
        """Open font chooser for button font."""
        try:
            current_font = tkfont.Font(family=self.button_font_var.get(), size=self.button_font_size_var.get())
            # Create a simple font selection dialog
            font_families = list(tkfont.families())
            font_families.sort()
            
            # Create a dialog
            dialog = tk.Toplevel(self)
            dialog.title("Choose Button Font")
            dialog.geometry("400x500")
            dialog.resizable(False, False)
            
            frame = ttk.Frame(dialog, padding=10)
            frame.pack(fill="both", expand=True)
            
            ttk.Label(frame, text="Select font family:").pack(anchor="w")
            
            listbox_frame = ttk.Frame(frame)
            listbox_frame.pack(fill="both", expand=True, pady=5)
            
            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)
            
            for font_family in font_families:
                listbox.insert(tk.END, font_family)
            
            # Select current font
            try:
                idx = font_families.index(self.button_font_var.get())
                listbox.selection_set(idx)
                listbox.see(idx)
            except:
                pass
            
            def on_ok():
                selection = listbox.curselection()
                if selection:
                    self.button_font_var.set(font_families[selection[0]])
                dialog.destroy()
            
            ttk.Button(frame, text="OK", command=on_ok).pack(pady=5)
            
            dialog.transient(self)
            dialog.grab_set()
            self.parent.theme.apply_to_window(dialog)
            
        except Exception:
            pass
    
    def _choose_label_font(self) -> None:
        """Open font chooser for label/text font."""
        try:
            current_font = tkfont.Font(family=self.label_font_var.get(), size=self.label_font_size_var.get())
            # Create a simple font selection dialog
            font_families = list(tkfont.families())
            font_families.sort()
            
            # Create a dialog
            dialog = tk.Toplevel(self)
            dialog.title("Choose Label/Text Font")
            dialog.geometry("400x500")
            dialog.resizable(False, False)
            
            frame = ttk.Frame(dialog, padding=10)
            frame.pack(fill="both", expand=True)
            
            ttk.Label(frame, text="Select font family:").pack(anchor="w")
            
            listbox_frame = ttk.Frame(frame)
            listbox_frame.pack(fill="both", expand=True, pady=5)
            
            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)
            
            for font_family in font_families:
                listbox.insert(tk.END, font_family)
            
            # Select current font
            try:
                idx = font_families.index(self.label_font_var.get())
                listbox.selection_set(idx)
                listbox.see(idx)
            except:
                pass
            
            def on_ok():
                selection = listbox.curselection()
                if selection:
                    self.label_font_var.set(font_families[selection[0]])
                dialog.destroy()
            
            ttk.Button(frame, text="OK", command=on_ok).pack(pady=5)
            
            dialog.transient(self)
            dialog.grab_set()
            self.parent.theme.apply_to_window(dialog)
            
        except Exception:
            pass
    
    def _apply_settings(self) -> None:
        """Apply the settings without closing the window."""
        try:
            # Check if database path changed
            db_path = self.db_path_var.get().strip()
            current_db_path = self.parent.geometry_store.get("database_path")
            db_changed = False
            
            if db_path and db_path != current_db_path:
                # Validate the path
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    if not messagebox.askyesno("Create Directory", 
                        f"The directory '{db_dir}' does not exist.\nDo you want to create it?", 
                        parent=self):
                        return
                    try:
                        os.makedirs(db_dir, exist_ok=True)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to create directory:\n{e}", parent=self)
                        return
                
                # Save database path
                self.parent.geometry_store.set_value("database_path", db_path)
                db_changed = True
            
            # Save column count
            columns = self.columns_var.get()
            if 1 <= columns <= 10:
                self.parent.geometry_store.set_value("button_columns", columns)
            
            # Save button font
            button_font = (self.button_font_var.get(), self.button_font_size_var.get())
            self.parent.geometry_store.set_value("button_font", list(button_font))
            
            # Save label font
            label_font = (self.label_font_var.get(), self.label_font_size_var.get())
            self.parent.geometry_store.set_value("label_font", list(label_font))

            # Apply theme and refresh ttk fonts/colors
            theme_choice = self.theme_var.get().strip().lower()
            if theme_choice in (THEME_LIGHT, THEME_DARK):
                self.parent.theme.set_theme(theme_choice, persist=True, refresh_tabs=False)
            else:
                self.parent.theme.configure_ttk()
            self.parent.theme.apply_to_window(self.parent)
            self.parent._theme_child_windows()
            
            # Refresh tabs to apply changes (except database which requires restart)
            if hasattr(self.parent, 'tabs'):
                for tab_name in ["clipboard", "shell"]:
                    tab = self.parent.tabs.get(tab_name)
                    if tab and hasattr(tab, 'refresh_items'):
                        tab.refresh_items()
            
            if db_changed:
                messagebox.showinfo("Settings Applied", 
                    "Settings have been applied successfully.\n\n"
                    "Database location has been changed.\n"
                    "Please restart the application for the change to take effect.", 
                    parent=self)
            else:
                messagebox.showinfo("Settings Applied", 
                    "Settings have been applied successfully.\n"
                    "Changes will take effect immediately.", 
                    parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply settings:\n{e}", parent=self)
    
    def _ok_settings(self) -> None:
        """Apply settings and close the window."""
        self._apply_settings()
        self.destroy()
    
    def _reset_defaults(self) -> None:
        """Reset all settings to default values."""
        if messagebox.askyesno("Reset to Defaults", 
            "Are you sure you want to reset all settings to their default values?\n\n"
            "This will reset:\n"
            "• Database location to default\n"
            "• Button columns to 2\n"
            "• Theme to light\n"
            "• All fonts to defaults", 
            parent=self):
            # Reset database path to default
            default_db_path = os.path.join(self.parent._resolve_base_dir(), DB_FILENAME)
            self.db_path_var.set(default_db_path)
            
            # Reset other settings
            self.columns_var.set(DEFAULT_COLUMNS)
            self.button_font_var.set(DEFAULT_BUTTON_FONT[0])
            self.button_font_size_var.set(DEFAULT_BUTTON_FONT[1])
            self.label_font_var.set(DEFAULT_LABEL_FONT[0])
            self.label_font_size_var.set(DEFAULT_LABEL_FONT[1])
            self.theme_var.set(DEFAULT_THEME)


class CommandBarApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tools Suite V2")
        self.resizable(True, True)
        self.geometry("900x600")

        self.db = DatabaseManager(self._resolve_db_path())
        self.geometry_store = WindowGeometryStore(self._resolve_base_dir())
        self.theme = AppTheme(self, self.geometry_store)

        # Tab references for cross-tab communication
        self.tabs = {}
        
        # Child window references
        self.manage_clipboard_window: Optional[ManageClipboardWindow] = None
        self.manage_shell_commands_window: Optional[ManageShellCommandsWindow] = None
        self.help_window: Optional[HelpWindow] = None
        self.about_window: Optional[AboutWindow] = None
        self.properties_window: Optional[PropertiesWindow] = None
        
        # Create menu bar
        self._create_menu_bar()

        # Main layout with notebook
        container = ttk.Frame(self, padding=4)
        container.pack(fill="both", expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True)

        # Create all tabs (excluding Help and About - now in separate windows)
        self._create_tabs()
        
        # Enable tab drag-and-drop reordering
        self._setup_tab_dragging()
        
        # Bind notebook tab changes to reload clipboard in formatter
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Restore main window geometry if available
        self._restore_geometry_if_saved("main", self)
        
        # Save geometry on app close
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)
        
        # F1 opens help window
        self.bind_all("<F1>", self._on_f1_help)
        
        # Auto-fit height to initial tab after window is displayed
        self.after(100, self._auto_fit_tab_height)

        self.theme.apply_to_window(self)
    
    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = tk.Menu(self)
        self.menubar = menubar
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self._on_app_close, accelerator="Alt+F4")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(
            label="Light Theme",
            command=lambda: self._set_theme(THEME_LIGHT),
        )
        view_menu.add_command(
            label="Dark Theme",
            command=lambda: self._set_theme(THEME_DARK),
        )
        view_menu.add_separator()
        view_menu.add_command(
            label="Toggle Theme",
            command=self._toggle_theme,
            accelerator="Ctrl+T",
        )
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Properties...", command=self.open_properties_window, accelerator="Ctrl+,")
        edit_menu.add_separator()
        edit_menu.add_command(label="Manage Clipboard Items...", command=self.open_manage_clipboard_window)
        edit_menu.add_command(label="Manage Shell Commands...", command=self.open_manage_shell_commands_window)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Help Contents", command=self.open_help_window, accelerator="F1")
        help_menu.add_separator()
        help_menu.add_command(label="About Tools Suite", command=self.open_about_window)

        self.theme.style_menu(menubar)
        
        # Bind keyboard shortcuts
        self.bind_all("<Control-comma>", lambda e: self.open_properties_window())
        self.bind_all("<Control-t>", lambda e: self._toggle_theme())
        self.bind_all("<Control-T>", lambda e: self._toggle_theme())

    def _set_theme(self, name: str) -> None:
        self.theme.set_theme(name)
        self._theme_child_windows()

    def _toggle_theme(self) -> None:
        self.theme.toggle_theme()
        self._theme_child_windows()

    def _theme_child_windows(self) -> None:
        """Re-apply theme to open child windows."""
        for attr in (
            "manage_clipboard_window",
            "manage_shell_commands_window",
            "help_window",
            "about_window",
            "properties_window",
        ):
            win = getattr(self, attr, None)
            if win is not None and win.winfo_exists():
                self.theme.apply_to_window(win)

    def _create_tabs(self) -> None:
        """Create all tabs in the notebook (Help and About are now separate windows)."""
        # Tab 1: Clipboard Paster
        clipboard_tab = ClipboardTab(self.notebook, self.db, self)
        self.notebook.add(clipboard_tab, text="Clipboard Paster")
        self.tabs["clipboard"] = clipboard_tab

        # Tab 2: Shell Commands
        shell_tab = ShellCommandsTab(self.notebook, self.db, self)
        self.notebook.add(shell_tab, text="Shell Commands")
        self.tabs["shell"] = shell_tab

        # Tab 3: List Formatter
        formatter_tab = ListFormatterTab(self.notebook, self)
        self.notebook.add(formatter_tab, text="List Formatter")
        self.tabs["formatter"] = formatter_tab
        
        # Restore saved tab order if available
        self._restore_tab_order()
    
    def _setup_tab_dragging(self) -> None:
        """Setup drag-and-drop reordering for notebook tabs."""
        self._drag_data = {"tab": None, "x": 0}
        
        # Bind mouse events for dragging
        self.notebook.bind("<ButtonPress-1>", self._on_tab_press)
        self.notebook.bind("<B1-Motion>", self._on_tab_drag)
        self.notebook.bind("<ButtonRelease-1>", self._on_tab_release)
    
    def _on_tab_press(self, event) -> None:
        """Handle mouse press on a tab."""
        try:
            # Identify which tab was clicked
            clicked_tab = self.notebook.tk.call(self.notebook._w, "identify", "tab", event.x, event.y)
            if clicked_tab != "":
                self._drag_data["tab"] = int(clicked_tab)
                self._drag_data["x"] = event.x
        except Exception:
            self._drag_data["tab"] = None
    
    def _on_tab_drag(self, event) -> None:
        """Handle dragging motion over tabs."""
        if self._drag_data["tab"] is None:
            return
        
        try:
            # Check if we're over a different tab
            target_tab = self.notebook.tk.call(self.notebook._w, "identify", "tab", event.x, event.y)
            if target_tab != "":
                target_idx = int(target_tab)
                source_idx = self._drag_data["tab"]
                
                # If dragged over a different tab, swap them
                if target_idx != source_idx:
                    # Get the tab widget before moving
                    tab_widget = self.notebook.nametowidget(self.notebook.tabs()[source_idx])
                    tab_text = self.notebook.tab(source_idx, "text")
                    
                    # Remove and re-insert at new position
                    self.notebook.forget(source_idx)
                    self.notebook.insert(target_idx, tab_widget, text=tab_text)
                    
                    # Update drag data to track new position
                    self._drag_data["tab"] = target_idx
                    
                    # Select the moved tab
                    self.notebook.select(target_idx)
        except Exception:
            pass
    
    def _on_tab_release(self, event) -> None:
        """Handle mouse release after dragging."""
        if self._drag_data["tab"] is not None:
            # Save the new tab order
            self._save_tab_order()
        self._drag_data["tab"] = None
    
    def _save_tab_order(self) -> None:
        """Save the current tab order to persistent storage."""
        try:
            # Get current tab order (list of tab texts)
            tab_order = []
            for tab_id in self.notebook.tabs():
                tab_text = self.notebook.tab(tab_id, "text")
                tab_order.append(tab_text)
            
            # Save to geometry store
            self.geometry_store.set_value("tab_order", tab_order)
        except Exception:
            pass
    
    def _restore_tab_order(self) -> None:
        """Restore saved tab order from persistent storage."""
        try:
            saved_order = self.geometry_store.get("tab_order")
            if not saved_order or not isinstance(saved_order, list):
                return
            
            # Build a map of tab text to tab widget
            current_tabs = {}
            for tab_id in self.notebook.tabs():
                tab_text = self.notebook.tab(tab_id, "text")
                tab_widget = self.notebook.nametowidget(tab_id)
                current_tabs[tab_text] = tab_widget
            
            # Remove all tabs
            for tab_id in self.notebook.tabs():
                self.notebook.forget(0)
            
            # Re-add tabs in saved order
            for tab_text in saved_order:
                if tab_text in current_tabs:
                    self.notebook.add(current_tabs[tab_text], text=tab_text)
            
            # Add any tabs that weren't in the saved order (new tabs)
            for tab_text, tab_widget in current_tabs.items():
                if tab_text not in saved_order:
                    self.notebook.add(tab_widget, text=tab_text)
        except Exception:
            pass

    def open_manage_clipboard_window(self) -> None:
        """Open or focus the Manage Clipboard window."""
        if self.manage_clipboard_window is not None and self.manage_clipboard_window.winfo_exists():
            # Window already exists, bring it to front
            self.manage_clipboard_window.lift()
            self.manage_clipboard_window.focus_force()
        else:
            # Create new window
            self.manage_clipboard_window = ManageClipboardWindow(self, self.db)
    
    def open_manage_shell_commands_window(self) -> None:
        """Open or focus the Manage Shell Commands window."""
        if self.manage_shell_commands_window is not None and self.manage_shell_commands_window.winfo_exists():
            # Window already exists, bring it to front
            self.manage_shell_commands_window.lift()
            self.manage_shell_commands_window.focus_force()
        else:
            # Create new window
            self.manage_shell_commands_window = ManageShellCommandsWindow(self, self.db)
    
    def open_help_window(self, initial_tab: Optional[str] = None) -> None:
        """Open or focus the Help window."""
        if self.help_window is not None and self.help_window.winfo_exists():
            # Window already exists, bring it to front
            self.help_window.lift()
            self.help_window.focus_force()
        else:
            # Create new window
            self.help_window = HelpWindow(self, initial_tab)
    
    def open_about_window(self) -> None:
        """Open or focus the About window."""
        if self.about_window is not None and self.about_window.winfo_exists():
            # Window already exists, bring it to front
            self.about_window.lift()
            self.about_window.focus_force()
        else:
            # Create new window
            self.about_window = AboutWindow(self)
    
    def open_properties_window(self) -> None:
        """Open or focus the Properties window."""
        if self.properties_window is not None and self.properties_window.winfo_exists():
            # Window already exists, bring it to front
            self.properties_window.lift()
            self.properties_window.focus_force()
        else:
            # Create new window
            self.properties_window = PropertiesWindow(self)
    
    def _resolve_db_path(self) -> str:
        """Resolve the database path, checking for custom location first."""
        # Check if user has configured a custom database path
        if hasattr(self, 'geometry_store'):
            custom_path = self.geometry_store.get("database_path")
            if custom_path and isinstance(custom_path, str) and custom_path.strip():
                return custom_path.strip()
        
        # Default: Place DB in the same directory as the script
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, DB_FILENAME)

    def _on_tab_changed(self, event=None) -> None:
        """Handle notebook tab change - reload clipboard if formatter tab is selected and auto-fit height."""
        try:
            current_tab = self.notebook.select()
            formatter_tab = self.tabs.get("formatter")
            if formatter_tab and self.notebook.nametowidget(current_tab) == formatter_tab:
                # User switched to List Formatter tab - reload from clipboard
                if hasattr(formatter_tab, '_reload_from_clipboard'):
                    formatter_tab._reload_from_clipboard()
            
            # Auto-fit window height to tab content
            self._auto_fit_tab_height()
        except Exception:
            pass
    
    def _auto_fit_tab_height(self) -> None:
        """Automatically adjust window height to fit current tab content."""
        try:
            # Update to ensure all widgets have proper sizes
            self.update_idletasks()
            
            # Get current tab
            current_tab_id = self.notebook.select()
            if not current_tab_id:
                return
            
            current_tab = self.notebook.nametowidget(current_tab_id)
            
            # Request the preferred size for the current tab
            current_tab.update_idletasks()
            
            # Get the required height for the tab content
            req_height = current_tab.winfo_reqheight()
            
            # Add padding for notebook, window chrome, and margins
            notebook_padding = 50  # Space for tab buttons and notebook padding
            window_chrome = 60     # Space for title bar and borders
            extra_padding = 20     # Extra safety margin
            
            total_height = req_height + notebook_padding + window_chrome + extra_padding
            
            # Get current window dimensions
            current_width = self.winfo_width()
            current_x = self.winfo_x()
            current_y = self.winfo_y()
            
            # Set minimum and maximum heights
            min_height = 400
            max_height = self.winfo_screenheight() - 100  # Leave some space for taskbar
            
            # Constrain the height
            new_height = max(min_height, min(total_height, max_height))
            
            # Only resize if the change is significant (more than 50 pixels difference)
            if abs(self.winfo_height() - new_height) > 50:
                self.geometry(f"{current_width}x{new_height}+{current_x}+{current_y}")
        except Exception:
            pass
    
    def _on_f1_help(self, _event=None) -> None:
        # Open help window
        try:
            self.open_help_window()
        except Exception:
            pass

    def _on_app_close(self) -> None:
        try:
            self._save_geometry_for("main", self)
        except Exception:
            pass
        self.destroy()

    def _restore_geometry_if_saved(self, key: str, window: tk.Misc) -> bool:
        try:
            data = self.geometry_store.get(key)
            if not data:
                return False
            x, y, w, h = data.get("x"), data.get("y"), data.get("w"), data.get("h")
            if None in (x, y, w, h):
                return False
            window.update_idletasks()
            window.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
            return True
        except Exception:
            return False

    def _save_geometry_for(self, key: str, window: tk.Misc) -> None:
        try:
            window.update_idletasks()
            # Use winfo methods to avoid parsing strings
            x = int(window.winfo_x())
            y = int(window.winfo_y())
            w = int(window.winfo_width())
            h = int(window.winfo_height())
            # Fallbacks if width/height are not yet measured
            if w <= 1 or h <= 1:
                # Parse geometry string as last resort
                geom = str(window.winfo_geometry())
                # Expected format: WxH+X+Y
                parts = geom.split("+")
                size = parts[0].split("x") if parts else []
                if len(size) == 2:
                    try:
                        w = max(w, int(size[0]))
                        h = max(h, int(size[1]))
                    except Exception:
                        pass
            self.geometry_store.set(key, x, y, w, h)
        except Exception:
            pass

    def _resolve_base_dir(self) -> str:
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    app = CommandBarApp()
    app.mainloop()


if __name__ == "__main__":
    main()


