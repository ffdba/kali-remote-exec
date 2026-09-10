# 踩坑手册 — 经实战验证的失败模式与处置

按需阅读。每条都来自真实测试,不是理论风险。

## 1. zsh glob 字符

**症状**:命令在交互终端正常,经 SSH 执行报 `zsh:1: no matches found: xxx?yyy` 或 `parse error near ')'`。

**原因**:Kali 新版本默认 shell 是 zsh。`?` `(` `)` `[` `]` `*` 裸写在 URL/参数里会被 zsh 当 glob 展开失败的 pattern。

**处置**:所有含特殊字符的参数加引号;整条命令尽量用单引号包裹 URL。验证方式:`echo $0` 看远程默认 shell。

## 2. PowerShell → SSH 双层引号剥除

**症状**:经 `kali-exec.ps1 -RemoteCommand "curl -sk 'https://x' -A 'Mozilla/5.0'"` 执行,curl 收到的引号丢失,报 `parse error near ')'`。

**原因**:PowerShell 解析外层双引号后,内层单引号经参数传递再被 zsh 剥掉,引号层数对不上。

**处置**:复杂命令(多层引号、管道、循环)一律改走 Python 入口;更复杂的(脚本本身)用 base64 传输:

```bash
B64=$(base64 -w0 /tmp/script.py)
python kali_exec.py -- "echo $B64 | base64 -d > /tmp/script.py && python3 /tmp/script.py"
```

## 3. paramiko 通道超时导致结果丢失

**症状**:长时间命令后台跑了很久,SSH 调用返回 `paramiko.buffered_pipe.PipeTimeout` / `socket.timeout`,拿不到任何输出。

**原因**:`exec_command(timeout=N)` 是读超时;命令跑超 N 秒后通道读挂起。默认 `--timeout 120`。

**处置**:
- 短命令(<100s):`--timeout 300` 够用
- 长任务(全端口扫描、目录爆破、爬虫):nohup 后台 + 轮询(见 SKILL.md 规则 3),输出落远端文件
- 轮询间隔 1-2 分钟一次即可,不要高频轮询挤占通道

## 4. DNS 解析失败降级

**症状**:测试中途突然全部请求报 `Temporary failure in name resolution`(Kali 侧),此前一直正常。

**原因**:Kali 的 systemd-resolved 或上游 DNS 抖动;也有可能是高频扫描触发了网络环境限制。

**处置**:
- 临时绕过:URL 换 IP + 手动 Host 头(`httpx`/`curl -H 'Host: xxx'`)
- 已写好的脚本用域名时,快速改造:`BASE_IP` + `headers={"Host": 域名}`
- 长期:在 Kali `/etc/resolv.conf` 加可靠 DNS(如 223.5.5.5)或 `/etc/hosts` 固定目标

## 5. HTTP 代理环境(Windows 侧 Clash 等)

**症状**:本机浏览器/调试代理开着时,直连目标的行为与 Kali 侧不一致;或脚本引擎报 `proxy=[http://127.0.0.1:7897]` 类错误。

**原因**:Windows 上系统代理(Clash/v2rayN)会劫持部分程序的流量;不同工具对系统代理的遵从度不同,出口 IP 可能和预期不一样。

**处置**:
- 对照测试时明确三条路径:Kali 直连 / 本机直连(--noproxy)/ 本机走代理,逐条比对再下结论
- curl:`--noproxy '*'` 或 `-x http://127.0.0.1:7897` 显式控制
- 怀疑被目标封 IP 前,先用两个出口 IP 交叉验证

## 6. 大输出文件回传

**症状**:`cat` 大文件经 SSH stdout 回传,输出被截断或混入横幅。

**处置**:
- 超大输出(>1MB)优先 gzip + base64 分段回传,或在 Kali 起临时 http 服务拉取
- 回传内容统一剥离横幅:`sed -n '/^--- stdout ---$/,$p' | tail -n +2`
- 只需要文件统计信息时,远程先处理(head/grep/wc)再回传,不要全量拉

## 7. 命令留证

AGENTS.md 类工作流要求"命令+输出+时间"留证。两种方式:
- 脚本级:`--json-out /path/evidence.json` 每次执行落盘结构化结果(含时间戳、耗时、退出码)
- 案例级:重要命令的完整输出重定向到 case 目录的 evidence 文件

## 8. 远程 shell 是 zsh 时 for 循环的坑

**症状**:内联 for 循环带 URL 参数时 zsh 报 no matches found(即使加了引号,`$(...)` 里的值展开后仍可能触发)。

**处置**:循环类任务写成 Python 脚本 base64 上传执行,不要在命令行内联;既避开 glob,也方便复跑和留档。
