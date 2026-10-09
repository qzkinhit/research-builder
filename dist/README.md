# dist · claude.ai 网页版上传包

`research-builder-web.zip` 是给 claude.ai 网页版上传的 skill 包。本地 Claude Code 与 Codex 直接用仓库本体，不需要它。

打包脚本自动满足网页版的四条上传规则，即整包只有一个 `SKILL.md`(嵌套的调研 skill 改名为 `paper-survey/paper-survey.md`)、路径全是 ASCII、description 不超过 1024 个字符、体积小于 30 MB。包里有全部手册、knowledge、模板、绘图模块与检查脚本。独立的 `paper-figure-pptx` 技能有自己的 `SKILL.md`，不放进这个包，你自己的 `materials/` 素材也不打包。

## 上传

claude.ai 的 Settings 里打开 Skills，上传 `research-builder-web.zip` 并启用。使用前需要打开代码执行。

## 重新打包

改了 skill 之后运行下面这行，脚本会重新生成压缩包并打印四项检查的结果。

```bash
bash dist/build_web_zip.sh
```
