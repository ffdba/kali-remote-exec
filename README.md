# kali-remote-exec

从 Windows(或任意有 Python 的机器)通过 SSH 在远程 Kali Linux 上执行命令并回收输出的**通用智能体 skill**。编排机(Windows/Linux/macOS)负责工作流、证据管理和报告;所有扫描/攻击工具(nmap、hydra、sqlmap、nuclei 等)都在 Kali 侧执行,不在本机安装任何扫描器。

**跨智能体通用**:同一个包支持 ZCode、Claude Code、Codex/OpenCode 等 AGENTS.md 系智能体,也可经 MCP 暴露给任意客户端——见下方「各平台接入」。

## 这是什么

一个自包含的 skill 包,核心是 paramiko SSH 执行器 + 一次运行的体检向导:

```
kali-remote-exec/
├── SKILL.md                    # 模型工作流(平台无关,含强制设置向导)
├── README.md                   # 本文件:人类安装使用说明
├── config/
│   └── kali.example.ps1        # 配置模板(复制为 kali.ps1 后填写;不强制)
├── scripts/
│   ├── doctor.py               # ★ 首次使用体检:自动诊断缺什么并给出修复命令
│   ├── kali_exec.py            # 核心执行器(Python/paramiko,平台无关)
│   ├── kali-exec.ps1           # PowerShell 包装入口(可选)
│   └── install.py              # 跨平台一键安装(ZCode/Claude Code/AGENTS片段)
├── integrations/
│   ├── AGENTS.md               # Codex/OpenCode 等 AGENTS.md 系接入片段
│   └── CLAUDE.md               # Claude Code 目录接入 + MCP server 封装示例
└── references/
    ├── setup.md                # 分步设置指引(FAQ + 排查顺序)
    └── pitfalls.md             # 实战踩坑手册(模型按需读取)
```

**第一次用?直接跳到下面「三分钟上手」。**

## 环境要求

- 本机:Python 3.8+ 和 `paramiko`(`pip install paramiko`),Windows 直接可用
- 远端:一台可 SSH 的 Kali Linux(其他 Linux 发行版同样可用),账号具备 sudo 更佳
- 网络:本机能 TCP 到达 Kali 的 22 端口

## 三分钟上手

### 第 1 步:安装

把 `kali-remote-exec/` 整个目录解压/复制到 ZCode 的 skill 发现路径(任选其一):

