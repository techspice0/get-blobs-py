#!/usr/bin/env python3

import subprocess
import getpass
import shlex

def run(cmd):
    print(f"> {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def run_capture(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def main():
    ip = input("Device IP: ").strip()
    sudo_pw = getpass.getpass("Sudo password on device: ")

    ssh = f"ssh mobile@{ip}"
    scp = f"scp mobile@{ip}"

    # 1. Copy apticket from cryptex using sudo
    run(
        f'{ssh} "echo {shlex.quote(sudo_pw)} | sudo -S '
        'cp /private/preboot/cryptex1/current/apticket* ./"'
    )

    # 2. Find the apticket filename
    apticket = run_capture(
        f'{ssh} "ls apticket.*.im4m"'
    )

    print(f"Found apticket: {apticket}")

    # 3. SCP it locally
    run(f"{scp}:{apticket} ./")

    # 4. Remove remote copy
    run(f'{ssh} "rm {apticket}"')

    # 5. Run img4tool and grep cnch
    run(f"img4tool ./{apticket} | grep cnch")

if __name__ == "__main__":
    main()
