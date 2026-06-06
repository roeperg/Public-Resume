------------------------------
## Tools Suite V2 — Technical Documentation
Version: 2.0
Runtime: Python 3.10+
Dependencies: tkinter (Standard Library), sqlite3 (Standard Library), httpx (Optional)
------------------------------
## 1. System Architecture & Components
Tools Suite V2 is a tabbed desktop administration utility built with Python's standard graphical framework (tkinter/ttk). The software features an event-driven loop execution paradigm, persisting settings across windows using an inline JSON state architecture and relying on an localized SQLite database layer for persistence.

                  +----------------------------------------+
                  ¦           Main Application Window      ¦
                  ¦   [File] [View] [Edit] [Help] (Menus)  ¦
                  +----------------------------------------+
                                      ¦
         +----------------------------+----------------------------+
         ?                            ?                            ?
+------------------+         +------------------+         +------------------+
¦ Tab 1: Clipboard ¦         ¦ Tab 2: Shell     ¦         ¦ Tab 3: Formatter ¦
¦ Buttons (SQLite) ¦         ¦ Commands (SQLite)¦         ¦ In-Memory Re-fmt ¦
+------------------+         +------------------+         +------------------+

------------------------------
## 2. Configuration & Persistence Engine## Core Defaults & Settings Constants
Global constants drive runtime initialization metrics before the state file parsing layer executes:

* DB_FILENAME: "tools_suite.db" — The core relational data store.
* DEFAULT_COLUMNS: 2 — The structural layout constraint for dynamic matrix buttons.
* DEFAULT_BUTTON_FONT / DEFAULT_LABEL_FONT: ("Segoe UI", 10) — Base UI typographies.
* DEFAULT_THEME: "light" — Primary structural visual canvas context.

## Theme & Palette Data Matrix
The user interface alternates between light and dark profiles using predefined hex strings to ensure crisp contrast constraints:

| Color Component | Light Mode Hex Value | Dark Mode Hex Value |
|---|---|---|
| bg | #f3f3f3 | #1e1e1e |
| fg | #1e1e1e | #e8e8e8 |
| surface | #ffffff | #2d2d2d |
| border | #d4d4d4 | #4a4a4a |
| text_bg | #ffffff | #252526 |
| selection_bg | #cce8ff | #264f78 |

------------------------------
## 3. Database Schema Blueprint
The application relies on SQLite to safely manage configuration states and payload data models across sessions.
## CLIPBOARD_PASTE Table Schema
Stores static text lines mapped out dynamically to one-click functional clipboard macro buttons.

CREATE TABLE CLIPBOARD_PASTE (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL DEFAULT 'General',
    label TEXT NOT NULL,
    paste_text TEXT NOT NULL
);

## SHELL_COMMANDS Table Schema
Stores external operational code triggers and arguments routed to the host environment sub-shell engine.

CREATE TABLE SHELL_COMMANDS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL DEFAULT 'General',
    label TEXT NOT NULL,
    command TEXT NOT NULL,
    arguments TEXT
);

------------------------------
## 4. API & Method Specifications## Functional Utilities## _hex_luminance(hex_color: str) -> float
Calculates an explicit, weighted brightness value for background canvas colors based on human eye perception algorithms.

* Formula Applied: 0.299 × Red + 0.587 × Green + 0.114 × Blue
* Returns: Floating point scalar value from 0.0 (pure dark) to 255.0 (pure light).

## get_button_foreground(bg_color: str) -> str
Enforces high UI readability by auto-selecting black (#1e1e1e) or off-white (#f5f5f5) text color based on the computed luminance threshold.

* Cutoff Boundary: > 145.0 luminance yields dark text; otherwise, light text is selected.

## get_pastel_color_for_category(category_name: Optional[str], theme: str = THEME_LIGHT) -> str
Hashes arbitrary string input names to map a consistent, unique pastel background index color from the appropriate palette array.
------------------------------
## Class Components## class AppTheme
Houses theme configurations, applying functional component styles down to standard tkinter and ttk layout widgets.
## __init__(self, root: tk.Misc, geometry_store: WindowGeometryStore) -> None

* Purpose: Constructs a thematic manager instance bound to an active widget space.
* Side-Effects: Inspects state caches, sets base fallback color parameters, and modifies system style registries via configure_ttk().

## configure_ttk(self) -> None

* Purpose: Re-binds structural style behaviors across components (TFrame, TLabel, TButton, TNotebook). Sets target metrics for button padding boundaries (12, 6) and tab padding borders (14, 7).

------------------------------
## 5. View & UI Tab Operations## Tab 1: Clipboard Paster Engine

   1. Reads all elements from the CLIPBOARD_PASTE table.
   2. Organizes buttons into a dynamic grid layout using the configured number of column properties.
   3. Associates a click event callback wrapper to the button component, copying raw text values directly onto the platform-native OS system clipboard layer via root.clipboard_clear() and root.clipboard_append().

## Tab 2: Shell Commands Executer

   1. Parses operational execution properties defined inside SHELL_COMMANDS.
   2. Automatically wraps commands containing space characters in double quotes ("...") to maintain formatting.
   3. Launches external execution routines asynchronously using Python's subprocess.Popen pipeline wrapper within separate context worker threads (threading.Thread) to prevent graphical freezing on long-running tasks.

## Tab 3: Clipboard List Formatter

* Operation Flow: Extracts existing system clipboard payloads -> Evaluates and formats data according to user-selected structural schemas (e.g., bulleted points, markdown brackets) -> Feeds updated values back onto the system clipboard.

