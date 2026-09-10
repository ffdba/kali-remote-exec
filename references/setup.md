# 设置指引(分步,给第一次使用的人)

本指南覆盖从零到第一次成功执行远程命令的全过程。每一步都有"怎么判断我做对了"。

> 模型/agent 使用者:skill 内置的 `scripts/doctor.py` 会自动完成本指南的全部检查并给出精确修复命令,通常不需要人工逐条执行;本文件用于人工排查或理解每一步在做什么。

---

## 第 0 步:确认你有什么

开始前确认两件事:

| 需要什么 | 怎么确认 | 没有怎么办 |
|---|---|---|
| 一台能 SSH 的 Kali Linux | 虚拟机开机、`service ssh status` 显示 running | VMWare/VirtualBox 装 Kali 镜像后执行 `sudo systemctl enable --now ssh`;记下它的 IP(`ip a` 看 eth0) |
| 本机 Python 3.8+ | `python --version` | https://www.python.org/downloads/ 安装,勾选 "Add to PATH" |

Windows 自带 OpenSSH 客户端也可以先用手工方式验证连通性:`ssh kali@<Kali的IP>`(输密码能进去说明网络与凭据都正常,退出即可)。

## 第 1 步:安装 skill

把 `kali-remote-exec/` 整个目录放到:

- Windows 用户级:`C:\Users\<你>\.agents\skills\kali-remote-exec\`
- Linux/macOS 用户级:`~/.agents/skills/kali-remote-exec/`
- 或项目级:`<项目>\.agents\skills\kali-remote-exec\`

✅ 判断:目录下能看到 `SKILL.md`、`README.md`、`scripts/`、`config/`。

## 第 2 步:安装 Python 依赖

```bash
pip install paramiko
```

国内网络慢可换源:

```bash
pip install paramiko -i https://pypi.tuna.tsinghua.edu.cn/simple
```

✅ 判断:`python -c "import paramiko; print(paramiko.__version__)"` 打印版本号。

## 第 3 步:提供 Kali 连接信息(三选一)

优先级:**命令行参数 > 环境变量 > 配置文件**。

### 方式 A:环境变量(推荐)

PowerShell(当前窗口有效,建议加进 `$PROFILE` 持久化):

```powershell
$env:KALI_HOST = '192.168.x.x'      # 你的 Kali IP
$env:KALI_USER = 'kali'
$env:KALI_PASSWORD = '<你的SSH密码>'
```

Git Bash / Linux / macOS:

```bash
export KALI_HOST='192.168.x.x'
export KALI_USER='kali'
export KALI_PASSWORD='<你的SSH密码>'
```

✅ 判断:`echo $env:KALI_HOST`(PS)或 `echo $KALI_HOST`(bash)能打印出 IP。

### 方式 B:配置文件(固定环境)

```bash
cp config/kali.example.ps1 config/kali.ps1
```

编辑 `config/kali.ps1`:

```powershell
$KaliHost = '192.168.x.x'   # 你的 Kali IP
$KaliUser = 'kali'
$KaliPort = 22
$KaliKey  = ''               # 可选:私钥绝对路径
```

✅ 判断:`python scripts/kali_exec.py -- "echo OK"` 能返回 `--- stdout --- OK`(密码仍走 `KALI_PASSWORD`)。

### 方式 C:私钥认证(免密码)

```bash
ssh-keygen -t ed25519                    # 若还没有密钥
ssh-copy-id kali@<Kali的IP>              # 把公钥装到 Kali(或手动追加到 ~/.ssh/authorized_keys)
```

然后 `config/kali.ps1` 的 `KaliKey` 填私钥路径,或设 `KALI_KEY` 环境变量。

✅ 判断:`KALI_PASSWORD` 未设置的情况下执行命令仍成功。

## 第 4 步:体检 + 冒烟

```bash
python scripts/doctor.py     # 期望:结论 READY,退出码 0
python scripts/kali_exec.py -- "uname -a && which nmap hydra sqlmap | head -3"
```

✅ 判断:`doctor.py` 打印 5 个 `[PASS]` 且结论 READY;第二条命令返回 Kali 的内核版本和工具路径。

## 常见问题(FAQ)

**Q1:每个人的 Kali IP 都不一样,skill 怎么通用?**
skill 本体不含任何地址。IP 通过环境变量/配置文件/命令行参数在运行时注入,三者任选。分发时大家拿到的包完全相同,差异只在各自的环境变量或 `config/kali.ps1`(该文件不进 zip,类似 `.env`)。

**Q2:我有不止一台 Kali,怎么切换?**
环境变量方式:改 `KALI_HOST` 后立即生效。或在命令行直接 `--host <IP>` 覆盖,互不影响。

**Q3:配置文件会不会被 git 提交泄露?**
`config/kali.ps1` 与 `.env` 同理,属于本机私有文件。若 skill 目录在 git 仓库内,把 `config/kali.ps1` 加入 `.gitignore`(分发包里只有 example 模板)。

**Q4:公司网络有代理,paramiko 装不上?**
`pip install paramiko -i https://pypi.tuna.tsinghua.edu.cn/simple --proxy http://代理:端口`。SSH 本身不走 HTTP 代理;若 Kali 在代理后的隔离网络里,需要能路由到它的网络路径(VPN/跳板)。

**Q5:doctor 显示 TCP 可达但 SSH 认证被拒绝?**
依次检查:用户名拼写;密码是否最新(Kali 重装过?);Kali 侧 `sudo systemctl status ssh`;`/etc/ssh/sshd_config` 中 `PasswordAuthentication` 与 `PermitRootLogin` 是否放开。

**Q6:命令能跑,但输出里有 `=== kali@... ===` 之类的横幅?**
那是执行器的标准输出格式(命令回显 + 退出码 + stdout/stderr 分段),不是异常。写脚本解析时取 `--- stdout ---` 之后的内容,或加 `--quiet`。

## 出问题时的固定排查顺序

1. `python scripts/doctor.py` —— 按 FAIL 项处理
2. 手工 SSH 验证:`ssh <user>@<ip>`(排除 skill 本身因素)
3. 查 `references/pitfalls.md` 里与症状匹配的条目(转义/超时/代理/DNS)
4. 仍无法解决:带着 doctor 完整输出提问
