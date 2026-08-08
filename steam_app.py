import tkinter as tk

from steam_tracker.ui.main_window import SteamAchievementApp


def main():
    root = tk.Tk()
    SteamAchievementApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
