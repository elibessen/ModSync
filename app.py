import ctypes

# ---------------- DPI FIX ----------------
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


# ---------------- STATE ----------------
app_running = True
progress_lines = {}


# ---------------- THEME ----------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ---------------- RESOURCE PATH ----------------
def resource_path(path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)


# ---------------- CONFIG ----------------
with open(resource_path("config.json"), "r") as f:
    cfg = json.load(f)

updater = ModUpdater(cfg["minecraft_version"])


# ---------------- WINDOW (FIXED SIZE) ----------------
root = ctk.CTk()
root.title("Fabric Mod Updater")

root.geometry("1100x650")
root.minsize(900, 550)

root.configure(fg_color="#0F0F0F")


def on_close():
    global app_running
    app_running = False
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)


if sys.platform.startswith("win"):
    root.iconbitmap(resource_path("mod_sync.ico"))


# ---------------- SIDEBAR ----------------
sidebar = ctk.CTkFrame(root, width=240, fg_color="#151515")
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)


logo_img = ctk.CTkImage(
    light_image=Image.open(resource_path("fabric_logo.png")),
    dark_image=Image.open(resource_path("fabric_logo.png")),
    size=(28, 28)
)

title_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
title_frame.pack(pady=(30, 10))

ctk.CTkLabel(title_frame, image=logo_img, text="").pack(side="left", padx=(0, 6))

ctk.CTkLabel(
    title_frame,
    text="Fabric Updater",
    font=("Segoe UI", 18, "bold")
).pack(side="left")


status = ctk.CTkLabel(sidebar, text="Ready", text_color="#00cc66")
status.pack(pady=10)


# ---------------- VERSION DROPDOWN ----------------
versions = updater.get_installed_versions()
current = cfg["minecraft_version"]

version_var = ctk.StringVar(
    value=current if current in versions else (versions[0] if versions else current)
)

ctk.CTkOptionMenu(
    sidebar,
    values=versions if versions else [current],
    variable=version_var
).pack(pady=20, padx=20)


# ---------------- MAIN ----------------
main = ctk.CTkFrame(root, fg_color="#0F0F0F")
main.pack(side="right", fill="both", expand=True)


# ---------------- LOG BOX ----------------
log_font = ("Consolas", 9)

logbox = tk.Text(
    main,
    font=log_font,
    bg="#181818",
    fg="#cccccc",
    insertbackground="white",
    bd=0
)

logbox.pack(fill="both", expand=True, padx=20, pady=(20, 10))

logbox.tag_config("ok", foreground="#00cc66")
logbox.tag_config("skip", foreground="#ff4444")
logbox.tag_config("error", foreground="#ff4444")
logbox.tag_config("info", foreground="#4da3ff")
logbox.tag_config("default", foreground="#cccccc")


# ---------------- FAILED BOX ----------------
ctk.CTkLabel(
    main,
    text="Failed Mods",
    font=("Segoe UI", 13, "bold")
).pack(anchor="w", padx=20)

failed_box = tk.Text(
    main,
    height=6,
    font=log_font,
    bg="#1f1f1f",
    fg="#ff4444",
    bd=0
)

failed_box.pack(fill="x", padx=20, pady=(0, 15))


failed_mods = []


# ---------------- LOGGING ----------------
def log(msg):
    if not app_running:
        return

    def _write():
        if not app_running:
            return

        logbox.insert("end", msg + "\n")

        tag = "default"
        if "[OK]" in msg:
            tag = "ok"
        elif "[SKIP]" in msg:
            tag = "skip"
        elif "[ERROR]" in msg:
            tag = "error"
        elif "Checking" in msg:
            tag = "info"

        start = logbox.index("end-2l linestart")
        end = logbox.index("end-2l lineend")

        logbox.tag_add(tag, start, end)
        logbox.see("end")

    root.after(0, _write)


# ---------------- PROGRESS BARS ----------------
def update_progress(mod_id, current, total):
    if not app_running:
        return

    if total <= 0:
        total = 1

    percent = int((current / total) * 100)

    width = 22
    filled = int((percent / 100) * width)

    bar = "#" * filled + "-" * (width - filled)

    text = f"{mod_id:<18} [{bar}] {percent}%"

    def _write():
        if not app_running:
            return

        if mod_id in progress_lines:
            line = progress_lines[mod_id]
            logbox.delete(f"{line}.0", f"{line}.end")
            logbox.insert(f"{line}.0", text)
        else:
            logbox.insert("end", text + "\n")
            progress_lines[mod_id] = int(logbox.index("end-2l").split(".")[0])

        logbox.see("end")

    root.after(0, _write)


updater.progress_callback = update_progress


# ---------------- FAIL HANDLER ----------------
def add_fail(mod, reason):
    failed_mods.append((mod, reason))

    def _write():
        failed_box.insert("end", f"{mod} → {reason}\n")
        failed_box.see("end")

    root.after(0, _write)


def clear_failed():
    failed_mods.clear()
    failed_box.delete("1.0", "end")


def set_status(text, color):
    root.after(0, lambda: status.configure(text=text, text_color=color))


# ---------------- UPDATE ----------------
def run_update():
    button.configure(state="disabled")

    clear_failed()
    progress_lines.clear()
    logbox.delete("1.0", "end")

    updater.set_version(version_var.get())

    set_status(f"Updating {version_var.get()}", "#ffaa00")

    log("Starting update...")

    try:
        updater.update(log, on_fail=add_fail)
        set_status("Finished", "#00cc66")
        log("Done")

    except Exception as e:
        set_status("Error", "#ff4444")
        log(f"[ERROR] {e}")

    button.configure(state="normal")


def start():
    if not app_running:
        return
    threading.Thread(target=run_update, daemon=True).start()


# ---------------- BUTTONS ----------------
button = ctk.CTkButton(sidebar, text="Update Mods", command=start)
button.pack(pady=25, padx=20)

ctk.CTkFrame(sidebar, fg_color="transparent").pack(expand=True, fill="both")

ctk.CTkButton(sidebar, text="Exit", command=root.destroy)\
    .pack(pady=15, padx=20, side="bottom")


root.mainloop()