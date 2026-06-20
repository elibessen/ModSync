import urllib.request
import urllib.parse
import json
import os
import zipfile
import sys


API_BASE = "https://api.modrinth.com/v2"


class ModUpdater:
    def __init__(self, minecraft_version):
        self.mc_version = minecraft_version
        self.mods_folder = self.detect_folder()
        self.cache = {}

    # ---------------- VERSION ----------------

    def set_version(self, v):
        self.mc_version = v

    def get_minecraft_root(self):
        if sys.platform.startswith("win"):
            return os.path.join(os.environ["APPDATA"], ".minecraft")

        if os.path.exists("/mnt/c/Users"):
            for user in os.listdir("/mnt/c/Users"):
                path = os.path.join(
                    "/mnt/c/Users",
                    user,
                    "AppData",
                    "Roaming",
                    ".minecraft"
                )
                if os.path.exists(path):
                    return path

        return os.path.join(os.path.expanduser("~"), ".minecraft")

    def get_installed_versions(self):
        root = self.get_minecraft_root()
        versions_path = os.path.join(root, "versions")

        if not os.path.exists(versions_path):
            return []

        versions = []

        for folder in os.listdir(versions_path):
            folder_path = os.path.join(versions_path, folder)

            if not os.path.isdir(folder_path):
                continue

            json_file = os.path.join(folder_path, f"{folder}.json")

            version_id = None

            try:
                # Preferred: read real Minecraft version id from JSON
                if os.path.exists(json_file):
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    version_id = data.get("id")

                    # IMPORTANT FIX:
                    # fallback to inheritsFrom (used by Fabric/Forge)
                    if not version_id:
                        version_id = data.get("inheritsFrom")

                # fallback to folder name
                if not version_id:
                    version_id = folder

                version_id = str(version_id)

                # FILTER OUT fabric loader profiles properly
                if "fabric-loader" in version_id:
                    continue

                versions.append(version_id)

            except:
                # last resort fallback
                if "fabric-loader" not in folder:
                    versions.append(folder)

        # remove duplicates (preserve order)
        seen = set()
        clean = []
        for v in versions:
            if v not in seen:
                seen.add(v)
                clean.append(v)

        return clean

    # ---------------- PATH ----------------

    def detect_folder(self):
        root = self.get_minecraft_root()
        mods_path = os.path.join(root, "mods")

        if os.path.isdir(mods_path):
            return mods_path

        raise Exception(f"Mods folder not found: {mods_path}")

    # ---------------- MOD DETECTION ----------------

    def detect_mods(self, log):
        mods = []

        log(f"Mods folder: {self.mods_folder}\n")

        for file in os.listdir(self.mods_folder):
            if not file.endswith(".jar"):
                continue

            path = os.path.join(self.mods_folder, file)

            try:
                with zipfile.ZipFile(path, "r") as jar:
                    if "fabric.mod.json" not in jar.namelist():
                        continue

                    data = json.loads(jar.read("fabric.mod.json"))

                    mod_id = data.get("id")
                    mod_version = data.get("version")

                    if mod_id:
                        mods.append({
                            "id": mod_id,
                            "version": mod_version,
                            "file": file
                        })

                        log(f"Detected: {mod_id}")

            except:
                log(f"Skipped {file}")

        return mods

    # ---------------- MODRINTH ----------------

    def search_project(self, mod_id):
        if mod_id in self.cache:
            return self.cache[mod_id]

        url = f"{API_BASE}/search?{urllib.parse.urlencode({'query': mod_id})}"

        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())

        hits = data.get("hits", [])
        if not hits:
            return None

        pid = hits[0]["project_id"]
        self.cache[mod_id] = pid
        return pid

    def get_latest_version(self, project_id):
        params = urllib.parse.urlencode({
            "loaders": json.dumps(["fabric"]),
            "game_versions": json.dumps([self.mc_version])
        })

        url = f"{API_BASE}/project/{project_id}/version?{params}"

        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())

        if not data:
            return None

        return data[0]

    # ---------------- UPDATE CORE ----------------

    def update(self, log, on_fail=None):
        mods = self.detect_mods(log)

        log(f"\nFound {len(mods)} mods\n")

        for mod in mods:
            mod_id = mod["id"]
            old_file = mod["file"]

            log(f"Checking {mod_id}")

            project_id = self.search_project(mod_id)

            if not project_id:
                log(f"[NOT FOUND] {mod_id}\n")
                if on_fail:
                    on_fail(mod_id, "Not found on Modrinth")
                continue

            latest = self.get_latest_version(project_id)

            if not latest:
                log(f"[SKIP] {mod_id}\n")
                if on_fail:
                    on_fail(mod_id, "No compatible version")
                continue

            file_info = latest["files"][0]

            old_path = os.path.join(self.mods_folder, old_file)
            new_name = file_info["filename"]
            new_path = os.path.join(self.mods_folder, new_name)
            tmp_path = new_path + ".tmp"

            try:
                data = urllib.request.urlopen(file_info["url"], timeout=30).read()

                with open(tmp_path, "wb") as f:
                    f.write(data)

                if len(data) < 1000:
                    log(f"[ERROR] {mod_id} invalid file\n")
                    if on_fail:
                        on_fail(mod_id, "Corrupt download")
                    continue

                if os.path.exists(old_path):
                    os.remove(old_path)

                os.rename(tmp_path, new_path)

                log(f"[OK] Installed {new_name}\n")

            except Exception as e:
                log(f"[ERROR] {mod_id}: {e}\n")
                if on_fail:
                    on_fail(mod_id, str(e))

                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        log("\nFinished")