- 用户级(推荐,所有项目可用):`C:\Users\<你>\.agents\skills\kali-remote-exec\`(Linux/macOS 为 `~/.agents/skills/...`)
- 项目级:`<项目根>\.agents\skills\kali-remote-exec\`

无需注册,重启会话后 ZCode 自动发现。

### 第 2 步:装依赖

```bash
pip install paramiko
```

### 第 3 步:体检(自动引导配置)

```bash
python scripts/doctor.py
```

doctor 会依次检查 Python 版本 → paramiko → 配置 → 网络可达 → SSH 认证实测,并在缺什么时**打印可直接复制执行的修复命令**。跟着输出走,直到结论为 `READY`。

### 第 4 步:第一条命令

```bash
python scripts/kali_exec.py -- "uname -a && nmap --version | head -1"
```

看到 Kali 的内核信息即全部就绪。之后可以在 ZCode 里直接说"在 Kali 上跑 nmap ..."触发 skill。

## 连接信息怎么配(为什么每个人都能用)

**skill 本体不含任何 IP/凭据**。连接信息在运行时按以下优先级解析,三选一:

| 优先级 | 方式 | 适合 |
|---|---|---|
| 1 | 命令行参数 `--host <IP> --user <用户>` | 一次性/临时切换 |
| 2 | 环境变量 `KALI_HOST` / `KALI_USER` / `KALI_PORT` / `KALI_KEY` / `KALI_PASSWORD` | 日常使用(推荐) |
| 3 | 配置文件 `config/kali.ps1`(从 `kali.example.ps1` 复制) | 固定环境 |

所以分发时大家拿到的包完全相同,各自的 IP/凭据只存在于自己的环境变量或本机配置文件里——`config/kali.ps1` 类似 `.env`,不会也不应进入分发包。

环境变量示例:

```bash
# Git Bash / Linux / macOS
export KALI_HOST='192.168.x.x'
export KALI_USER='kali'
export KALI_PASSWORD='<你的SSH密码>'    # 不落盘
# 或免密:export KALI_KEY='/path/to/id_rsa'
```

```powershell
# PowerShell
$env:KALI_HOST='192.168.x.x'; $env:KALI_USER='kali'; $env:KALI_PASSWORD='<密码>'
```

更细的分步说明与 FAQ 见 [references/setup.md](references/setup.md)。

## 日常使用

优先用 Python 入口(引号转义最可靠):

```bash
python scripts/kali_exec.py --timeout 300 -- "nmap -Pn -sV --top-ports 100 --open <target> | tail -20"
```

PowerShell 入口:

```powershell
.\scripts\kali-exec.ps1 -RemoteCommand "nmap --version"
```

常用参数:

| 参数 | 用途 |
|---|---|
| `--timeout 600` | 单命令超时秒数,默认 120。长命令必须加 |
| `--json-out <path>` | 结果落盘 JSON(留证/脚本间传递) |
| `--quiet` | 只输出 stdout/stderr,供管道使用 |
| `--config <path>` | 指定配置文件 |

超过 100 秒的任务(全端口扫描、目录爆破、爬虫)用 nohup 后台模式,见 SKILL.md「强制工作流规则」。

## 在智能体里触发

skill 按 description 自动触发,以下说法都会命中:

- "在 Kali 上跑 / 经 Kali 执行 / 用 Kali 扫一下 <命令>"
- "检查 Kali 上有没有 hydra"
- "把扫描放到 Kali 执行"
- 首次触发时会自动先跑 `scripts/doctor.py` 做体检

也可以显式调用:`/kali-remote-exec <任务描述>`。

## 各平台接入

核心是三个普通文件(`kali_exec.py` / `doctor.py` / Markdown 文档),**任何能执行 shell 命令的智能体都能用**;差别只在"自动发现与触发"这一层:

| 平台 | 接入方式 | 自动触发 |
|---|---|---|
| **ZCode** | 复制到 `~/.agents/skills/kali-remote-exec/`(或用 `install.py`) | ✅ 按 description 自动触发 |
| **Claude Code** | 复制到 `~/.claude/skills/kali-remote-exec/`(SKILL.md 格式兼容) | ✅ 自动触发 |
| **Codex / OpenCode 等 AGENTS.md 系** | 把 `integrations/AGENTS.md` 的片段贴进你的全局/项目 AGENTS.md | 按片段中的触发词使用 |
| **Cursor 等规则制客户端** | 把 SKILL.md 正文要点贴进其规则文件(可参考 integrations/AGENTS.md 的压缩写法) | 按规则触发 |
| **MCP 客户端(Claude 桌面版等)** | 用 `integrations/CLAUDE.md` 里的 30 行 server.py 包装 `kali_exec.py` 为 MCP 工具 | 以工具调用形式 |
| **无智能体(人工)** | 直接命令行使用,README 即说明书 | — |

一键安装(ZCode + Claude Code 一起装,或 `--target` 单选):

```bash
python scripts/install.py            # 装到所有支持的目录
python scripts/install.py --target claude
python scripts/install.py --target agents-all   # 打印 AGENTS.md 接入片段
```

安装器不会覆盖或读取任何已有配置;个人配置文件(`config/kali.ps1`)与凭据始终留在本机。

## 适用场景与限制

适用:
- 渗透测试/安全评估中把攻击工具集中在 Kali 执行、Windows 只做编排的双机工作流
- 目标环境只允许从固定出口 IP(如实验室内网 Kali)发起扫描
- 需要在证据链中保留"命令+输出+耗时"的测试记录

限制:
- 不提供 SFTP 文件传输封装,传文件走 base64 命令行通道(见 SKILL.md)
- 每条命令是独立 SSH 会话,无交互式程序(vim/htop)支持;需要交互的程序用 `nohup` 或改用你自己的终端
- 输出横幅(`=== kali@... ===` 等)是脚本格式的一部分,解析时需按约定剥离(或 `--quiet`)

## 故障排查

固定顺序:

1. `python scripts/doctor.py` —— 按 FAIL 项的提示处理
2. 手工 SSH 验证(`ssh <user>@<ip>`)排除 skill 因素
3. 查 [references/pitfalls.md](references/pitfalls.md) 匹配症状(转义/超时/代理/DNS)
4. 仍无法解决:带着 doctor 完整输出提问

## 安全与合规

- **只在授权目标上使用**。把目标换成你自己的资产或获得书面授权的测试范围。
- 密码只放环境变量,不要写进 config、命令历史或聊天记录;`config/kali.ps1` 若在 git 仓库内请加入 `.gitignore`。
- 对生产系统操作前确认限速与窗口期;扫描产生的请求是真实的。
- 本 skill 只封装 SSH 执行,不包含任何攻击工具本身;工具的合法性与使用责任在使用者。

## 分发

直接分发 zip 包即可(接收方从「三分钟上手」开始)。打包时确保 `config/kali.ps1`(个人配置)不在包内,只保留 `kali.example.ps1` 模板。修改脚本时保持 `kali_exec.py` 与 `kali-exec.ps1` 的参数兼容。
