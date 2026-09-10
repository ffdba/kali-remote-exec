# 通用智能体接入(Claude Code / Claude 桌面版)

适用:Claude Code(CLI)与支持 Skills 的 Claude 客户端。

## Claude Code

Claude Code 使用与 ZCode 兼容的 skill 目录格式(`SKILL.md` + YAML frontmatter `name`/`description`)。安装方式二选一:

- 用户级:`~/.claude/skills/kali-remote-exec/`
- 项目级:`<项目>/.claude/skills/kali-remote-exec/`

直接复制整个 skill 目录即可,无需修改。`description` 字段会让 Claude 在用户提到"在 Kali 上执行/扫描"类请求时自动加载 SKILL.md 并按其中工作流执行(首次调用先跑 `scripts/doctor.py` 的规则写在正文里,Claude 会遵守)。

## Claude 桌面版(MCP 方式)

没有 skill 目录机制的客户端,可以把执行器包一层 MCP server 暴露为工具。最小封装示例(`server.py`,依赖 `mcp` 包):

```python
import subprocess, sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kali-remote-exec")
KALI_EXEC = r"<skill路径>/scripts/kali_exec.py"

@mcp.tool()
def kali_run(command: str, timeout: int = 120) -> str:
    """在远程 Kali 上执行命令并返回输出(先跑 doctor.py 确认 READY)"""
    r = subprocess.run(
        [sys.executable, KALI_EXEC, "--timeout", str(timeout), "--", command],
        capture_output=True, text=True, timeout=timeout + 30,
    )
    return r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr else "")

if __name__ == "__main__":
    mcp.run()
```

客户端配置(如 Claude 桌面版 `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kali-remote-exec": {
      "command": "python",
      "args": ["<skill路径>/integrations/server.py"]
    }
  }
}
```

凭据仍通过环境变量提供(`KALI_HOST`/`KALI_USER`/`KALI_PASSWORD`),MCP 子进程会继承。

## 通用提示

- 无论哪种接入,首次使用先跑 `python scripts/doctor.py`,READY 后再执行任务。
- 工作流规则、踩坑手册在 SKILL.md 与 references/pitfalls.md,与平台无关,建议接入方原文引用。
