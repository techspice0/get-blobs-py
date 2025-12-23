#!/usr/bin/env python3
"""
collect_blob_config.py
-----------------------
Create or modify SHSH blob config files.

Features:
- Modify existing configs (no retyping everything)
- iOS version is authoritative
- Cryptex requested only for iOS 16+
- Optional Build ID (for betas)
- Multiple configs per device
"""

import os
import re
import subprocess
import shutil

# ---------------- Helpers ----------------

def ask(prompt, optional=False):
    while True:
        v = input(prompt).strip()
        if v or optional:
            return v
        print("This field cannot be empty.\n")

def yesno(prompt, default=False):
    v = input(prompt).strip().lower()
    if not v:
        return default
    return v.startswith("y")

def ios_major(version):
    try:
        return int(version.split(".")[0])
    except Exception:
        return None

def load_config(path):
    data = {}
    with open(path) as f:
        for line in f:
            m = re.search(r"\*\*(.+?):\*\*\s*`(.*?)`", line)
            if m:
                data[m.group(1)] = m.group(2)
    return data

def ask_keep(label, key, existing, optional=False):
    default = existing.get(key, "")
    prompt = f"{label} [{default}]: " if default else f"{label}: "
    val = ask(prompt, optional=True)
    return val if val else default

def download_buildmanifest(url, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    internal = "AssetData/boot/BuildManifest.plist"
    dest = os.path.join(target_dir, "BuildManifest.plist")

    subprocess.run(["pzb", "-g", internal, url], check=True)

    if os.path.exists("BuildManifest.plist"):
        shutil.move("BuildManifest.plist", dest)
    else:
        raise RuntimeError("BuildManifest.plist not found after pzb")

# ---------------- Main ----------------

def main():
    print("=== SHSH Blob Config Generator ===\n")

    modify = yesno("Modify an existing config? (y/n): ", default=False)

    existing = {}
    existing_path = None
    device_dir = None

    if modify:
        existing_path = ask("Path to existing .mkdn file: ")
        if not os.path.exists(existing_path):
            print("Config not found.")
            return
        existing = load_config(existing_path)
        device_dir = os.path.dirname(existing_path)
        print(f"Loaded config: {os.path.basename(existing_path)}\n")

    nickname = ask_keep("Device nickname", "Nickname", existing)
    nickname = nickname.replace(" ", "-")

    device = ask_keep("Device identifier (e.g. iPhone11,8)", "Device ID", existing)
    ecid = ask_keep("ECID", "ECID", existing)

    ios_version = ask_keep("iOS version (e.g. 16.7.1)", "iOS Version", existing)
    build_id = ask_keep("Build ID (optional, for betas)", "Build ID", existing, optional=True)

    major = ios_major(ios_version)

    if not device_dir:
        device_dir = os.path.join("blobs", nickname)
    os.makedirs(device_dir, exist_ok=True)

    print("\nRestore type:")
    print("1) OTA  2) Update  3) Erase  4) ALL")
    rtmap = {"1": "ota", "2": "update", "3": "erase", "4": "all"}

    default_rt = existing.get("Restore Type", "")
    restore_choice = ask("Choice (1/2/3/4): ")
    restore_type = rtmap.get(restore_choice, default_rt)

    ota_url = existing.get("OTA URL", "")
    if restore_type in ("ota", "all"):
        ota_url = ask_keep("OTA URL", "OTA URL", existing)
        download_buildmanifest(ota_url, device_dir)

    apnonce = ask_keep("APNonce", "APNonce", existing)
    generator = ask_keep("Generator", "Generator", existing)

    cryptex_seed = ""
    cryptex_nonce = ""

    if major and major >= 16:
        cryptex_seed = ask_keep("Cryptex1 Seed", "Cryptex1 Seed", existing)
        cryptex_nonce = ask_keep(
            "Entangled Cryptex1 Nonce",
            "Entangled Cryptex1 Nonce",
            existing
        )

    cellular_str = ask_keep("Cellular device? (true/false)", "Cellular", existing)
    cellular = cellular_str.lower() in ("true", "yes", "y")

    bbsnum = "N/A"
    if cellular:
        bbsnum = ask_keep("Baseband SNUM", "Baseband SNUM", existing)

    safe_ecid = ecid.replace(":", "").replace(" ", "")
    suffix = build_id if build_id else ios_version
    filename = f"{device}-{safe_ecid}-{suffix}.mkdn"
    path = os.path.join(device_dir, filename)

    with open(path, "w") as f:
        f.write(f"""# SHSH Blob Configuration

## Device
- **Nickname:** `{nickname}`
- **Device ID:** `{device}`
- **ECID:** `{ecid}`
- **iOS Version:** `{ios_version}`
- **Build ID:** `{build_id}`

## Restore
- **Restore Type:** `{restore_type}`
- **OTA URL:** `{ota_url}`

## Security
- **APNonce:** `{apnonce}`
- **Generator:** `{generator}`
- **Cryptex1 Seed:** `{cryptex_seed}`
- **Entangled Cryptex1 Nonce:** `{cryptex_nonce}`

## Baseband
- **Cellular:** `{cellular}`
- **Baseband SNUM:** `{bbsnum}`
""")

    print(f"\nConfig saved to: {path}")

if __name__ == "__main__":
    main()
