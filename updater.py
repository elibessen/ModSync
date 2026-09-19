import urllib.request
import urllib.parse
import json
import os
import zipfile
import sys
import re
import hashlib

API_BASE = "https://api.modrinth.com/v2"

MODRINTH_SLUGS_LOOKUP = {
    "betterblockentities": "better-block-entities"
}

class ModUpdater:

    def __init__(self, minecraft_version):
        self.mc_version = minecraft_version
        self.mods_folder = self.detect_folder()
        self.cache = {}
        self.progress_callback = None

    # Version

    def set_version(self, version):
        self.mc_version = version

    def get_minecraft_root(self):

        if sys.platform.startswith("win"):
            return os.path.join(os.environ["APPDATA"], ".minecraft")

        # WSL support

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
                if os.path.exists(json_file):
                    with open(
                        json_file,
                        "r",
                        encoding="utf-8"
                    ) as f:
                        data = json.load(f)

                    version_id = data.get("id")

                    if not version_id:
                        version_id = data.get("inheritsFrom")

                if not version_id:
                    version_id = folder

                version_id = str(version_id)
                version_lower = version_id.lower()

                # Remove Fabric loader entries

                if "fabric-loader" in version_lower: continue

                # Remove OptiFine

                if "optifine" in version_lower: continue

                # Remove named snapshots

                if "snapshot" in version_lower: continue

                # Remove 23w31a etc

                if re.match(r"\d+w\d+[a-z]", version_lower): continue

                # Remove pre/rc

                if re.search(r"-(pre|rc)\d*", version_lower): continue

                versions.append(version_id)

            except Exception:
                continue

        # Remove duplicates

        seen = set()
        clean = []

        for version in versions:
            if version not in seen:
                seen.add(version)
                clean.append(version)
        return clean

    # Path

    def detect_folder(self):

        root = self.get_minecraft_root()
        mods_path = os.path.join(root, "mods" )

        if os.path.isdir(mods_path):
            return mods_path
        raise Exception(
            f"Mods folder not found: {mods_path}"
        )

    # Mod detection

    def detect_mods(self, log):

        mods = []
        log(f"Mods folder: {self.mods_folder}")

        for file in os.listdir(self.mods_folder):
            if not file.endswith(".jar"):
                continue
            path = os.path.join(self.mods_folder, file)
            try:
                with zipfile.ZipFile(path, "r") as jar:
                    if "fabric.mod.json" not in jar.namelist():
                        continue
                    data = json.loads(
                        jar.read("fabric.mod.json")
                    )

                    mod_id = data.get("id")
                    mod_name = data.get("name")
                    mod_version = data.get("version")

                    if mod_id:
                        mods.append({
                            "id": mod_id,
                            "name": mod_name,
                            "version": mod_version,
                            "file": file
                        })
                        log(f"Detected: {mod_id}")

            except Exception as e:
                log(f"Skipped {file}: {e}")

        return mods

    # Modrinth search

    def search_project(self, mod_id, mod_name):
        if mod_id in self.cache:
            return self.cache[mod_id]

        mod_id_lower = mod_id.lower()
        normalised_mod_id = mod_id_lower.replace("_", "-")

        search_ids = [mod_id_lower]

        if normalised_mod_id != mod_id_lower:
            search_ids.append(normalised_mod_id)

        if mod_name:
            search_ids.append(mod_name)

        facets = json.dumps([
            ["project_type:mod"],
            ["categories:fabric"]
        ])

        for search_id in search_ids:

            params = urllib.parse.urlencode({
                "query": search_id,
                "facets": facets,
                "limit": 20
            })

            url = (
                f"{API_BASE}/search?"
                f"{params}"
            )

            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(
                    r.read().decode()
                )

            hits = data.get("hits", [])

            print(f"\nSEARCH: {search_id}")
            print(f"RESULTS: {len(hits)}")

            for project in hits:

                slug = project.get("slug", "")
                title = project.get("title", "")
                project_id = project.get("project_id")
                slug_lower = slug.lower()
                title_lower = title.lower()

                if slug_lower == mod_id_lower:
                    self.cache[mod_id] = project_id
                    return project_id

                if slug_lower == normalised_mod_id:
                    self.cache[mod_id] = project_id
                    return project_id

                if mod_name:
                    if title_lower == mod_name.lower():
                        self.cache[mod_id] = project_id
                        return project_id

                # Fall back to a known Modrinth slug.
                project_slug = MODRINTH_SLUGS_LOOKUP.get(mod_id)

                if project_slug:
                    self.cache[mod_id] = project_slug
                    return project_slug

                return None

    def get_latest_version(self, project_id):

        params = urllib.parse.urlencode({
            "loaders": json.dumps(["fabric"]),
            "game_versions": json.dumps([self.mc_version])
        })

        url = (
            f"{API_BASE}/project/"
            f"{project_id}/version?"
            f"{params}"
        )

        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(
                r.read().decode()
            )
        if not data:
            return None

        for version in data:
            game_versions = version.get("game_versions", [])
            if self.mc_version in game_versions:
                return version

        return None

    # File hash

    def get_file_hash(self, file_path):

        sha512 = hashlib.sha512()

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha512.update(chunk)
        return sha512.hexdigest()

    # Update

    def update(self, log, on_fail=None):
        mods = self.detect_mods(log)

        log(f"\nFound {len(mods)} mods\n")

        for mod in mods:
            mod_id = mod["id"]
            old_file = mod["file"]
            log(f"Checking {mod_id}")

            try:
                project_id = self.search_project(mod_id, mod.get("name"))
            except Exception as e:
                log(f"[ERROR] Searching {mod_id}: {e}")
                continue
            if not project_id:
                log(f"[NOT FOUND] {mod_id}")
                if on_fail:
                    on_fail( mod_id, "Not found on Modrinth")
                continue
            try:
                latest = self.get_latest_version(project_id)

            except Exception as e:
                log(f"[ERROR] Getting version for {mod_id}: {e}")
                continue

            if not latest:
                log(f"[SKIP] {mod_id}")
                if on_fail:
                    on_fail(mod_id, "No compatible version")
                continue

            file_info = None

            # Find the primary file

            for file in latest.get("files", []):
                if file.get("primary", False):
                    file_info = file
                    break

            # Fall back to the first file

            if not file_info:
                files = latest.get("files", [])
                if files:
                    file_info = files[0]

            if not file_info:
                log(f"[SKIP] {mod_id}")
                if on_fail:
                    on_fail(mod_id,"No downloadable file")
                continue

            old_path = os.path.join(self.mods_folder,old_file)
            new_name = file_info["filename"]
            new_path = os.path.join(self.mods_folder, new_name)
            tmp_path = new_path + ".tmp"

            # Check if the installed file is already
            # exactly the same as the Modrinth file.

            remote_hash = file_info.get("hashes", {}).get("sha512")

            if remote_hash and os.path.exists(old_path):
                local_hash = self.get_file_hash(old_path)
                if local_hash == remote_hash:
                    log(
                        f"[UP TO DATE] "
                        f"{mod_id} {mod['version']}"
                    )
                    continue
            try:
                with urllib.request.urlopen(file_info["url"], timeout=30
                ) as response:
                    total = int( response.headers.get("Content-Length", 0))

                    downloaded = 0
                    chunk_size = 8192

                    with open(tmp_path, "wb") as f:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break

                            f.write(chunk)
                            downloaded += len(chunk)

                            if self.progress_callback:
                                self.progress_callback(
                                    mod_id,
                                    downloaded,
                                    total
                                )

                if os.path.getsize(tmp_path) < 1000:
                    raise Exception("Corrupt download")

                # Verify the downloaded file against
                # the SHA-512 hash from Modrinth.

                if remote_hash:
                    downloaded_hash = self.get_file_hash(tmp_path)
                    if downloaded_hash != remote_hash:
                        raise Exception("Downloaded file failed hash verification")

                # Read the actual mod version from
                # the downloaded JAR.

                with zipfile.ZipFile(tmp_path, "r") as jar:
                    data = json.loads(
                        jar.read("fabric.mod.json")
                    )
                downloaded_version = data.get("version")

                # The downloaded JAR contains the same
                # mod version that is already installed.

                if downloaded_version == mod["version"]:
                    log(
                        f"[UP TO DATE] "
                        f"{mod_id} {mod['version']}"
                    )
                    os.remove(tmp_path)
                    continue

                log(
                    f"[UPDATE] {mod_id} "
                    f"{mod['version']} -> "
                    f"{downloaded_version}"
                )

                if os.path.exists(old_path):
                    os.remove(old_path)

                os.rename(tmp_path, new_path)

                log(f"[OK] Installed {new_name}")

            except Exception as e:
                log(f"[ERROR] {mod_id}: {e}")

                if on_fail:

                    on_fail(
                        mod_id,
                        str(e)
                    )

                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        log("\nFinished")