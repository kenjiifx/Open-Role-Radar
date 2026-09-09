"""Merge probed/new source boards into config/sources.yml."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [item for item in data if isinstance(item, dict)]


def key(entry: dict) -> tuple[str, str]:
    return (
        str(entry.get("adapter", "")).strip().lower(),
        str(entry.get("tenant", "")).strip().lower(),
    )


def main() -> None:
    main_path = ROOT / "config" / "sources.yml"
    main = load_list(main_path)
    extra = load_list(ROOT / ".local" / "probed-sources.yml") + load_list(
        ROOT / ".local" / "new-sources.yml"
    )

    seen = {key(entry) for entry in main if key(entry)[0] and key(entry)[1]}
    added: list[dict[str, str]] = []
    for entry in extra:
        k = key(entry)
        if not k[0] or not k[1] or k in seen:
            continue
        company = str(entry.get("company", "")).strip()
        domain = str(entry.get("domain", "")).strip().lower()
        if not company or not domain:
            continue
        seen.add(k)
        added.append(
            {
                "company": company,
                "domain": domain,
                "adapter": k[0],
                "tenant": k[1],
            }
        )

    if not added:
        print("added=0")
        return

    lines = ["", "# --- Auto-merged probed boards (expanded coverage) ---"]
    for entry in sorted(added, key=lambda item: item["company"].lower()):
        lines.append(
            "- { company: "
            + entry["company"]
            + ", domain: "
            + entry["domain"]
            + ", adapter: "
            + entry["adapter"]
            + ", tenant: "
            + entry["tenant"]
            + " }"
        )
    text = main_path.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(lines) + "\n"
    main_path.write_text(text, encoding="utf-8")
    print(f"added={len(added)} total_keys={len(seen)}")


if __name__ == "__main__":
    main()
