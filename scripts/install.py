#!/usr/bin/env python3
"""跨平台安装器 — 把 kali-remote-exec 装进当前机器支持的智能体 skill 目录。

用法:
  python install.py                # 检测并安装到所有支持的目录
  python install.py --target zcode # 只装到指定平台(zcode/claude/agents-all)
  python install.py --src <目录>   # 从指定位置安装本 skill(默认:本脚本上级目录)

支持目标:
  zcode       -> ~/.agents/skills/            (ZCode 自动发现)
  claude      -> ~/.claude/skills/            (Claude Code 自动发现)
  agents-all  -> 打印 AGENTS.md 接入片段(Codex/OpenCode 等无 skill 机制的)
"""

import argparse
import shutil
import sys
from pathlib import Path

HOME = Path.home()
HERE = Path(__file__).resolve().parent.parent
NAME = "kali-remote-exec"

TARGETS = {
    "zcode": HOME / ".agents" / "skills" / NAME,
    "claude": HOME / ".claude" / "skills" / NAME,
}

EXCLUDE = {"kali.ps1", "install.py", "__pycache__"}

AGENTS_SNIPPET = f"""
## Kali 远程执行工作流(kali-remote-exec)

当用户要求在 Kali/远程 Linux 上执行命令(扫描、工具调用、文件传输)时:
1. 先运行 `python {HERE / 'scripts' / 'doctor.py'}` 体检;退出码 1 时按其输出的编号修复步骤引导用户,READY 之前不执行实际任务。
2. 通过 `python {HERE / 'scripts' / 'kali_exec.py'} -- "<命令>"` 执行并回收输出。
3. 严格遵守 {HERE / 'SKILL.md'} 的工作流规则(zsh 转义、长任务 nohup 后台、base64 传文件、凭据只走环境变量)。
4. 踩坑排查读 {HERE / 'references' / 'pitfalls.md'}。
"""


def copy_skill(dst: Path):
    if dst.exists():
        ans = input(f"[?] 目标已存在: {dst}\n    覆盖? [y/N] ").strip().lower()
        if ans != "y":
            print("    跳过")
            return False
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    n = 0
    for root, dirs, files in os_walk(HERE):
        rel = Path(root).relative_to(HERE)
        for f in files:
            if f in EXCLUDE:
                continue
            src_f = Path(root) / f
            dst_f = dst / rel / f
            dst_f.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_f, dst_f)
            n += 1
    print(f"[OK] 已安装到 {dst} ({n} 个文件)")
    return True


def os_walk(base: Path):
    for root, dirs, files in __import__("os").walk(base):
        yield root, dirs, files


def main():
    global HERE
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=[*TARGETS, "agents-all"], default=None,
                    help="只安装到指定平台;缺省 = 全部 + 打印 AGENTS 片段")
    ap.add_argument("--src", default=str(HERE), help="skill 源目录(默认本脚本上级)")
    ap.add_argument("--yes", action="store_true", help="覆盖已存在目录不再询问")
    args = ap.parse_args()

    if args.src != str(HERE):
        HERE = Path(args.src).resolve()

    targets = list(TARGETS) if args.target is None else [args.target]
    for t in targets:
        if t == "agents-all":
            print("\n===== 复制以下片段到你的 AGENTS.md =====")
            print(AGENTS_SNIPPET)
            continue
        if args.yes and TARGETS[t].exists():
            shutil.rmtree(TARGETS[t])
        copy_skill(TARGETS[t])

    print("\n下一步:")
    print(f"  1. python {HERE / 'scripts' / 'doctor.py'}   # 体检 + 自动配置指引")
    print(f"  2. python {HERE / 'scripts' / 'kali_exec.py'} -- \"uname -a\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
