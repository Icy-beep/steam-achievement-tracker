import tkinter as tk
from tkinter import ttk, messagebox

from ..database import add_game_to_db, delete_game_from_db, get_all_games


def open_db_manager(parent, on_change=None):
    db_window = tk.Toplevel(parent)
    db_window.title("Управление базой игр")
    db_window.geometry("780x520")

    tk.Label(db_window, text=" База данных игр Steam", font=("Arial", 14, "bold")).pack(pady=10)

    tree_frame = tk.Frame(db_window)
    tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

    columns = ("core_name", "volume", "subtitle", "app_id")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
    tree.heading("core_name", text="Название")
    tree.heading("volume", text="Часть")
    tree.heading("subtitle", text="Подзаголовок")
    tree.heading("app_id", text="App ID")
    tree.column("core_name", width=280)
    tree.column("volume", width=70, anchor="center")
    tree.column("subtitle", width=180)
    tree.column("app_id", width=100, anchor="center")

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.config(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def load_games():
        tree.delete(*tree.get_children())
        for game_id, app_id, core_name, volume, subtitle in get_all_games():
            tree.insert("", tk.END, iid=game_id, values=(core_name, volume or "", subtitle or "", app_id))

    load_games()

    add_frame = tk.Frame(db_window, padx=10, pady=5)
    add_frame.pack(fill="x")

    tk.Label(add_frame, text="Название:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
    core_name_entry = tk.Entry(add_frame, width=22)
    core_name_entry.grid(row=0, column=1, padx=2, pady=2)

    tk.Label(add_frame, text="Часть:").grid(row=0, column=2, sticky="w", padx=2, pady=2)
    volume_entry = tk.Entry(add_frame, width=8)
    volume_entry.grid(row=0, column=3, padx=2, pady=2)

    tk.Label(add_frame, text="Подзаголовок:").grid(row=0, column=4, sticky="w", padx=2, pady=2)
    subtitle_entry = tk.Entry(add_frame, width=18)
    subtitle_entry.grid(row=0, column=5, padx=2, pady=2)

    tk.Label(add_frame, text="App ID:").grid(row=0, column=6, sticky="w", padx=2, pady=2)
    appid_entry = tk.Entry(add_frame, width=12)
    appid_entry.grid(row=0, column=7, padx=2, pady=2)

    def add_game():
        core_name = core_name_entry.get().strip()
        volume = volume_entry.get().strip() or None
        subtitle = subtitle_entry.get().strip() or None
        app_id = appid_entry.get().strip()

        if not core_name or not app_id:
            messagebox.showwarning("Ошибка", "Заполните хотя бы «Название» и «App ID»!")
            return
        if add_game_to_db(app_id, core_name, volume, subtitle):
            core_name_entry.delete(0, tk.END)
            volume_entry.delete(0, tk.END)
            subtitle_entry.delete(0, tk.END)
            appid_entry.delete(0, tk.END)
            load_games()
            if on_change:
                on_change()
            messagebox.showinfo("Успех", f"Игра '{core_name}' добавлена!")
        else:
            messagebox.showwarning("Ошибка", "Игра с таким App ID уже существует!")

    def delete_game():
        selection = tree.selection()
        if not selection:
            return
        if messagebox.askyesno("Подтверждение", "Удалить выбранную игру?"):
            delete_game_from_db(selection[0])
            load_games()
            if on_change:
                on_change()

    btn_frame = tk.Frame(db_window, padx=10, pady=5)
    btn_frame.pack(fill="x")
    tk.Button(btn_frame, text="➕ Добавить", command=add_game, bg="#4CAF50", fg="white").pack(side="left", padx=5)
    tk.Button(btn_frame, text="🗑 Удалить", command=delete_game, bg="#f44336", fg="white").pack(side="left", padx=5)

    tk.Label(db_window, text=f"Всего игр в базе: {len(get_all_games())}", font=("Arial", 10)).pack(pady=5)
