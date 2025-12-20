#!/usr/bin/env python3
"""
collect_blob_config.py
-----------------------
Saves config and manifest to blobs/<nickname>/
Supports multiple configs by build number.
Allows interactive modification of existing configs.
Cryptex only for iOS 16+.
"""

import os
import subprocess
import shutil
import re
import sys

# -------------------- Helpers --------------------

def ask(prompt, optional=False):
    while True:
        v = input(prompt).strip()
        if v or optional:
            return v
        print("This field cannot be empty.\n")

def yesno(prompt, default=False):
    resp = input(prompt).strip().lower()
    if not resp:
        return default
    return resp[0] == "y"

def replace_field(text, field, new_value):
    pattern = rf"(\*\*{re.escape(field)}:\*\* `)([^`]*)"
    return re.sub(pattern, rf"\1{new_value}", text)

def ios_major_from_build(build_number):
    # Simple heuristic: first two digits usually major version
    m = re.match(r"(\d+)", build_number)
    if m:
        return int(m.group(1))
    return 0

# -------------------- BuildManifest --------------------

def download_buildmanifest(url, target_dir):
    os.makedirs(target_dir, exist_ok=True)

    manifest_internal_path = "AssetData/boot/BuildManifest.plist"
    local_filename = "BuildManifest.plist"
    final_dest = os.path.join(target_dir, local_filename)

    print("\n--- Downloading BuildManifest.plist ---")
    try:
        subprocess.run(
            ["pzb", "-g", manifest_internal_path, url],
            check=True
        )

        if os.path.exists(local_filename):
            shutil.move(local_filename, final_dest)
            print("BuildManifest.plist moved to:", final_dest)
        else:
            print("Error: BuildManifest.plist not found after pzb run.")
            sys.exit(1)

    except Exception as e:
        print("Error during manifest download:", e)
        sys.exit(1)

# -------------------- Config Selection --------------------

def select_config(device_dir):
    mkdn_files = sorted(f for f in os.listdir(device_dir) if f.endswith(".mkdn"))
    if not mkdn_files:
        print("No config files found.")
        sys.exit(1)

    print("\nAvailable configs:")
    for i, f in enumerate(mkdn_files, 1):
        print(f" {i}) {f}")

    while True:
        sel = ask("Select config number: ")
        if sel.isdigit() and 1 <= int(sel) <= len(mkdn_files):
            return mkdn_files[int(sel) - 1]

# -------------------- Modify Existing --------------------

def modify_existing_config():
    nickname = ask("Existing nickname (folder under blobs/): ").replace(" ", "-")
    device_dir = os.path.join("blobs", nickname)

    if not os.path.isdir(device_dir):
        print("Device directory not found.")
        sys.exit(1)

    config_name = select_config(device_dir)
    config_path = os.path.join(device_dir, config_name)

    with open(config_path, "r") as f:
        contents = f.read()

    print("\nLoaded config:", config_name, "\n")

    build_number = extract_field(contents, "iOS Build")
    major = ios_major_from_build(build_number)
    new_build = None

    if yesno("Modify Generator? (y/n): "):
        generator = ask("New Generator: ")
        contents = replace_field(contents, "Generator", generator)

    if yesno("Modify Build Number? (y/n): "):
        new_build = ask("New iOS build number: ")
        contents = replace_field(contents, "iOS Build", new_build)
        major = ios_major_from_build(new_build)

    if yesno("Modify BuildManifest / OTA URL? (y/n): "):
        ota_url = ask("New OTA URL: ")
        contents = replace_field(contents, "OTA URL", ota_url)
        device_dir_path = os.path.dirname(config_path)
        download_buildmanifest(ota_url, device_dir_path)

    # Cryptex only for iOS 16+
    if major > 15:
        if yesno("Modify Cryptex1 Nonce? (y/n): "):
            cryptex_nonce = ask("New Entangled Cryptex1 Nonce: ")
            contents = replace_field(contents, "Entangled Cryptex1 Nonce", cryptex_nonce)

        if yesno("Modify Cryptex1 Seed? (y/n): "):
            cryptex_seed = ask("New Cryptex1 Seed: ")
            contents = replace_field(contents, "Cryptex1 Seed", cryptex_seed)
    else:
        contents = replace_field(contents, "Entangled Cryptex1 Nonce", "N/A")
        contents = replace_field(contents, "Cryptex1 Seed", "N/A")

    # Rename file if build changed
    if new_build:
        parts = config_name.rsplit("-", 1)
        new_name = f"{parts[0]}-{new_build}.mkdn"
        new_path = os.path.join(device_dir, new_name)
        os.rename(config_path, new_path)
        config_path = new_path
        print("Renamed config to:", new_name)

    with open(config_path, "w") as f:
        f.write(contents)

    print("\nConfig updated successfully.")
    sys.exit(0)

