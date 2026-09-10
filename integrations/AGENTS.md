# 通用智能体接入(AGENTS.md 约定)

适用:Codex、OpenCode、Windsurf 等以 `AGENTS.md`(或等价全局指令文件)作为约定来源的智能体。

## 接入方法

把下面这段加入你的全局(`~/.codex/AGENTS.md`、`~/.opencode/AGENTS.md` 等)或项目级 `AGENTS.md`,并把路径改成 skill 实际解压位置:

```markdown
## Kali 远程执行工作流(kali-remote-exec)

当用户要求在 Kali/远程 Linux 上执行命令(扫描、工具调用、文件传输)时:
1. 先运行 `python <skill路径>/scripts/doctor.py` 体检;退出码 1 时按其输出的编号修复步骤引导用户,READY 之前不执行实际任务。
2. 通过 `python <skill路径>/scripts/kali_exec.py -- "<命令>"` 执行并回收输出。
3. 严格遵守 <skill路径>/SKILL.md 的工作流规则(zsh 转义、长任务 nohup 后台、base64 传文件、凭据只走环境变量)。
4. 踩坑排查读 <skill路径>/references/pitfalls.md。
```

## 说明

- 这类智能体没有 skill 自动触发机制,靠 AGENTS.md 指令里的触发描述让模型在合适时机主动使用。
- 触发词可按需追加,如:"在Kali上跑"、"经Kali执行"、"用Kali扫一下"、"在Kali上装XX工具"。
- SKILL.md 的 frontmatter(name/description)对这类智能体没有作用,但保留无害;起作用的是正文工作流。
