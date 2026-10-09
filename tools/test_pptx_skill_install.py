#!/usr/bin/env python3
"""Exercise PPT skill installers only in disposable target roots.

Run from the repository: python3 tools/test_pptx_skill_install.py
No HOME or CODEX_HOME environment variable is changed. A small synthetic
research-builder/paper-survey repository verifies their existing copy/adaptation
behavior, while the real paper-figure-pptx assets are installed and checked.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
PPT_NAME = "paper-figure-pptx"
IGNORED = {"__pycache__", ".DS_Store"}


def snapshot(root: Path) -> dict[str, str]:
    result = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        if any(part in IGNORED for part in path.parts) or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            result[str(path.relative_to(root))] = "symlink:" + os.readlink(path)
        elif path.is_file():
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class PptxSkillInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pptx-install-test-")
        self.root = Path(self.temp.name)
        self.repo = self.root / "source repo"
        self.target = self.root / "target root"
        self.repo.mkdir()
        self.assertTrue((REPO / PPT_NAME / "SKILL.md").is_file(), "Missing independent PPT skill")
        shutil.copy2(REPO / "install.sh", self.repo / "install.sh")
        (self.repo / "codex").mkdir()
        shutil.copy2(REPO / "codex/sync_codex_skills.sh", self.repo / "codex/sync_codex_skills.sh")
        shutil.copytree(REPO / PPT_NAME, self.repo / PPT_NAME,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        # Synthetic input keeps these tests from interpreting research writing instructions.
        write(self.repo / "SKILL.md", "---\nname: research-builder\ndescription: Existing description\n---\n# Research fixture\nExisting source: ~/.claude/skills/research-builder/\n")
        write(self.repo / "writing-playbook.md", "WRITING_RULE_SENTINEL\n")
        write(self.repo / "diagnostic-playbook.md", "EXPERIMENT_RULE_SENTINEL\n")
        write(self.repo / "materials/domain/fixture.txt", "domain\n")
        write(self.repo / "materials/general/fixture.txt", "general\n")
        write(self.repo / "paper-survey/SKILL.md", "---\nname: paper-survey\ndescription: Existing survey\n---\n# Survey fixture\nExisting source: ~/.claude/skills/paper-survey/\n")
        write(self.repo / "paper-survey/tools/fetch_arxiv.sh", "#!/usr/bin/env bash\nexit 0\n")
        write(self.repo / "materials/README.md", "MATERIALS_README_SENTINEL\n")
        self.source_snapshot = snapshot(self.repo)
        self.expected_ppt = snapshot(self.repo / PPT_NAME)
        self.protected = {}
        for platform in (".claude", ".codex", ".agents"):
            for name in ("research-writing/writing-core/SKILL.md", "research-writing/figures-python/plot.py", "unrelated/SKILL.md"):
                path = self.target / platform / "skills" / name
                content = f"THIRD_PARTY_SENTINEL {platform} {name}\n"
                write(path, content)
                self.protected[path] = path.read_bytes()

    def tearDown(self):
        self.temp.cleanup()

    def run_install(self, platform: str, pptx_only: bool = False):
        script = "install.sh" if platform == ".claude" else "codex/sync_codex_skills.sh"
        args = ["bash", str(self.repo / script), "--target-root", str(self.target)]
        if pptx_only:
            args.append("--pptx-only")
        completed = subprocess.run(args, cwd=self.root, text=True, capture_output=True, timeout=90)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return completed.stdout

    def assert_protected_unchanged(self):
        for path, payload in self.protected.items():
            self.assertEqual(path.read_bytes(), payload, str(path))
        self.assertEqual(snapshot(self.repo), self.source_snapshot, "Installer mutated repository sources")

    def assert_ppt_install(self, platform: str):
        installed = self.target / platform / "skills" / PPT_NAME
        self.assertFalse(installed.is_symlink())
        self.assertEqual(snapshot(installed), self.expected_ppt)
        starter = installed / "assets/icon-library/starter"
        manifest = json.loads((starter / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["count"], len(manifest["icons"]))
        for icon in manifest["icons"]:
            svg = starter / icon["svg"]
            self.assertEqual(hashlib.sha256(svg.read_bytes()).hexdigest(), icon["svg_sha256"], str(svg))
            if "png" in icon:
                self.assertTrue((starter / icon["png"]).is_file(), icon["png"])
        self.assertEqual(len(list((starter / "svg").glob("*.svg"))), manifest["count"])
        self.assertTrue((starter / "contact-sheet.png").is_file())
        self.assertFalse((installed.parent / "research-builder" / PPT_NAME).exists())
        # Check repository-relative resource links without following web URLs.
        for document in [installed / "SKILL.md", *sorted((installed / "references").glob("*.md"))]:
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                target = target.strip("<>").split("#", 1)[0]
                if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                    continue
                self.assertFalse(target.startswith("/"), f"Host-specific resource link in {document}: {target}")
                self.assertTrue((document.parent / target).exists(), f"Broken resource link in {document}: {target}")
        if platform == ".codex":
            alias = self.target / ".agents/skills" / PPT_NAME
            self.assertTrue(alias.is_symlink())
            self.assertEqual(alias.resolve(), installed.resolve())
        self.assert_protected_unchanged()

    def assert_material_links(self, rb):
        self.assertEqual((rb / "materials/README.md").read_text(encoding="utf-8"), "MATERIALS_README_SENTINEL\n")

    def test_full_install_and_repeat_preserve_existing_non_ppt_behavior(self):
        for platform in (".claude", ".codex"):
            with self.subTest(platform=platform):
                old = self.target / platform / "skills" / PPT_NAME / "old.txt"
                write(old, "OLD_PPT_SENTINEL\n")
                nested = self.target / platform / "skills/research-builder" / PPT_NAME / "nested.txt"
                write(nested, "OLD_NESTED_PPT_SENTINEL\n")
                self.run_install(platform)
                self.assert_ppt_install(platform)
                rb = self.target / platform / "skills/research-builder"
                self.assert_material_links(rb)
                self.assertEqual((rb / "writing-playbook.md").read_bytes(), (self.repo / "writing-playbook.md").read_bytes())
                self.assertEqual((rb / "diagnostic-playbook.md").read_bytes(), (self.repo / "diagnostic-playbook.md").read_bytes())
                for name in ("research-builder", "paper-survey"):
                    skill = self.target / platform / "skills" / name / "SKILL.md"
                    if platform == ".claude":
                        source = self.repo / ("SKILL.md" if name == "research-builder" else "paper-survey/SKILL.md")
                        self.assertEqual(skill.read_bytes(), source.read_bytes())
                    else:
                        text = skill.read_text(encoding="utf-8")
                        self.assertIn("Codex 版说明", text)
                        self.assertIn(f"~/.codex/skills/{name}/", text)
                        self.assertNotIn(".claude/skills/", text)
                backups = self.target / platform / "skill_backups"
                self.assertTrue(any(p.read_text() == "OLD_PPT_SENTINEL\n" for p in backups.rglob("old.txt")))
                self.assertTrue(any(p.read_text() == "OLD_NESTED_PPT_SENTINEL\n" for p in backups.rglob("nested.txt")))
                before = snapshot(self.target / platform / "skills")
                self.run_install(platform)
                self.assertEqual(snapshot(self.target / platform / "skills"), before)
                self.assert_ppt_install(platform)
        self.assertEqual((self.target / ".claude/skills" / PPT_NAME / "SKILL.md").read_bytes(),
                         (self.target / ".codex/skills" / PPT_NAME / "SKILL.md").read_bytes())

    def test_pptx_only_preserves_existing_research_and_survey_skills(self):
        for platform in (".claude", ".codex"):
            with self.subTest(platform=platform):
                skills = self.target / platform / "skills"
                for name in ("research-builder", "paper-survey"):
                    write(skills / name / "SKILL.md", f"LOCAL_METADATA_SENTINEL {name}\n")
                    write(skills / name / "agents/openai.yaml", f"LOCAL_AGENT_SENTINEL {name}\n")
                    write(skills / name / "writing.md", "LOCAL_WRITING_RULE\n")
                    write(skills / name / "experiments.py", "LOCAL_EXPERIMENT_RULE\n")
                preserved = {name: snapshot(skills / name) for name in ("research-builder", "paper-survey")}
                write(skills / "research-builder" / PPT_NAME / "old.txt", "OLD_NESTED\n")
                self.run_install(platform, pptx_only=True)
                self.assert_ppt_install(platform)
                for name, expected in preserved.items():
                    self.assertEqual(snapshot(skills / name), expected)
                before = snapshot(skills)
                self.run_install(platform, pptx_only=True)
                self.assertEqual(snapshot(skills), before)

    def test_codex_discovery_directory_is_backed_up_and_replaced_by_alias(self):
        old_alias = self.target / ".agents/skills" / PPT_NAME
        write(old_alias / "old.txt", "OLD_DISCOVERY_COPY\n")
        self.run_install(".codex", pptx_only=True)
        self.assert_ppt_install(".codex")
        backups = self.target / ".codex/skill_backups"
        self.assertTrue(any(p.read_text() == "OLD_DISCOVERY_COPY\n" for p in backups.rglob("old.txt")))

    def test_clone_directly_into_claude_skill_directory_keeps_source_and_installs_ppt(self):
        destination = self.target / ".claude/skills/research-builder"
        shutil.copytree(self.repo, destination)
        source_before = snapshot(destination)
        for args in ([], ["--pptx-only"], []):
            result = subprocess.run(["bash", str(destination / "install.sh"),
                                     "--target-root", str(self.target), *args],
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(snapshot(destination), source_before)
            self.assert_material_links(destination)
            self.assertEqual(snapshot(self.target / ".claude/skills" / PPT_NAME), self.expected_ppt)
            self.assertTrue((destination / PPT_NAME / "SKILL.md").is_file())
            self.assertTrue((self.target / ".claude/skills/paper-survey/SKILL.md").is_file())
        self.assert_protected_unchanged()

    def test_existing_ppt_symlink_does_not_modify_its_external_target(self):
        for platform in (".claude", ".codex"):
            external = self.root / (platform + " external-source")
            write(external / "old.txt", "EXTERNAL_SOURCE_UNCHANGED\n")
            installed = self.target / platform / "skills" / PPT_NAME
            installed.symlink_to(external, target_is_directory=True)
            self.run_install(platform, pptx_only=True)
            self.assert_ppt_install(platform)
            self.assertEqual((external / "old.txt").read_text(), "EXTERNAL_SOURCE_UNCHANGED\n")
            self.assertEqual(list(external.iterdir()), [external / "old.txt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
