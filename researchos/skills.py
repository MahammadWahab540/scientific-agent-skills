from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SkillDescriptor:
    name: str
    description: str
    path: Path
    allowed_tools: str = ""


class SkillCatalog:
    def __init__(self, skills: dict[str, SkillDescriptor]) -> None:
        self._skills = dict(skills)

    @classmethod
    def discover(cls, root: Path | str = Path("skills")) -> "SkillCatalog":
        root = Path(root)
        skills: dict[str, SkillDescriptor] = {}
        if not root.exists():
            return cls(skills)
        for skill_file in sorted(root.glob("*/SKILL.md")):
            fields = _frontmatter_fields(skill_file)
            name = fields.get("name")
            description = fields.get("description", "")
            if name:
                skills[name] = SkillDescriptor(
                    name=name,
                    description=description,
                    path=skill_file.parent,
                    allowed_tools=fields.get("allowed-tools", ""),
                )
        return cls(skills)

    def get(self, name: str) -> SkillDescriptor:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise KeyError(f"unknown scientific skill: {name}") from exc

    def search(self, query: str, limit: int = 10) -> list[SkillDescriptor]:
        terms = [term.lower() for term in query.split() if term.strip()]
        scored: list[tuple[int, SkillDescriptor]] = []
        for skill in self._skills.values():
            haystack = f"{skill.name} {skill.description}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, skill))
        scored.sort(key=lambda item: (-item[0], item[1].name))
        return [skill for _, skill in scored[:limit]]

    def __len__(self) -> int:
        return len(self._skills)


def _frontmatter_fields(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields
