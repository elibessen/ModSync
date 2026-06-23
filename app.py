import customtkinter as ctk
from PIL import Image
import tkinter as tk
import threading
import json
import os
import sys

from updater import ModUpdater


# ---------------- APPEARANCE ----------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ---------------- RESOURCES ----------------

def resource_path(path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, path)

    return os.path.join(os.path.abspath("."), path)


# ---------------- DISPLAY SCALING ----------------

temp = ctk.CTk()

screen_width = temp.winfo_screenwidth()
screen_height = temp.winfo_screenheight()

temp.destroy()

scale = min(
    screen_width / 1920,
    screen_height / 1080
)

scale = max(
    0.9,
    min(scale, 1.5)
)

ctk.set_widget_scaling(scale)
ctk.set_window_scaling(scale)


# ---------------- CONFIG ----------------

with open(resource_path("config.json"), "r") as f:
    cfg = json.load(f)

updater = ModUpdater(
    cfg["minecraft_version"]
)


# ---------------- WINDOW ----------------

root = ctk.CTk()

root.title("Fabric Mod Updater")

root.geometry(
    f"{int(1250*scale)}x{int(750*scale)}"
)

root.configure(
    fg_color="#0F0F0F"
)

if sys.platform.startswith("win"):
    root.iconbitmap(
        resource_path("mod_sync.ico")
    )


# ---------------- SIDEBAR ----------------

sidebar = ctk.CTkFrame(
    root,
    width=int(250*scale),
    fg_color="#151515"
)

sidebar.pack(
    side="left",
    fill="y"
)

sidebar.pack_propagate(False)


logo_img = ctk.CTkImage(
    light_image=Image.open(
        resource_path(
            "fabric_logo.png"
        )
    ),

    dark_image=Image.open(
        resource_path(
            "fabric_logo.png"
        )
    ),

    size=(
        int(30*scale),
        int(30*scale)
    )
)

title_frame = ctk.CTkFrame(
    sidebar,
    fg_color="transparent"
)

title_frame.pack(
    pady=(30,10)
)

logo_label = ctk.CTkLabel(
    title_frame,
    image=logo_img,
    text=""
)

logo_label.pack(
    side="left",
    padx=(0,5)
)

title = ctk.CTkLabel(
    title_frame,
    text="Fabric Updater",
    font=(
        "Segoe UI",
        int(20*scale),
        "bold"
    )
)

title.pack(
    side="left"
)

status = ctk.CTkLabel(
    sidebar,
    text="Ready",
    text_color="#00cc66"
)

status.pack(
    pady=10
)


# ---------------- VERSION SELECT ----------------

versions = updater.get_installed_versions()

current = cfg["minecraft_version"]

version_var = ctk.StringVar(
    value=current if current in versions
    else versions[0]
)


dropdown = ctk.CTkOptionMenu(
    sidebar,
    values=versions,
    variable=version_var
)

dropdown.pack(
    pady=20,
    padx=20
)


# ---------------- MAIN ----------------

main = ctk.CTkFrame(
    root,
    fg_color="#0F0F0F"
)

main.pack(
    side="right",
    fill="both",
    expand=True
)


# ---------------- LOG BOX ----------------

logbox = tk.Text(
    main,
    font=(
        "Consolas",
        int(10*scale)
    ),

    bg="#181818",
    fg="#cccccc",
    insertbackground="white",
    bd=0
)

logbox.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=(20,10)
)

logbox.tag_config(
    "ok",
    foreground="#00cc66"
)

logbox.tag_config(
    "skip",
    foreground="#ff4444"
)

logbox.tag_config(
    "error",
    foreground="#ff4444"
)

logbox.tag_config(
    "info",
    foreground="#4da3ff"
)

logbox.tag_config(
    "default",
    foreground="#cccccc"
)


# ---------------- FAILED MODS ----------------

failed_label = ctk.CTkLabel(
    main,
    text="Failed Mods",
    font=(
        "Segoe UI",
        int(14*scale),
        "bold"
    )
)