# -------------------- Field extractor --------------------

def extract_field(contents, key):
    m = re.search(rf"\*\*{re.escape(key)}:\*\*\s*`(.*?)`", contents)
    return m.group(1) if m else None

# -------------------- Main --------------------

def main():
    print("=== SHSH Blob Config Generator ===\n")

    if yesno("Do you want to modify an existing config? (y/n): ", default=False):
        modify_existing_config()

    nickname = ask("Enter a nickname for this device (e.g., iphone-xr-black): ").replace(" ", "-")
    device = ask("Device identifier (e.g., iPhone11,8): ")
    ecid = ask("ECID: ")
    build_number = ask("Enter iOS build number (e.g., 17A5777): ")

    major = ios_major_from_build(build_number)

    device_dir = os.path.join("blobs", nickname)
    os.makedirs(device_dir, exist_ok=True)

    print("\nRestore type options: 1) OTA, 2) Update, 3) Erase, 4) ALL")
    rtmap = {"1": "ota", "2": "update", "3": "erase", "4": "all"}
    while True:
        sel = ask("Choose restore type (1/2/3/4): ")
        if sel in rtmap:
            restore_type = rtmap[sel]
            break

    ota_url = ""
    if restore_type in ["ota", "all"]:
        ota_url = ask("Enter OTA URL: ")
        download_buildmanifest(ota_url, device_dir)

    apnonce = ask("APNonce: ")
    generator = ask("Generator: ")

    if major > 15:
        cryptex_nonce = ask("Entangled Cryptex1 Nonce: ")
        print('Use "0x11111111111111111111111111111111" unless needed')
        cryptex_seed = ask("Cryptex1 Seed: ")
    else:
        cryptex_nonce = "N/A"
        cryptex_seed = "N/A"

    cellular = yesno("Is this a cellular device? (y/n): ", default=False)
    bbsnum = ask("Baseband SNUM: ") if cellular else "N/A"

    safe_ecid = ecid.replace(":", "").replace(" ", "")
    filename = f"{device}-{safe_ecid}-{build_number}.mkdn"
    filepath = os.path.join(device_dir, filename)

    contents = f"""# SHSH Blob Configuration
## Device
- **Nickname:** `{nickname}`
- **Device ID:** `{device}`
- **ECID:** `{ecid}`
- **iOS Build:** `{build_number}`

## Restore Mode
- **Restore Type:** `{restore_type}`

## Secure Values
- **APNonce:** `{apnonce}`
- **Generator:** `{generator}`
- **Entangled Cryptex1 Nonce:** `{cryptex_nonce}`
- **Cryptex1 Seed:** `{cryptex_seed}`

## OTA URL
- **OTA URL:** `{ota_url}`

## Baseband
- **Cellular:** `{cellular}`
- **Baseband SNUM:** `{bbsnum}`
"""

    with open(filepath, "w") as f:
        f.write(contents)

    print("\nConfig saved to:", filepath)

# --------------------

if __name__ == "__main__":
    main()
