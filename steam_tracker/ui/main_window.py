import tkinter as tk
import urllib.parse
import webbrowser
from tkinter import ttk, messagebox

import requests

from ..database import (
    build_full_name,
    get_all_games,
    get_game_by_app_id,
    import_builtin_popular_games,
    init_db,
    search_games,
)
from ..game_data import GAME_NAME_CORRECTIONS
from ..profile import load_profile, save_profile
from ..steam_api import SteamApiError, fetch_achievement_schema, fetch_player_achievements
from .db_manager_window import open_db_manager as open_db_manager_window

HELP_URLS = {
    "api_key": "https://steamcommunity.com/dev/apikey",
    "steam_id": "https://steamcommunity.com/profiles",
    "app_id": "https://steamdb.info/apps/",
}


class SteamAchievementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Steam Achievement Tracker")
        self.root.geometry("950x700")
        self.game_name = ""
        self.app_id = ""
        self.selected_achievement_name = None
        init_db()

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Вставить", command=self.paste_to_focused_widget)

        self.achievement_context_menu = tk.Menu(self.root, tearoff=0)
        self.achievement_context_menu.add_command(label="🔍 Найти гайд", command=self.open_guide_from_context)
        self.achievement_context_menu.add_command(label="📋 Копировать название", command=self.copy_achievement_name)
        self.achievement_context_menu.add_command(label="🌐 Открыть в Steam", command=self.open_in_steam)

        self.create_input_fields()
        self.create_tabs()
        self.setup_hotkeys()
        self.load_profile_from_file()
        self.refresh_game_listbox()

    def create_input_fields(self):
        input_frame = tk.Frame(self.root, padx=10, pady=10)
        input_frame.pack(fill="x")

        tk.Label(input_frame, text="🎮 Поиск игры:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.game_entry = tk.Entry(input_frame, width=47, font=("Arial", 10))
        self.game_entry.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
        self.game_entry.bind("<KeyRelease>", self.on_game_search)
        self.bind_context_menu(self.game_entry)

        listbox_frame = tk.Frame(input_frame)
        listbox_frame.grid(row=1, column=1, sticky="ew", padx=5)
        self.game_listbox = tk.Listbox(listbox_frame, height=6, font=("Arial", 9))
        self.game_listbox.pack(side="left", fill="both", expand=True)
        self.game_listbox.bind("<<ListboxSelect>>", self.on_game_selected)
        self.game_listbox.bind("<Button-3>", lambda e: "break")
        listbox_scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.game_listbox.yview)
        listbox_scrollbar.pack(side="right", fill="y")
        self.game_listbox.config(yscrollcommand=listbox_scrollbar.set)

        btn_frame = tk.Frame(input_frame)
        btn_frame.grid(row=0, column=2, rowspan=2, padx=5, sticky="n")
        tk.Button(
            btn_frame, text="База игр", command=self.open_db_manager, bg="#2196F3", fg="white"
        ).pack(fill="x", pady=2)
        tk.Button(
            btn_frame, text="Загрузить список игр", command=self.import_popular, bg="#FF9800", fg="white"
        ).pack(fill="x", pady=2)
        tk.Button(
            btn_frame, text="Найти карту игры", command=self.open_game_map_search, bg="#009688", fg="white"
        ).pack(fill="x", pady=2)

        tk.Label(input_frame, text="Steam API Key:").grid(row=2, column=0, sticky="w", pady=2)
        self.api_key_entry = tk.Entry(input_frame, width=50)
        self.api_key_entry.grid(row=2, column=1, pady=2, padx=5, sticky="ew")
        self.bind_context_menu(self.api_key_entry)
        self.create_help_button(input_frame, row=2, url=HELP_URLS["api_key"])

        tk.Label(input_frame, text="Steam ID (17 цифр):").grid(row=3, column=0, sticky="w", pady=2)
        self.steam_id_entry = tk.Entry(input_frame, width=50)
        self.steam_id_entry.grid(row=3, column=1, pady=2, padx=5, sticky="ew")
        self.bind_context_menu(self.steam_id_entry)
        self.create_help_button(input_frame, row=3, url=HELP_URLS["steam_id"])

        tk.Label(input_frame, text="App ID:").grid(row=4, column=0, sticky="w", pady=2)
        self.app_id_entry = tk.Entry(input_frame, width=50)
        self.app_id_entry.grid(row=4, column=1, pady=2, padx=5, sticky="ew")
        self.app_id_entry.insert(0, "49520")
        self.bind_context_menu(self.app_id_entry)
        self.create_help_button(input_frame, row=4, url=HELP_URLS["app_id"])

        self.save_profile_var = tk.BooleanVar(value=True)
        tk.Checkbutton(input_frame, text="Запомнить этот профиль", variable=self.save_profile_var).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=2
        )

        self.load_btn = tk.Button(
            input_frame,
            text="Получить достижения",
            command=self.load_data,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
        )
        self.load_btn.grid(row=6, column=0, columnspan=3, pady=10, sticky="we")

    def create_help_button(self, parent, row, url):
        tk.Button(
            parent,
            text="?",
            width=2,
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold"),
            command=lambda: webbrowser.open(url),
        ).grid(row=row, column=2, padx=5, pady=2, sticky="w")

    def add_scrollbar(self, frame, widget):
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=widget.yview)
        scrollbar.pack(side="right", fill="y", pady=5)
        widget.config(yscrollcommand=scrollbar.set)

    def on_game_search(self, event):
        self.refresh_game_listbox()

    def refresh_game_listbox(self):
        query = self.game_entry.get().strip()
        games = search_games(query) if query else get_all_games()
        self.game_listbox.delete(0, tk.END)
        for game_id, app_id, core_name, volume, subtitle in games:
            display_name = build_full_name(core_name, volume, subtitle)
            self.game_listbox.insert(tk.END, f"{display_name}  [{app_id}]")

    def on_game_selected(self, event):
        selection = self.game_listbox.curselection()
        if not selection:
            return
        text = self.game_listbox.get(selection[0])
        if "[" in text and text.endswith("]"):
            app_id = text.split("[")[-1][:-1]
            name = text.split("[")[0].strip()
            self.app_id_entry.delete(0, tk.END)
            self.app_id_entry.insert(0, app_id)
            self.game_entry.delete(0, tk.END)
            self.game_entry.insert(0, name)

    def open_db_manager(self):
        open_db_manager_window(self.root, on_change=self.refresh_game_listbox)

    def import_popular(self):
        added, message = import_builtin_popular_games()
        messagebox.showinfo("Готово", f"{message}\nТеперь поиск по этим играм работает мгновенно.")
        self.refresh_game_listbox()

    def create_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=5)

        self.tab_unlocked = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_unlocked, text="Открытые (0)")
        self.unlocked_tree = self.create_achievements_tree(self.tab_unlocked)

        self.tab_locked = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_locked, text="Закрытые (0)")
        self.locked_tree = self.create_achievements_tree(self.tab_locked)

        for tree in (self.unlocked_tree, self.locked_tree):
            tree.bind("<Double-1>", self.open_guide)
            tree.bind("<Button-3>", self.show_achievement_context_menu)

    def create_achievements_tree(self, tab):
        tree = ttk.Treeview(tab, columns=("name", "description"), show="headings", height=20)
        tree.heading("name", text="Достижение")
        tree.heading("description", text="Описание")
        tree.column("name", width=250)
        tree.column("description", width=450)
        tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.add_scrollbar(tab, tree)
        return tree

    def setup_hotkeys(self):
        self.root.bind_class("Entry", "<Control-v>", lambda e: e.widget.event_generate("<<Paste>>"))

    def bind_context_menu(self, widget):
        widget.bind("<Button-3>", lambda event: self.show_context_menu(event, widget))

    def show_context_menu(self, event, widget):
        widget.focus_set()
        self.context_menu.post(event.x_root, event.y_root)

    def show_achievement_context_menu(self, event):
        widget = event.widget
        item = widget.identify_row(event.y)
        if item:
            widget.selection_set(item)
            widget.focus(item)
            item_values = widget.item(item)["values"]
            if item_values:
                raw_name = item_values[0]
                self.selected_achievement_name = raw_name.replace("✓", "").replace("🔒", "").strip()
            self.achievement_context_menu.post(event.x_root, event.y_root)
        else:
            self.selected_achievement_name = None

    def paste_to_focused_widget(self):
        focused = self.root.focus_get()
        if isinstance(focused, tk.Entry):
            try:
                focused.insert(tk.INSERT, self.root.clipboard_get().strip())
            except tk.TclError:
                pass

    def open_guide_from_context(self):
        if self.selected_achievement_name:
            self.search_guide(self.selected_achievement_name)
        else:
            messagebox.showinfo("Информация", "Сначала выберите достижение правым кликом.")

    def copy_achievement_name(self):
        if self.selected_achievement_name:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.selected_achievement_name)
            messagebox.showinfo("Скопировано", f"Название скопировано:\n{self.selected_achievement_name}")
        else:
            messagebox.showinfo("Информация", "Сначала выберите достижение правым кликом.")

    def open_in_steam(self):
        if self.app_id:
            url = f"https://steamcommunity.com/stats/{self.app_id}/achievements"
            webbrowser.open(url)
        else:
            messagebox.showinfo("Информация", "App ID не задан.")

    def search_guide(self, achievement_name):
        if not achievement_name:
            return
        query = f'"{self.game_name}" ачивка "{achievement_name}" гайд'
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(url)

    def open_game_map_search(self):
        game_name = self.game_entry.get().strip()
        if not game_name:
            messagebox.showinfo("Информация", "Введите или выберите игру в поле поиска.")
            return
        query = f"{game_name} карта игры"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(url)

    def open_guide(self, event):
        widget = event.widget
        selection = widget.selection()
        if not selection:
            return
        item = widget.item(selection[0])
        clean_name = item["values"][0].replace("✓", "").replace("🔒", "").strip()
        self.search_guide(clean_name)

    def load_profile_from_file(self):
        config = load_profile()
        if not config:
            return

        app_id = str(config.get("app_id", "49520"))
        if "steampowered.com" in app_id or len(app_id) > 10:
            app_id = "49520"

        self.api_key_entry.delete(0, tk.END)
        self.steam_id_entry.delete(0, tk.END)
        self.app_id_entry.delete(0, tk.END)
        self.api_key_entry.insert(0, config.get("api_key", "").strip())
        self.steam_id_entry.insert(0, config.get("steam_id", "").strip())
        self.app_id_entry.insert(0, app_id.strip())
        self.app_id = app_id

        game = get_game_by_app_id(app_id)
        if game:
            _, _, core_name, volume, subtitle = game
            self.game_entry.delete(0, tk.END)
            self.game_entry.insert(0, build_full_name(core_name, volume, subtitle))

    def load_data(self):
        api_key = self.api_key_entry.get().strip()
        steam_id = self.steam_id_entry.get().strip()
        app_id = self.app_id_entry.get().strip()

        if not api_key or not steam_id or not app_id:
            messagebox.showerror("Ошибка", "Заполните все три поля!")
            return
        if not app_id.isdigit():
            messagebox.showerror("Ошибка", "App ID должен состоять только из цифр.")
            return
        if not steam_id.isdigit() or len(steam_id) != 17:
            messagebox.showerror("Ошибка", "Steam ID должен содержать ровно 17 цифр.")
            return

        self.app_id = app_id

        if self.save_profile_var.get():
            save_profile(api_key, steam_id, app_id)

        self.load_btn.config(text="⏳ Связь со Steam...", state="disabled")
        self.root.update_idletasks()

        try:
            player_achievements = fetch_player_achievements(api_key, steam_id, app_id)
            schema_names, api_game_name, schema_descriptions = fetch_achievement_schema(api_key, app_id)

            game_in_db = get_game_by_app_id(app_id)
            db_name = build_full_name(game_in_db[2], game_in_db[3], game_in_db[4]) if game_in_db else ""
            self.game_name = (
                GAME_NAME_CORRECTIONS.get(app_id)
                or db_name
                or api_game_name
                or f"Игра {app_id}"
            )

            self.unlocked_tree.delete(*self.unlocked_tree.get_children())
            self.locked_tree.delete(*self.locked_tree.get_children())

            unlocked_count = locked_count = 0
            no_description_count = 0

            for ach in player_achievements:
                tech_name = ach["apiname"]
                display_name = schema_names.get(tech_name) or ach.get("name") or tech_name
                description = schema_descriptions.get(tech_name, "(Описание отсутствует)")

                if description == "(Описание отсутствует)":
                    no_description_count += 1

                if ach.get("achieved") == 1:
                    self.unlocked_tree.insert("", tk.END, values=(f"✓ {display_name}", description))
                    unlocked_count += 1
                else:
                    self.locked_tree.insert("", tk.END, values=(f"🔒 {display_name}", description))
                    locked_count += 1

            self.notebook.tab(0, text=f"Открытые ({unlocked_count})")
            self.notebook.tab(1, text=f"Закрытые ({locked_count})")

            message = f"Игра: {self.game_name}\nОткрыто: {unlocked_count}\nЗакрыто: {locked_count}"
            if no_description_count > 0:
                message += f"\n\n⚠️ У {no_description_count} достижений нет описания (Steam API не предоставляет данные)"
            message += "\n\n💡 Двойной клик по ачивке — поиск гайда\n💡 Правый клик — дополнительные действия"

            messagebox.showinfo("✅ Готово", message)

        except requests.exceptions.Timeout:
            messagebox.showerror("Ошибка", "Превышено время ожидания.")
        except SteamApiError as e:
            messagebox.showerror("Ошибка", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            self.load_btn.config(text="🔍 Получить достижения", state="normal")