failed_label.pack(
    anchor="w",
    padx=20
)

failed_box = tk.Text(
    main,
    height=6,
    font=(
        "Consolas",
        int(10*scale)
    ),

    bg="#1f1f1f",
    fg="#ff4444",
    bd=0
)

failed_box.pack(
    fill="x",
    padx=20,
    pady=(0,20)
)

failed_mods=[]
progress_lines={}


# ---------------- LOGGING ----------------

def log(msg):

    def _write():

        logbox.insert(
            "end",
            msg+"\n"
        )

        if "[OK]" in msg:
            tag="ok"

        elif "[SKIP]" in msg:
            tag="skip"

        elif "[ERROR]" in msg:
            tag="error"

        elif "Checking" in msg:
            tag="info"

        else:
            tag="default"

        start=logbox.index(
            "end-2l linestart"
        )

        end=logbox.index(
            "end-2l lineend"
        )

        logbox.tag_add(
            tag,
            start,
            end
        )

        logbox.see(
            "end"
        )

    root.after(
        0,
        _write
    )


def update_progress(
    mod_id,
    current,
    total
):

    if total<=0:
        total=1

    percent=int(
        current/total*100
    )

    width=25

    filled=int(
        width*percent/100
    )

    bar=(
        "#"*filled
        +
        "-"*(width-filled)
    )

    text=(
        f"{mod_id:<20}"
        f"[{bar}] "
        f"{percent}%"
    )

    def _write():

        if mod_id in progress_lines:

            line=progress_lines[
                mod_id
            ]

            logbox.delete(
                f"{line}.0",
                f"{line}.end"
            )

            logbox.insert(
                f"{line}.0",
                text
            )

        else:

            logbox.insert(
                "end",
                text+"\n"
            )

            line=int(
                logbox.index(
                    "end-2l"
                ).split(".")[0]
            )

            progress_lines[
                mod_id
            ]=line

        logbox.see(
            "end"
        )

    root.after(
        0,
        _write
    )


def add_fail(
    mod,
    reason
):

    failed_mods.append(
        (
            mod,
            reason
        )
    )

    def _write():

        failed_box.insert(
            "end",
            f"{mod} → {reason}\n"
        )

        failed_box.see(
            "end"
        )

    root.after(
        0,
        _write
    )


def clear_failed():

    failed_mods.clear()

    failed_box.delete(
        "1.0",
        "end"
    )


def set_status(
    text,
    color
):

    root.after(
        0,
        lambda: status.configure(
            text=text,
            text_color=color
        )
    )


updater.progress_callback=update_progress


# ---------------- UPDATE ----------------

def run_update():

    button.configure(
        state="disabled"
    )

    clear_failed()

    progress_lines.clear()

    logbox.delete(
        "1.0",
        "end"
    )

    updater.set_version(
        version_var.get()
    )

    set_status(
        f"Updating {version_var.get()}",
        "#ffaa00"
    )

    log(
        "Starting update..."
    )

    try:

        updater.update(
            log,
            on_fail=add_fail
        )

        set_status(
            "Finished",
            "#00cc66"
        )

        log(
            "Done"
        )

    except Exception as e:

        set_status(
            "Error",
            "#ff4444"
        )

        log(
            f"[ERROR] {e}"
        )

    button.configure(
        state="normal"
    )


def start():

    threading.Thread(
        target=run_update,
        daemon=True
    ).start()


button=ctk.CTkButton(
    sidebar,
    text="Update Mods",
    command=start
)

button.pack(
    pady=30,
    padx=20
)


spacer=ctk.CTkFrame(
    sidebar,
    fg_color="transparent"
)

spacer.pack(
    expand=True,
    fill="both"
)


exit_btn=ctk.CTkButton(
    sidebar,
    text="Exit",
    command=root.destroy
)

exit_btn.pack(
    pady=20,
    padx=20,
    side="bottom"
)


root.mainloop()