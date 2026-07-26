import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
import webbrowser
import urllib.parse
import sqlite3

CONFIG_FILE = "steam_profiles.json"
DB_FILE = "steam_games.db"
STEAM_API_ACHIEVEMENTS = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/"
STEAM_API_SCHEMA = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"

GAME_NAME_CORRECTIONS = {
    "49520": "Borderlands 2", "39800": "Borderlands", "397540": "Borderlands 3",
    "292030": "The Witcher 3: Wild Hunt", "72850": "The Elder Scrolls V: Skyrim", "730": "Counter-Strike 2",
}


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, app_id TEXT UNIQUE NOT NULL)""")
    conn.commit()
    conn.close()


def add_game_to_db(name, app_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO games (name, app_id) VALUES (?, ?)", (name, app_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_game_from_db(game_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()


def search_games(query):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, app_id FROM games WHERE name LIKE ? ORDER BY name LIMIT 100", (f"%{query}%",))
    results = cursor.fetchall()
    conn.close()
    return results


def get_all_games():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, app_id FROM games ORDER BY name")
    results = cursor.fetchall()
    conn.close()
    return results


def get_game_by_app_id(app_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, app_id FROM games WHERE app_id = ?", (app_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def import_builtin_popular_games():
    popular_games = [
        ("Counter-Strike 2", "730"), ("Dota 2", "570"), ("PUBG: BATTLEGROUNDS", "578080"),
        ("Apex Legends", "1172470"), ("Grand Theft Auto V", "271590"), ("The Witcher 3: Wild Hunt", "292030"),
        ("Cyberpunk 2077", "1091500"), ("Elden Ring", "1245620"), ("Baldur's Gate 3", "1086940"),
        ("Red Dead Redemption 2", "1174180"), ("Borderlands 2", "49520"), ("Borderlands 3", "397540"),
        ("The Elder Scrolls V: Skyrim", "72850"), ("Fallout 4", "377160"), ("Portal 2", "620"),
        ("Half-Life 2", "220"), ("Team Fortress 2", "440"), ("Left 4 Dead 2", "550"),
        ("Terraria", "105600"), ("Stardew Valley", "413150"), ("Valheim", "892970"),
        ("Rust", "252490"), ("Subnautica", "264710"), ("The Forest", "242760"),
        ("Factorio", "427520"), ("Rimworld", "294100"), ("Cities: Skylines", "255710"),
        ("Civilization VI", "289070"), ("Rocket League", "252950"), ("Resident Evil 4", "2050650"),
        ("Monster Hunter: World", "582010"), ("Hades", "1145350"), ("Hollow Knight", "367520"),
        ("Among Us", "945360"), ("Warframe", "230410"), ("Destiny 2", "1085660")
    ]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    added = 0
    for name, app_id in popular_games:
        try:
            cursor.execute("INSERT OR IGNORE INTO games (name, app_id) VALUES (?, ?)", (name, app_id))
            if cursor.rowcount > 0: added += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return added, f"Добавлено {added} популярных игр (работает без интернета!)"


class SteamAchievementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Steam Achievement Tracker")
        self.root.geometry("950x700")
        self.game_name = ""
        self.app_id = ""
        self.selected_achievement_name = None  # Сохраняем выбранное достижение
        init_db()

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Вставить", command=self.paste_to_focused_widget)

        # Контекстное меню для ачивок — создаём динамически
        self.achievement_context_menu = tk.Menu(self.root, tearoff=0)
        self.achievement_context_menu.add_command(label="🔍 Найти гайд", command=self.open_guide_from_context)
        self.achievement_context_menu.add_command(label="📋 Копировать название", command=self.copy_achievement_name)
        self.achievement_context_menu.add_command(label="🌐 Открыть в Steam", command=self.open_in_steam)

        self.create_input_fields()
        self.create_tabs()
        self.setup_hotkeys()
        self.load_profile_from_file()

    def create_input_fields(self):
        input_frame = tk.Frame(self.root, padx=10, pady=10)
        input_frame.pack(fill="x")

        tk.Label(input_frame, text="🎮 Поиск игры:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w",
                                                                                     pady=5)
        self.game_entry = tk.Entry(input_frame, width=47, font=("Arial", 10))
        self.game_entry.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
        self.game_entry.bind('<KeyRelease>', self.on_game_search)
        self.bind_context_menu(self.game_entry)

        listbox_frame = tk.Frame(input_frame)
        listbox_frame.grid(row=1, column=1, sticky="ew", padx=5)
        self.game_listbox = tk.Listbox(listbox_frame, height=6, font=("Arial", 9))
        self.game_listbox.pack(side="left", fill="both", expand=True)
        self.game_listbox.bind('<<ListboxSelect>>', self.on_game_selected)
        self.game_listbox.bind("<Button-3>", lambda e: "break")
        listbox_scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.game_listbox.yview)
        listbox_scrollbar.pack(side="right", fill="y")
        self.game_listbox.config(yscrollcommand=listbox_scrollbar.set)

        btn_frame = tk.Frame(input_frame)
        btn_frame.grid(row=0, column=2, rowspan=2, padx=5, sticky="n")
        tk.Button(btn_frame, text="📚 База игр", command=self.open_db_manager, bg="#2196F3", fg="white").pack(fill="x",
                                                                                                             pady=2)
        tk.Button(btn_frame, text="📥 Загрузить ТОП игры", command=self.import_popular, bg="#FF9800", fg="white").pack(
            fill="x", pady=2)

        tk.Label(input_frame, text="Steam API Key:").grid(row=2, column=0, sticky="w", pady=2)
        self.api_key_entry = tk.Entry(input_frame, width=50)
        self.api_key_entry.grid(row=2, column=1, pady=2, padx=5, sticky="ew")
        self.bind_context_menu(self.api_key_entry)

        tk.Label(input_frame, text="Steam ID (17 цифр):").grid(row=3, column=0, sticky="w", pady=2)
        self.steam_id_entry = tk.Entry(input_frame, width=50)
        self.steam_id_entry.grid(row=3, column=1, pady=2, padx=5, sticky="ew")
        self.bind_context_menu(self.steam_id_entry)

        tk.Label(input_frame, text="App ID:").grid(row=4, column=0, sticky="w", pady=2)
        self.app_id_entry = tk.Entry(input_frame, width=50)
        self.app_id_entry.grid(row=4, column=1, pady=2, padx=5, sticky="ew")
        self.app_id_entry.insert(0, "49520")
        self.bind_context_menu(self.app_id_entry)

        self.save_profile_var = tk.BooleanVar(value=True)
        tk.Checkbutton(input_frame, text="Запомнить этот профиль", variable=self.save_profile_var).grid(row=5, column=0,
                                                                                                        columnspan=3,
                                                                                                        sticky="w",
                                                                                                        pady=2)

        self.load_btn = tk.Button(input_frame, text="🔍 Получить достижения", command=self.load_data, bg="#4CAF50",
                                  fg="white", font=("Arial", 11, "bold"))
        self.load_btn.grid(row=6, column=0, columnspan=3, pady=10, sticky="we")

    def add_scrollbar(self, frame, widget):
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=widget.yview)
        scrollbar.pack(side="right", fill="y", pady=5)
        widget.config(yscrollcommand=scrollbar.set)

    def on_game_search(self, event):
        query = self.game_entry.get().strip()
        self.game_listbox.delete(0, tk.END)
        if not query: return
        for game_id, name, app_id in search_games(query):
            self.game_listbox.insert(tk.END, f"{name}  [{app_id}]")

    def on_game_selected(self, event):
        selection = self.game_listbox.curselection()
        if not selection: return
        text = self.game_listbox.get(selection[0])
        if "[" in text and text.endswith("]"):
            app_id = text.split("[")[-1][:-1]
            name = text.split("[")[0].strip()
            self.app_id_entry.delete(0, tk.END)
            self.app_id_entry.insert(0, app_id)
            self.game_entry.delete(0, tk.END)
            self.game_entry.insert(0, name)
            self.game_listbox.delete(0, tk.END)

    def open_db_manager(self):
        db_window = tk.Toplevel(self.root)
        db_window.title("Управление базой игр")
        db_window.geometry("700x500")

        tk.Label(db_window, text=" База данных игр Steam", font=("Arial", 14, "bold")).pack(pady=10)

        tree_frame = tk.Frame(db_window)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        tree = ttk.Treeview(tree_frame, columns=("name", "app_id"), show="headings", height=15)
        tree.heading("name", text="Название игры");
        tree.heading("app_id", text="App ID")
        tree.column("name", width=450);
        tree.column("app_id", width=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.config(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True);
        scrollbar.pack(side="right", fill="y")

        def load_games():
            tree.delete(*tree.get_children())
            for game_id, name, app_id in get_all_games():
                tree.insert("", tk.END, iid=game_id, values=(name, app_id))

        load_games()

        add_frame = tk.Frame(db_window, padx=10, pady=5)
        add_frame.pack(fill="x")
        tk.Label(add_frame, text="Название:").pack(side="left")
        name_entry = tk.Entry(add_frame, width=30);
        name_entry.pack(side="left", padx=5)
        tk.Label(add_frame, text="App ID:").pack(side="left")
        appid_entry = tk.Entry(add_frame, width=15);
        appid_entry.pack(side="left", padx=5)

        def add_game():
            name, app_id = name_entry.get().strip(), appid_entry.get().strip()
            if not name or not app_id:
                messagebox.showwarning("Ошибка", "Заполните оба поля!");
                return
            if add_game_to_db(name, app_id):
                name_entry.delete(0, tk.END);
                appid_entry.delete(0, tk.END)
                load_games();
                messagebox.showinfo("Успех", f"Игра '{name}' добавлена!")
            else:
                messagebox.showwarning("Ошибка", "Игра с таким App ID уже существует!")

        def delete_game():
            selection = tree.selection()
            if not selection: return
            if messagebox.askyesno("Подтверждение", "Удалить выбранную игру?"):
                delete_game_from_db(selection[0]);
                load_games()

        tk.Button(add_frame, text="➕ Добавить", command=add_game, bg="#4CAF50", fg="white").pack(side="left", padx=5)
        tk.Button(add_frame, text="🗑 Удалить", command=delete_game, bg="#f44336", fg="white").pack(side="left", padx=5)
        tk.Label(db_window, text=f"Всего игр в базе: {len(get_all_games())}", font=("Arial", 10)).pack(pady=5)

    def import_popular(self):
        added, message = import_builtin_popular_games()
        messagebox.showinfo("Готово", f"{message}\nТеперь поиск по этим играм работает мгновенно.")

    def create_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=5)

        # Вкладка открытых достижений
        self.tab_unlocked = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_unlocked, text="Открытые (0)")

        self.unlocked_tree = ttk.Treeview(self.tab_unlocked, columns=("name", "description"), show="headings",
                                          height=20)
        self.unlocked_tree.heading("name", text="Достижение")
        self.unlocked_tree.heading("description", text="Описание")
        self.unlocked_tree.column("name", width=250)
        self.unlocked_tree.column("description", width=450)
        self.unlocked_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.add_scrollbar(self.tab_unlocked, self.unlocked_tree)

        # Вкладка закрытых достижений
        self.tab_locked = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_locked, text="Закрытые (0)")

        self.locked_tree = ttk.Treeview(self.tab_locked, columns=("name", "description"), show="headings", height=20)
        self.locked_tree.heading("name", text="Достижение")
        self.locked_tree.heading("description", text="Описание")
        self.locked_tree.column("name", width=250)
        self.locked_tree.column("description", width=450)
        self.locked_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.add_scrollbar(self.tab_locked, self.locked_tree)

        # Привязка событий
        self.unlocked_tree.bind("<Double-1>", self.open_guide)
        self.locked_tree.bind("<Double-1>", self.open_guide)
        self.unlocked_tree.bind("<Button-3>", self.show_achievement_context_menu)
        self.locked_tree.bind("<Button-3>", self.show_achievement_context_menu)

    def setup_hotkeys(self):
        self.root.bind_class("Entry", "<Control-v>", lambda e: e.widget.event_generate("<<Paste>>"))

    def bind_context_menu(self, widget):
        widget.bind("<Button-3>", lambda event: self.show_context_menu(event, widget))

    def show_context_menu(self, event, widget):
        widget.focus_set()
        self.context_menu.post(event.x_root, event.y_root)

    def show_achievement_context_menu(self, event):
        widget = event.widget
        # Определяем элемент под курсором
        item = widget.identify_row(event.y)
        if item:
            # Выделяем и сохраняем ссылку
            widget.selection_set(item)
            widget.focus(item)
            # Сохраняем имя достижения
            item_values = widget.item(item)['values']
            if item_values:
                raw_name = item_values[0]
                self.selected_achievement_name = raw_name.replace("✓", "").replace("🔒", "").strip()
            # Показываем меню
            self.achievement_context_menu.post(event.x_root, event.y_root)
        else:
            # Если кликнули в пустую область — снимаем выделение
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
        if not achievement_name: return
        url = f"https://www.google.com/search?q={urllib.parse.quote(f'\"{self.game_name}\" ачивка \"{achievement_name}\" гайд')}"
        webbrowser.open(url)

    def open_guide(self, event):
        widget = event.widget
        selection = widget.selection()
        if not selection: return
        item = widget.item(selection[0])
        clean_name = item['values'][0].replace("✓", "").replace("🔒", "").strip()
        self.search_guide(clean_name)

    def load_profile_from_file(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.api_key_entry.delete(0, tk.END);
                self.steam_id_entry.delete(0, tk.END);
                self.app_id_entry.delete(0, tk.END)
                app_id = str(config.get("app_id", "49520"))
                if "steampowered.com" in app_id or len(app_id) > 10: app_id = "49520"
                self.api_key_entry.insert(0, config.get("api_key", "").strip())
                self.steam_id_entry.insert(0, config.get("steam_id", "").strip())
                self.app_id_entry.insert(0, app_id.strip())
                self.app_id = app_id
                game = get_game_by_app_id(app_id)
                if game:
                    self.game_entry.delete(0, tk.END)
                    self.game_entry.insert(0, game[1])
            except Exception:
                pass

    def save_profile_to_file(self, api_key, steam_id, app_id):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"api_key": api_key, "steam_id": steam_id, "app_id": app_id}, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def get_achievement_names_schema(self, api_key, app_id):
        try:
            res = requests.get(STEAM_API_SCHEMA, params={"key": api_key, "appid": app_id, "l": "russian"}, timeout=15)
            if res.status_code != 200: return {}, "", {}
            data = res.json()
            game_name = data.get('game', {}).get('gameName', "")

            ach_map = {}
            desc_map = {}
            for ach in data.get('game', {}).get('availableGameStats', {}).get('achievements', []):
                name = ach['name']
                ach_map[name] = ach.get('displayName', name)
                description = ach.get('description', '')
                if not description:
                    description = "(Описание отсутствует)"
                desc_map[name] = description

            return ach_map, game_name, desc_map
        except Exception:
            return {}, "", {}

    def load_data(self):
        api_key = self.api_key_entry.get().strip()
        steam_id = self.steam_id_entry.get().strip()
        app_id = self.app_id_entry.get().strip()

        if not api_key or not steam_id or not app_id:
            messagebox.showerror("Ошибка", "Заполните все три поля!");
            return
        if not app_id.isdigit():
            messagebox.showerror("Ошибка", "App ID должен состоять только из цифр.");
            return
        if not steam_id.isdigit() or len(steam_id) != 17:
            messagebox.showerror("Ошибка", "Steam ID должен содержать ровно 17 цифр.");
            return

        self.app_id = app_id

        if self.save_profile_var.get(): self.save_profile_to_file(api_key, steam_id, app_id)

        self.load_btn.config(text="⏳ Связь со Steam...", state="disabled")
        self.root.update_idletasks()

        try:
            user_res = requests.get(STEAM_API_ACHIEVEMENTS,
                                    params={"appid": app_id, "key": api_key, "steamid": steam_id, "l": "russian"},
                                    timeout=15)
            if user_res.status_code == 400: raise Exception("Ошибка 400: Проверьте Steam ID (17 цифр) и App ID.")
            if user_res.status_code == 403: raise Exception("Ошибка 403: Неверный API-ключ или закрытый профиль.")
            if user_res.status_code != 200 or not user_res.text.strip(): raise Exception("Steam вернул пустой ответ.")

            user_data = user_res.json()
            if not user_data.get("playerstats", {}).get("success", True):
                raise Exception(
                    f"Steam вернул ошибку: {user_data.get('playerstats', {}).get('error', 'Неизвестная ошибка')}")

            player_achievements = user_data.get('playerstats', {}).get('achievements', [])
            if not player_achievements: raise Exception("Достижения не найдены. Убедитесь, что вы запускали игру.")

            schema_names, api_game_name, schema_descriptions = self.get_achievement_names_schema(api_key, app_id)

            self.game_name = GAME_NAME_CORRECTIONS.get(app_id) or (get_game_by_app_id(app_id)[1] if get_game_by_app_id(
                app_id) else "") or api_game_name or f"Игра {app_id}"

            self.unlocked_tree.delete(*self.unlocked_tree.get_children())
            self.locked_tree.delete(*self.locked_tree.get_children())

            unlocked_count = locked_count = 0
            no_description_count = 0

            for ach in player_achievements:
                tech_name = ach['apiname']
                display_name = schema_names.get(tech_name) or ach.get('name') or tech_name
                description = schema_descriptions.get(tech_name, "(Описание отсутствует)")

                if description == "(Описание отсутствует)":
                    no_description_count += 1

                if ach.get('achieved') == 1:
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
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            self.load_btn.config(text="🔍 Получить достижения", state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = SteamAchievementApp(root)
    root.mainloop()