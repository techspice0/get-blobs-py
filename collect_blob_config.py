#!/usr/bin/env python3
"""
collect_blob_config.py
-----------------------
Saves config and manifest to blobs/<nickname>/
Fix: Manually moves BuildManifest.plist if pzb saves to root.
"""
import os
import subprocess
import shutil

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

def download_buildmanifest(url, target_dir):
    """Downloads BuildManifest.plist and moves it to the target directory."""
    os.makedirs(target_dir, exist_ok=True)
    
    # Path inside the OTA zip
    manifest_internal_path = "AssetData/boot/BuildManifest.plist"
    # pzb default filename in current directory
    local_filename = "BuildManifest.plist"
    # Ultimate destination
    final_dest = os.path.join(target_dir, local_filename)

    print(f"\n--- Downloading BuildManifest.plist ---")
    try:
        # Run pzb (downloads to root/current dir)
        subprocess.run(["pzb", "-g", manifest_internal_path, url], check=True)
        
        # Check if it landed in the root and move it
        if os.path.exists(local_filename):
            shutil.move(local_filename, final_dest)
            print(f"✅ Moved BuildManifest.plist to: {final_dest}")
        else:
            print("❌ Error: BuildManifest.plist not found in root after pzb run.")
            exit(1)
            
    except Exception as e:
        print(f"❌ Error during manifest download: {e}")
        exit(1)

def main():
    print("=== SHSH Blob Config Generator ===\n")

    nickname = ask("Enter a nickname for this device (e.g., iphone-xr-black): ").replace(" ", "-")
    device = ask("Device identifier (e.g., iPhone11,8): ")
    ecid = ask("ECID: ")
    ios_version = ask("iOS version (e.g., 17.0): ")

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
    cryptex_nonce = ask("Entangled Cryptex1 Nonce: ")
    print('PLEASE USE "0x11111111111111111111111111111111" unless you have a reason not to')
    cryptex_seed = ask("Cryptex1 Seed: ")

    cellular = yesno("Is this a cellular device? (y/n): ", default=False)
    bbsnum = ask("Baseband SNUM: ") if cellular else "N/A"

    safe_ecid = ecid.replace(":", "").replace(" ", "")
    filename = f"{device}-{safe_ecid}.mkdn"
    filepath = os.path.join(device_dir, filename)

    contents = f"""# SHSH Blob Configuration
## Device
- **Nickname:** `{nickname}`
- **Device ID:** `{device}`
- **ECID:** `{ecid}`
- **iOS Version:** `{ios_version}`

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

    print(f"\n✔ Config saved to: {filepath}")

if __name__ == "__main__":
    main()
