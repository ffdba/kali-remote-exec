#!/usr/bin/env python3
"""First-run doctor for kali-remote-exec skill.

Checks, in order:
  1. Python version
  2. paramiko installed
  3. Config resolution (env vars > config file)
  4. TCP reachability of the Kali host
  5. SSH authentication

Exit code 0 = READY (SSH auth passed), 1 = not ready (action list printed).
The model should run this on first invocation and walk the user through
the printed action items until it exits 0.
"""

import os
import re
import socket
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SKILL_DIR / "config" / "kali.ps1"

PS1_ASSIGN = re.compile(
    r"^\s*\$(?P<key>KaliHost|KaliUser|KaliPort|KaliKey)\s*=\s*'(?P<val>[^']*)'\s*$"
)

ACTIONS = []


def action(text):
    ACTIONS.append(text)


def load_ps1_config(path):
    data = {"KaliHost": None, "KaliUser": None, "KaliPort": 22, "KaliKey": ""}
    if not path.is_file():
        return None, data
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        m = PS1_ASSIGN.match(line)
        if m:
            key = m.group("key")
            val = m.group("val")
            data[key] = int(val) if key == "KaliPort" and val else val
    return text, data


def main():
    print("=" * 62)
    print("kali-remote-exec 体检 (doctor)")
    print("=" * 62)
    ok = True

    # 1. Python
    v = sys.version_info
    if v >= (3, 8):
        print(f"[PASS] Python {v.major}.{v.minor}.{v.micro}")
    else:
        print(f"[FAIL] Python {v.major}.{v.minor} 过旧,需要 3.8+")
        action("安装 Python 3.8+:https://www.python.org/downloads/ 或 winget install Python.Python.3.12")
        ok = False

    # 2. paramiko
    try:
        import paramiko  # noqa: F401
        print("[PASS] paramiko 已安装")
    except ImportError:
        print("[FAIL] paramiko 未安装")
        action("执行: pip install paramiko   (代理环境可加 -i https://pypi.tuna.tsinghua.edu.cn/simple)")
        ok = False

    # 3. Config resolution
    cfg_path = Path(os.environ.get("KALI_CONFIG", DEFAULT_CONFIG))
    raw, cfg = load_ps1_config(cfg_path)
    if cfg_path.is_file():
        print(f"[PASS] 配置文件存在: {cfg_path}")
        if raw is not None and not any(PS1_ASSIGN.match(line) for line in raw.splitlines()):
            print("[WARN] 配置文件存在但没解析出任何 $KaliHost/$KaliUser 赋值行,视为空配置")
    else:
        print(f"[INFO] 配置文件不存在(可用环境变量代替): {cfg_path}")

    host = os.environ.get("KALI_HOST") or cfg.get("KaliHost")
    user = os.environ.get("KALI_USER") or cfg.get("KaliUser")
    port = os.environ.get("KALI_PORT") or cfg.get("KaliPort") or 22
    key = os.environ.get("KALI_KEY") or (cfg.get("KaliKey") or None)
    password = os.environ.get("KALI_PASSWORD")
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 22

    src = []
    if os.environ.get("KALI_HOST") or os.environ.get("KALI_USER"):
        src.append("环境变量")
    if cfg_path.is_file() and (cfg.get("KaliHost") or cfg.get("KaliUser")):
        src.append("配置文件")
    if host and user:
        print(f"[PASS] 目标已配置(来源: {'+'.join(src) or 'CLI'}): {user}@{host}:{port}"
              + (f"  私钥={key}" if key else "")
              + f"  密码={'已设置' if password else '未设置'}")
    else:
        print("[FAIL] 未找到 Kali 主机/用户配置")
        print(f"       当前值: KALI_HOST={os.environ.get('KALI_HOST')!r} "
              f"KALI_USER={os.environ.get('KALI_USER')!r} "
              f"config={cfg_path}")
        action("方式A(推荐): 设置环境变量后重新体检\n"
               "  PowerShell:  $env:KALI_HOST='192.168.x.x'; $env:KALI_USER='kali'; $env:KALI_PASSWORD='<密码>'\n"
               "  Git Bash:    export KALI_HOST=192.168.x.x KALI_USER=kali KALI_PASSWORD='<密码>'")
        action("方式B: 复制模板并填写(密码仍走环境变量)\n"
               f"  cp \"{SKILL_DIR / 'config' / 'kali.example.ps1'}\" \"{cfg_path}\"  然后编辑")
        ok = False

    # 4. TCP reachability
    if host:
        try:
            with socket.create_connection((host, port), timeout=5):
                print(f"[PASS] TCP 可达: {host}:{port}")
            net_ok = True
        except Exception as exc:
            print(f"[FAIL] TCP 不可达: {host}:{port} ({type(exc).__name__}: {exc})")
            action("检查: 1) Kali 虚拟机是否开机且 SSH 服务运行(service ssh status)\n"
                   f"     2) 本机能否 ping 通 {host}\n"
                   "     3) 是否有防火墙/VPN 隔离")
            ok = False
            net_ok = False
    else:
        net_ok = False

    # 5. SSH auth
    if net_ok and host and user and (password or key):
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            kwargs = {
                "hostname": host, "port": port, "username": user,
                "timeout": 8, "allow_agent": False, "look_for_keys": False,
                "banner_timeout": 15, "auth_timeout": 15,
            }
            if key:
                kwargs["key_filename"] = key
                kwargs["look_for_keys"] = True
            if password:
                kwargs["password"] = password
            client.connect(**kwargs)
            _stdin, stdout, _stderr = client.exec_command("echo SSH_AUTH_OK", timeout=8)
            out = stdout.read().decode().strip()
            client.close()
            if "SSH_AUTH_OK" in out:
                print("[PASS] SSH 认证并执行成功")
            else:
                print("[FAIL] SSH 已连通但执行异常")
                ok = False
        except paramiko.AuthenticationException:
            print("[FAIL] SSH 认证被拒绝(用户名或密码/私钥错误)")
            action(f"核对 {user}@{host}:{port} 的密码;Kali 侧检查 /etc/ssh/sshd_config 是否允许密码登录")
            ok = False
        except Exception as exc:
            print(f"[FAIL] SSH 连接异常: {type(exc).__name__}: {exc}")
            action("查看 references/pitfalls.md 排障;确认 22 端口确实是 SSH")
            ok = False
    elif net_ok and not (password or key):
        print("[FAIL] 主机可达但没有提供凭据")
        action("设置 $env:KALI_PASSWORD='<密码>'(或 KALI_KEY 私钥路径)后重新体检")
        ok = False

    print("-" * 62)
    if ok:
        print("结论: READY — 所有检查通过,可以直接使用 kali_exec.py 执行远程命令。")
        print(f"快速验证: python \"{SKILL_DIR / 'scripts' / 'kali_exec.py'}\" -- \"uname -a\"")
        return 0

    print(f"结论: NOT READY — 共 {len(ACTIONS)} 项需要处理:")
    for i, a in enumerate(ACTIONS, 1):
        print(f"\n[{i}] {a}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
