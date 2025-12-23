#!/usr/bin/env python3
"""
save_blobs.py
-------------
Runs tsschecker using a config file.
Cryptex flags used only for iOS 16+.
"""

import os
import re
import subprocess
import sys

def extract(txt, key):
    m = re.search(rf"\*\*{re.escape(key)}:\*\*\s*`(.*?)`", txt)
    return m.group(1) if m else ""

def ios_major(version):
    try:
        return int(version.split(".")[0])
    except Exception:
        return None

def main():
    cfg = input("Path to config (.mkdn): ").strip()
    if not os.path.exists(cfg):
        print("Config not found.")
        return

    base = os.path.dirname(cfg)
    txt = open(cfg).read()

    device = extract(txt, "Device ID")
    ecid = extract(txt, "ECID")
    ios_version = extract(txt, "iOS Version")
    build_id = extract(txt, "Build ID")
    restore = extract(txt, "Restore Type")
    apnonce = extract(txt, "APNonce")
    generator = extract(txt, "Generator")
    cryptex_seed = extract(txt, "Cryptex1 Seed")
    cryptex_nonce = extract(txt, "Entangled Cryptex1 Nonce")
    cellular = extract(txt, "Cellular")
    bbsnum = extract(txt, "Baseband SNUM")

    major = ios_major(ios_version)
    manifest = os.path.join(base, "BuildManifest.plist")

    modes = ["update", "erase", "ota"] if restore == "all" else [restore]

    for mode in modes:
        out = os.path.join(base, "shsh", f"{ios_version}-{mode}")
        os.makedirs(out, exist_ok=True)

        cmd = [
            "tsschecker",
            "-d", device,
            "-e", ecid,
            "-s",
            "--apnonce", apnonce,
            "-g", generator,
            "--save-path", out
        ]

        if major and major >= 16:
            cmd += ["-x", cryptex_seed, "-t", cryptex_nonce]

        if build_id:
            cmd += ["--buildid", build_id]
        else:
            cmd += ["-i", ios_version]

        if mode == "ota":
            if not os.path.exists(manifest):
                print("Skipping OTA (missing BuildManifest.plist)")
                continue
            cmd += ["-m", manifest, "-o"]
        elif mode == "update":
            cmd.append("-u")
        elif mode == "erase":
            cmd.append("-E")

        if cellular.lower() in ("false", "no", "n"):
            cmd.append("-b")
        elif bbsnum and bbsnum != "N/A":
            cmd += ["-c", bbsnum]

        subprocess.run(cmd)

    print("\nDone.")

if __name__ == "__main__":
    main()
