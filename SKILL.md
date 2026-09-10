---
name: kali-remote-exec
description: Run commands and security tools on a remote Kali Linux box over SSH from a Windows machine (or any host with Python). Use whenever the user wants to execute nmap/hydra/sqlmap/nuclei or any Linux tooling on a remote Kali host, run pentest scans via a "Kali bridge/toolbox", check Kali tool availability, transfer files to Kali, or orchestrate Windows-Kali dual-machine workflows — even if they just say "在Kali上跑", "经Kali执行", or "用Kali扫一下".
---

# Kali Remote Exec — Windows → Kali SSH 桥接

通过 paramiko SSH 在远程 Kali 主机上执行命令并回收输出。Windows 只做编排,所有扫描/攻击工具都在 Kali 侧执行。

## 首次调用:强制设置向导

**本 skill 在当前会话第一次被调用时,必须先跑体检脚本**(无论用户请求什么任务):

```bash
python "<skill>/scripts/doctor.py"
```

按退出码与输出分流:

- **退出码 0(READY)**:所有检查通过,直接进入下方"基本调用"执行用户任务。
- **退出码 1(NOT READY)**:输出末尾有编号的修复步骤,每步都带可直接复制执行的命令。此时:
  1. 把修复步骤原样呈现给用户,并说明缺的是什么(Python/paramiko/配置/凭据/网络)
  2. 用户回复其 Kali 的 IP/用户名/认证方式后,**代为执行**对应配置命令(密码只设进 `KALI_PASSWORD` 环境变量,严禁写入任何文件或回显)
  3. 重新运行 doctor,直到退出码 0;**READY 之前不得执行用户的实际任务**

doctor 检查项依次为:Python 版本 → paramiko → 配置解析(环境变量 > 配置文件)→ TCP 可达 → SSH 认证实测。哪一项 FAIL 就修哪一项,已通过项不会重复打扰。

配置解析优先级:**命令行参数 > 环境变量(KALI_HOST/KALI_USER/KALI_PORT/KALI_KEY/KALI_PASSWORD)> 配置文件**。每个人环境不同,以下三种方式任选其一,skill 完全通用:

1. **环境变量(推荐,零文件改动,可随时切机器)**:

   ```bash
   export KALI_HOST='192.168.x.x'   # 换成使用者自己的 Kali IP
   export KALI_USER='kali'
   export KALI_PASSWORD='<密码>'    # 密码不落盘
   python "<skill>/scripts/kali_exec.py" -- "nmap --version"
   ```

2. **配置文件(固定环境)**:从 `config/kali.example.ps1` 复制为 `config/kali.ps1` 并填写。

3. **纯命令行(一次性使用)**:

   ```bash
   python "<skill>/scripts/kali_exec.py" --host 192.168.x.x --user kali -- "uname -a"
   ```

**引导职责**:用户首次使用时,若环境变量和配置文件都没有,主动询问用户其 Kali 的 IP/用户名/认证方式,然后按上面任一方式帮其完成配置;**不要**猜测或假设 IP/凭据。更细的分步说明见 `references/setup.md`(给人看,doctor 输出已覆盖模型所需)。

## 基本调用

优先用 Python 入口(引号转义比 PowerShell 双层传递可靠):

```bash
python "<skill>/scripts/kali_exec.py" -- "nmap -Pn -sV --top-ports 100 --open <target> | tail -20"
```

PowerShell 入口(给习惯 PS 的用户):

```powershell
$env:KALI_PASSWORD='<密码>'
powershell -ExecutionPolicy Bypass -File "<skill>\scripts\kali-exec.ps1" -RemoteCommand "nmap --version"
```

常用参数:

| 参数 | 用途 |
|---|---|
| `--config <path>` | 指定配置文件(默认 `<skill>/config/kali.ps1`) |
| `--timeout 600` | 单命令超时秒数,默认 120。长命令必须加 |
| `--json-out <path>` | 结果落盘 JSON(留证/脚本间传递) |
| `--quiet` | 只输出 stdout/stderr,供管道使用 |
| `--host/--user/--port` | 临时覆盖配置 |

## 强制工作流规则

1. **引用本 skill 的脚本一律用绝对路径**(skill 安装路径因人而异,先确认实际安装位置)。
2. **远程命令默认在 zsh 执行**(Kali 默认 shell 可能是 zsh,不是 bash):`?` `(` `)` `[` `]` 是 glob 字符,裸写会被 zsh 拒绝(`no matches found`)。含这些字符的参数必须加引号。详细规则见 references/pitfalls.md。
3. **长任务(>100s)不要阻塞 SSH 通道**——paramiko 超时会让结果丢失。用 nohup 后台 + 轮询模式:

```bash
# 启动(立即返回)
python "<skill>/scripts/kali_exec.py" -- "nohup nmap -Pn -sS -p- --open --min-rate 1500 <target> -oN /tmp/scan.txt > /dev/null 2>&1 & echo BG_STARTED"
# 轮询(每隔1-2分钟)
python "<skill>/scripts/kali_exec.py" -- "cat /tmp/scan.txt 2>/dev/null || echo RUNNING"
```

4. **传文件给 Kali**:脚本内容用 base64 编码后经命令行传输(SSH 桥不提供 SFTP 封装):

```bash
B64=$(base64 -w0 /tmp/script.py)
python "<skill>/scripts/kali_exec.py" -- "echo $B64 | base64 -d > /tmp/script.py && python3 /tmp/script.py"
```

反向取文件:远程 `cat` 输出经本地重定向落盘,注意剥掉输出横幅(`=== kali@... ===` 到 `--- stdout ---` 之间的行)。

5. **凭据与授权**:密码只走 `KALI_PASSWORD` 环境变量,不写进任何文件;`--password` 参数会留在进程列表,避免使用。使用前确认目标已获授权。

## 排障速查

| 症状 | 原因 | 处置 |
|---|---|---|
| `CONNECT_FAIL: ...` | 主机不可达/凭据错/端口错 | 先 ping、再核对 config |
| `Missing auth` | 没设 KALI_PASSWORD | `$env:KALI_PASSWORD='<密码>'` 或 `export KALI_PASSWORD=...` |
| channel timeout / PipeTimeout | 命令超过 `--timeout` | 加大 `--timeout` 或改 nohup 后台模式 |
| `zsh: no matches found` | 裸写 glob 字符 | 参数加引号 |
| 引号丢失/parse error near ')' | PowerShell→ssh 双层转义剥掉了内层引号 | 改用 Python 入口 + base64 传脚本 |

更完整的踩坑案例(含 HTTP 代理环境、DNS 故障降级、全端口扫描节奏)按需 Read references/pitfalls.md。

## 输出约定

- 非安静模式输出格式:`=== kali@host:port ===` → `$ 命令` → `exit=N duration=Ns` → `--- stdout ---` → `--- stderr ---`。解析时以此为准。
- 每次执行都会带来真实的远程副作用(扫描、写文件)。对生产/授权目标操作前,先和用户确认范围与限速。
