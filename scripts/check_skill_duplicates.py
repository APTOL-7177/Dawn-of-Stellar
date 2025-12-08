"""Check skill ID overlaps between YAML files and legacy job_skills modules.

Usage:
    python scripts/check_skill_duplicates.py
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS_YAML_DIR = ROOT / "data" / "skills"
JOB_SKILLS_DIR = ROOT / "src" / "character" / "skills" / "job_skills"


def collect_yaml_skill_ids() -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for path in SKILLS_YAML_DIR.glob("*.yaml"):
        try:
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            rel = path.relative_to(ROOT).as_posix()
            print(f"[WARN] YAML parse error: {rel}: {exc}")
            continue

        skill_id = data.get("id")
        if not skill_id:
            continue
        result.setdefault(skill_id, []).append(path.relative_to(ROOT).as_posix())
    return result


def collect_job_skill_ids() -> tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    id_map: Dict[str, Set[str]] = {}
    module_map: Dict[str, Set[str]] = {}

    class SkillVisitor(ast.NodeVisitor):
        def __init__(self, rel_path: str):
            self.rel_path = rel_path

        def visit_Call(self, node: ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in {"Skill", "TeamworkSkill"} and node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    skill_id = arg0.value
                    id_map.setdefault(skill_id, set()).add(self.rel_path)
                    module_map.setdefault(self.rel_path, set()).add(skill_id)
            self.generic_visit(node)

    for path in JOB_SKILLS_DIR.glob("*.py"):
        with path.open(encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(path))
        SkillVisitor(path.relative_to(ROOT).as_posix()).visit(tree)

    return id_map, module_map


def main() -> None:
    yaml_ids = collect_yaml_skill_ids()
    py_ids, module_map = collect_job_skill_ids()

    overlap = sorted(set(yaml_ids) & set(py_ids))
    only_yaml = sorted(set(yaml_ids) - set(py_ids))
    only_py = sorted(set(py_ids) - set(yaml_ids))

    print(f"YAML skill IDs: {len(yaml_ids)}")
    print(f"job_skills IDs: {len(py_ids)}")
    print(f"Overlap IDs: {len(overlap)}")
    print()

    print("-- Overlap (sample up to 20) --")
    for sid in overlap[:20]:
        yaml_path = yaml_ids[sid][0]
        py_paths = ", ".join(sorted(py_ids[sid]))
        print(f"{sid}: yaml={yaml_path} | py={py_paths}")
    print()

    print("-- YAML only (sample up to 20) --")
    for sid in only_yaml[:20]:
        yaml_path = yaml_ids[sid][0]
        print(f"{sid}: yaml={yaml_path}")
    print()

    print("-- job_skills only (sample up to 20) --")
    for sid in only_py[:20]:
        py_paths = ", ".join(sorted(py_ids[sid]))
        print(f"{sid}: py={py_paths}")

    print()
    print("-- Modules fully covered by YAML --")
    fully_covered = []
    partial = []
    for module_path, ids in sorted(module_map.items()):
        missing = [sid for sid in ids if sid not in yaml_ids]
        if not missing and ids:
            fully_covered.append((module_path, len(ids)))
        else:
            partial.append((module_path, len(ids), len(missing)))

    if fully_covered:
        for module_path, count in fully_covered:
            print(f"{module_path}: {count} skills (all in YAML)")
    else:
        print("(none)")

    print()
    print("-- Modules with YAML gaps (top 15) --")
    if partial:
        partial.sort(key=lambda x: (x[2], -x[1]))  # sort by missing count ascending
        for module_path, total_count, missing_count in partial[:15]:
            coverage = (1 - missing_count / total_count) * 100 if total_count else 0
            print(f"{module_path}: {total_count} skills, {missing_count} missing ({coverage:.1f}% covered)")
    else:
        print("(none)")

    print()
    print("-- Detailed missing skills (coverage >= 15%) --")
    detailed = [
        (module_path, module_map[module_path], [sid for sid in module_map[module_path] if sid not in yaml_ids])
        for module_path in module_map
    ]
    detailed = [item for item in detailed if item[1] and (1 - len(item[2]) / len(item[1])) >= 0.15]
    if detailed:
        detailed.sort(key=lambda x: (len(x[2]), x[0]))
        for module_path, ids, missing in detailed:
            coverage = (1 - len(missing) / len(ids)) * 100
            print(f"{module_path}: {coverage:.1f}% covered -> missing: {', '.join(sorted(missing))}")
    else:
        print("(none)")



if __name__ == "__main__":
    main()
