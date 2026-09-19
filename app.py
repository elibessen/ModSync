import ctypes

# DPI fix

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

import customtkinter as ctk
from PIL import Image
import tkinter as tk
import threading
import json
import os
import sys
from updater import ModUpdater

APP_VERSION = "1.2.0"

class ModSyncApp:
    def __init__(self):
        self.app_running = True
        self.progress_lines = {}
        self.failed_mods = []

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.load_config()
        self.updater = ModUpdater(
            self.cfg["minecraft_version"]
        )
        self.root = ctk.CTk()
        self.root.title(
            f"Fabric Mod Updater v{APP_VERSION}"
        )
        self.root.geometry("1100x650")
        self.root.minsize(900, 550)
        self.root.configure(
            fg_color="#0F0F0F"
        )
        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        if sys.platform.startswith("win"):
            self.root.iconbitmap(
                self.resource_path("mod_sync.ico")
            )

        self.create_sidebar()
        self.create_main()

        self.updater.progress_callback = (
            self.update_progress
        )

    def resource_path(self, path):
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(
                sys._MEIPASS,
                path
            )
        return os.path.join(
            os.path.abspath("."),
            path
        )

    def load_config(self):
        with open(
            self.resource_path("config.json"),
            "r"
        ) as f:

            self.cfg = json.load(f)

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.root,
            width=240,
            fg_color="#151515"
        )
        self.sidebar.pack(
            side="left",
            fill="y"
        )
        self.sidebar.pack_propagate(False)

        logo_img = ctk.CTkImage(
            light_image=Image.open(
                self.resource_path(
                    "fabric_logo.png"
                )
            ),
            dark_image=Image.open(
                self.resource_path(
                    "fabric_logo.png"
                )
            ),
            size=(28, 28)
        )

        title_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )
        title_frame.pack(
            pady=(30, 10)
        )
        title_row = ctk.CTkFrame(
            title_frame,
            fg_color="transparent"
        )
        title_row.pack()

        ctk.CTkLabel(
            title_row,
            image=logo_img,
            text=""
        ).pack(
            side="left",
            padx=(0, 6)
        )

        ctk.CTkLabel(
            title_row,
            text="Fabric Updater",
            font=("Segoe UI", 18, "bold")
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            title_frame,
            text=f"Version {APP_VERSION}",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray60")
        ).pack(
            pady=(3, 0)
        )

        self.status = ctk.CTkLabel(
            self.sidebar,
            text="Ready",
            text_color="#00cc66"
        )
        self.status.pack(
            pady=10
        )

        versions = (
            self.updater.get_installed_versions()
        )
        current = self.cfg[
            "minecraft_version"
        ]

        self.version_var = ctk.StringVar(
            value=(
                current
                if current in versions
                else (
                    versions[0]
                    if versions
                    else current
                )
            )
        )

        ctk.CTkOptionMenu(
            self.sidebar,
            values=(
                versions
                if versions
                else [current]
            ),
            variable=self.version_var
        ).pack(
            pady=20,
            padx=20
        )
        self.button = ctk.CTkButton(
            self.sidebar,
            text="Update Mods",
            command=self.start
        )
        self.button.pack(
            pady=25,
            padx=20
        )

        ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        ).pack(
            expand=True,
            fill="both"
        )

        ctk.CTkButton(
            self.sidebar,
            text="Exit",
            command=self.on_close
        ).pack(
            pady=15,
            padx=20,
            side="bottom"
        )

    def create_main(self):
        self.main = ctk.CTkFrame(
            self.root,
            fg_color="#0F0F0F"
        )

        self.main.pack(
            side="right",
            fill="both",
            expand=True
        )

        log_font = ("Consolas", 9)

        self.logbox = tk.Text(
            self.main,
            font=log_font,
            bg="#181818",
            fg="#cccccc",
            insertbackground="white",
            bd=0
        )

        self.logbox.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(20, 10)
        )
        self.logbox.tag_config(
            "ok",
            foreground="#00cc66"
        )
        self.logbox.tag_config(
            "skip",
            foreground="#ff4444"
        )
        self.logbox.tag_config(
            "error",
            foreground="#ff4444"
        )
        self.logbox.tag_config(
            "info",
            foreground="#4da3ff"
        )
        self.logbox.tag_config(
            "default",
            foreground="#cccccc"
        )

        ctk.CTkLabel(
            self.main,
            text="Failed Mods",
            font=("Segoe UI", 13, "bold")
        ).pack(
            anchor="w",
            padx=20
        )

        self.failed_box = tk.Text(
            self.main,
            height=6,
            font=log_font,
            bg="#1f1f1f",
            fg="#ff4444",
            bd=0
        )

        self.failed_box.pack(
            fill="x",
            padx=20,
            pady=(0, 15)
        )

    def on_close(self):
        self.app_running = False
        self.root.destroy()

    def log(self, msg):
        if not self.app_running:
            return
        def _write():
            if not self.app_running:
                return

            self.logbox.insert(
                "end",
                msg + "\n"
            )

            tag = "default"

            if "[OK]" in msg:
                tag = "ok"
            elif "[SKIP]" in msg:
                tag = "skip"
            elif "[ERROR]" in msg:
                tag = "error"
            elif "Checking" in msg:
                tag = "info"

            start = self.logbox.index(
                "end-2l linestart"
            )
            end = self.logbox.index(
                "end-2l lineend"
            )
            self.logbox.tag_add(
                tag,
                start,
                end
            )
            self.logbox.see("end")
        self.root.after(
            0,
            _write
        )

    def update_progress(
        self,
        mod_id,
        current,
        total
    ):
        if not self.app_running:
            return
        if total <= 0:
            total = 1
        percent = int(
            (current / total) * 100
        )
        width = 22
        filled = int(
            (percent / 100) * width
        )
        bar = (
            "#" * filled
            + "-" * (width - filled)
        )
        text = (
            f"{mod_id:<18} "
            f"[{bar}] "
            f"{percent}%"
        )

        def _write():
            if not self.app_running:
                return
            if mod_id in self.progress_lines:
                line = self.progress_lines[
                    mod_id
                ]
                self.logbox.delete(
                    f"{line}.0",
                    f"{line}.end"
                )
                self.logbox.insert(
                    f"{line}.0",
                    text
                )
            else:
                self.logbox.insert(
                    "end",
                    text + "\n"
                )
                self.progress_lines[
                    mod_id
                ] = int(
                    self.logbox.index(
                        "end-2l"
                    ).split(".")[0]
                )
            self.logbox.see("end")
        self.root.after(
            0,
            _write
        )

    def add_fail(
        self,
        mod,
        reason
    ):
        self.failed_mods.append(
            (mod, reason)
        )

        def _write():
            if not self.app_running:
                return
            self.failed_box.insert(
                "end",
                f"{mod} → {reason}\n"
            )

            self.failed_box.see("end")

        self.root.after(
            0,
            _write
        )

    def clear_failed(self):
        self.failed_mods.clear()
        self.failed_box.delete(
            "1.0",
            "end"
        )
    def set_status(
        self,
        text,
        color
    ):
        def _update():
            if not self.app_running:
                return
            self.status.configure(
                text=text,
                text_color=color
            )
        self.root.after(
            0,
            _update
        )

    def run_update(self):
        try:
            self.updater.update(
                self.log,
                on_fail=self.add_fail
            )
            self.set_status(
                "Finished",
                "#00cc66"
            )
            self.log(
                "Done"
            )
        except Exception as e:
            self.set_status(
                "Error",
                "#ff4444"
            )

            self.log(
                f"[ERROR] {e}"
            )

        self.root.after(
            0,
            lambda: self.button.configure(
                state="normal"
            )
        )

    def start(self):
        if not self.app_running:
            return
        self.button.configure(
            state="disabled"
        )
        self.clear_failed()
        self.progress_lines.clear()
        self.logbox.delete(
            "1.0",
            "end"
        )
        self.updater.set_version(
            self.version_var.get()
        )
        self.set_status(
            f"Updating {self.version_var.get()}",
            "#ffaa00"
        )
        self.log(
            "Starting update..."
        )
        threading.Thread(
            target=self.run_update,
            daemon=True
        ).start()
    def run(self):
        self.root.mainloop()

def main():
    app = ModSyncApp()
    app.run()

if __name__ == "__main__":
    main()