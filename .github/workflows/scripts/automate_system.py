#!/usr/bin/env python3
"""
Minimal automation runner.

Behavior:
- If AUTOMATE_VIA_SSH env var is "1", it will SSH to SYSTEM_HOST as SYSTEM_USER using SSH_PRIVATE_KEY and run AUTOMATION_COMMAND (or default commands).
- Otherwise it runs the default local commands.
- Returns non-zero exit code on failure so CI fails appropriately.

Dependencies:
- paramiko (only required for SSH mode)
"""

import os
import sys
import json
import subprocess
from typing import Tuple

SSH_MODE = os.getenv("AUTOMATE_VIA_SSH", "") == "1"
SYSTEM_HOST = os.getenv("SYSTEM_HOST", "")
SYSTEM_USER = os.getenv("SYSTEM_USER", "")
SSH_PRIVATE_KEY = os.getenv("SSH_PRIVATE_KEY", "")
AUTOMATION_COMMAND = os.getenv("AUTOMATION_COMMAND", "")

DEFAULT_COMMANDS = [
    # Replace these with the real steps you want automated.
    "echo 'Step 1: Pull latest code or artifacts'",
    "echo 'Step 2: Run tests'",
    "echo 'Step 3: Restart service'",
]

def run_local(commands) -> Tuple[int, str]:
    combined_output = []
    for cmd in commands:
        combined_output.append(f"$ {cmd}")
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        combined_output.append(proc.stdout)
        combined_output.append(proc.stderr)
        if proc.returncode != 0:
            return proc.returncode, "\n".join(combined_output)
    return 0, "\n".join(combined_output)

def run_ssh(commands) -> Tuple[int, str]:
    try:
        import paramiko
    except ImportError:
        return 1, "paramiko not installed. Add paramiko to requirements.txt or install it."

    if not (SYSTEM_HOST and SYSTEM_USER and SSH_PRIVATE_KEY):
        return 1, "Missing SYSTEM_HOST, SYSTEM_USER or SSH_PRIVATE_KEY for SSH mode."

    key = paramiko.RSAKey.from_private_key(io.StringIO(SSH_PRIVATE_KEY))
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=SYSTEM_HOST, username=SYSTEM_USER, pkey=key, timeout=20)
        out_lines = []
        for cmd in commands:
            stdin, stdout, stderr = client.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            out_lines.append(f"$ {cmd}")
            out_lines.append(stdout.read().decode())
            out_lines.append(stderr.read().decode())
            if exit_status != 0:
                client.close()
                return exit_status, "\n".join(out_lines)
        client.close()
        return 0, "\n".join(out_lines)
    except Exception as e:
        return 1, f"SSH error: {e}"

def main():
    commands = [AUTOMATION_COMMAND] if AUTOMATION_COMMAND else DEFAULT_COMMANDS
    if SSH_MODE:
        code, output = run_ssh(commands)
    else:
        code, output = run_local(commands)

    summary = {
        "ssh_mode": SSH_MODE,
        "system_host": SYSTEM_HOST if SSH_MODE else None,
        "exit_code": code,
        "output": output,
    }

    print(json.dumps(summary, indent=2))
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(code)

if __name__ == "__main__":
    main()
