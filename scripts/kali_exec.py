#!/usr/bin/env python3
"""Run a command on a remote Kali host over SSH and capture output.

Auth (in priority order):
  1. env KALI_PASSWORD (preferred; never written to disk)
  2. --password (avoid if possible; visible in process list)
  3. SSH private key via config KaliKey / --key

Config file is a PowerShell-style assignment list:
  $KaliHost = '192.168.81.130'
  $KaliUser = 'kali'
  $KaliPort = '22'
  $KaliKey  = ''            # optional path to a private key

A template ships at config/kali.example.ps1.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("paramiko is required: pip install paramiko", file=sys.stderr)
    sys.exit(1)

# Config path relative to this script's directory (self-contained skill).
DEFAULT_CONFIG = str(Path(__file__).resolve().parent.parent / "config" / "kali.ps1")

PS1_ASSIGN = re.compile(
    r"^\s*\$(?P<key>KaliHost|KaliUser|KaliPort|KaliKey)\s*=\s*'(?P<val>[^']*)'\s*$"
)


def load_ps1_config(path):
    data = {"KaliHost": None, "KaliUser": None, "KaliPort": 22, "KaliKey": ""}
    if not path.is_file():
        return data
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = PS1_ASSIGN.match(line)
        if not m:
            continue
        key = m.group("key")
        val = m.group("val")
        if key == "KaliPort":
            data[key] = int(val) if val else 22
        else:
            data[key] = val
    return data


def connect(host, port, user, password=None, key_path=None):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = {
        "hostname": host,
        "port": port,
        "username": user,
        "timeout": 20,
        "allow_agent": False,
        "look_for_keys": False,
        "banner_timeout": 30,
        "auth_timeout": 30,
    }
    if key_path:
        kwargs["key_filename"] = key_path
        kwargs["look_for_keys"] = True
    if password:
        kwargs["password"] = password
    client.connect(**kwargs)
    return client


def run_remote(client, command, timeout=120):
    started = time.time()
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    return {
        "command": command,
        "exit_code": code,
        "stdout": out,
        "stderr": err,
        "duration_sec": round(time.time() - started, 3),
    }


def main():
    parser = argparse.ArgumentParser(description="Execute a command on Kali over SSH")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help="Path to kali.ps1-style config (default: <skill>/config/kali.ps1)")
    parser.add_argument("--host", help="Override KaliHost from config")
    parser.add_argument("--user", help="Override KaliUser from config")
    parser.add_argument("--port", type=int, help="Override KaliPort from config")
    parser.add_argument("--key", help="Path to SSH private key")
    parser.add_argument("--password", help="Prefer KALI_PASSWORD env var instead")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Per-command timeout in seconds (default 120)")
    parser.add_argument("--json-out", help="Write result JSON to this path")
    parser.add_argument("--quiet", action="store_true",
                        help="Only print stdout/stderr, not metadata")
    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="Remote command; use -- first")
    args = parser.parse_args()

    cfg = load_ps1_config(Path(args.config))
    # Resolution order (later wins unless overridden by higher priority):
    #   config file  ->  environment variables  ->  CLI arguments
    # Env vars let users switch hosts without touching any file.
    host = args.host or os.environ.get("KALI_HOST") or cfg.get("KaliHost")
    user = args.user or os.environ.get("KALI_USER") or cfg.get("KaliUser")
    port = args.port or os.environ.get("KALI_PORT") or cfg.get("KaliPort") or 22
    key = args.key or os.environ.get("KALI_KEY") or (cfg.get("KaliKey") or None)
    password = args.password or os.environ.get("KALI_PASSWORD")

    command_parts = args.command
    if command_parts and command_parts[0] == "--":
        command_parts = command_parts[1:]
    if not command_parts:
        parser.error("remote command is required, e.g. kali_exec.py -- uname -a")
    command = " ".join(command_parts)

    if not host or not user:
        print(
            "Missing host/user. Provide via one of (priority: CLI > env > config file):\n"
            "  1. CLI:      --host 192.168.x.x --user kali\n"
            "  2. Env vars: KALI_HOST / KALI_USER / KALI_PORT / KALI_KEY\n"
            "  3. Config:   copy config/kali.example.ps1 -> config/kali.ps1 and edit",
            file=sys.stderr,
        )
        return 2
    if not password and not key:
        print("Missing auth. Set env KALI_PASSWORD or provide --key", file=sys.stderr)
        return 2

    try:
        client = connect(host, int(port), user, password, key if key else None)
    except Exception as exc:
        print(f"CONNECT_FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    try:
        result = run_remote(client, command, timeout=args.timeout)
    finally:
        client.close()

    result.update(
        {
            "host": host,
            "user": user,
            "port": int(port),
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "ok": result["exit_code"] == 0,
        }
    )

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    if args.quiet:
        sys.stdout.write(result["stdout"])
        if result["stderr"]:
            sys.stderr.write(result["stderr"])
    else:
        print(f"=== kali@{host}:{port} ===")
        print(f"$ {command}")
        print(f"exit={result['exit_code']} duration={result['duration_sec']}s")
        if result["stdout"]:
            print("--- stdout ---")
            print(result["stdout"], end="" if result["stdout"].endswith("\n") else "\n")
        if result["stderr"]:
            print("--- stderr ---")
            print(result["stderr"], end="" if result["stderr"].endswith("\n") else "\n")

    return 0 if result["exit_code"] == 0 else result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
