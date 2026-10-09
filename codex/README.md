# Codex 版（OpenAI Codex CLI）

Codex 有三种方式承载同一套工作流，内容都来自本仓库：

- **Codex skill(推荐)**：`~/.codex/skills/research-builder/` 与 `~/.codex/skills/paper-survey/`，由 `sync_codex_skills.sh` 从仓库生成，与 Claude 版逐文件一致，只有 SKILL.md 头部的 description 与适配说明不同。
- **自定义 prompt**：把 `research-builder.md`、`paper-survey.md` 放到 `~/.codex/prompts/`，在 Codex 里用 `/research-builder`、`/paper-survey` 显式调用。
- **AGENTS.md**：把硬纪律(无破折号分号、不造新词、用素材锁定词、LaTeX 与 HTML 优先)写进项目根的 `AGENTS.md`，Codex 每次都遵守。

## 学术插图技能

`paper-figure-pptx` 是独立的技能，与 Claude Code 用同一份 `SKILL.md`、脚本、SVG 图标和论文图参考，在 Codex 里用 `$paper-figure-pptx` 调用。安装脚本会建立 `~/.agents/skills/paper-figure-pptx` 符号链接，指向 `~/.codex/skills/paper-figure-pptx`，这是 [Codex 文档](https://learn.chatgpt.com/docs/build-skills) 规定的本地技能发现位置。

```bash
bash codex/sync_codex_skills.sh --pptx-only
```

这个命令先备份旧的 PPT 技能，再安装仓库里的版本，research-builder 与 paper-survey 不受影响。加 `--target-root /tmp/pptx-skill-test` 可以先装到独立目录里验证。版式原型见 [figure-archetypes](../knowledge/figure-archetypes.md)。

## 安装

**推荐，Codex skills。** Codex 现在会读 `~/.codex/skills/<名字>/SKILL.md`。在仓库里跑一行即可把三个 skill 同步过去，旧版本自动备份到 `~/.codex/skill_backups/`：

```bash
bash codex/sync_codex_skills.sh
```

脚本把仓库镜像到 `~/.codex/skills/research-builder/` 与 `~/.codex/skills/paper-survey/`，SKILL.md 换成 Codex 版(description 裁到 1024 字符以内，加适配说明，路径改成 `~/.codex/skills/`)，保留各自的 `agents/openai.yaml`。改了 skill 就重跑一次。

**备选，自定义 prompt。**

```bash
mkdir -p ~/.codex/prompts
cp research-builder.md paper-survey.md ~/.codex/prompts/
# 可选: 把硬纪律并入项目 AGENTS.md
cat AGENTS.snippet.md >> /path/to/your/project/AGENTS.md
```

## 用法

```
codex
> /research-builder        # 调研→搭系统→实验→回填论文 / 也能只画图、润色或投稿前去 AI 化核查
> /paper-survey            # LaTeX/HTML 优先调研 baseline 与相关工作
```

## 与 Claude 版的两点差异

1. 自定义 prompt 要用 `/名字` 调用，或把内容贴进对话。Codex skill 没有这个限制，可以显式调用，也会按描述自动选用。
2. Codex 没有子代理。工作流里并行派出的步骤改为按顺序执行，或开多个 codex 会话手动并行。其余内容来自同一份仓库源文件。

## 素材路径

Codex prompt 里引用的素材默认在 `~/.claude/skills/research-builder/materials/`(若你装了 Claude 版)。没装 Claude 版就把本仓库 clone 下来，把 prompt 里的素材路径改成你的 clone 路径。
