import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

REPOSITORY_ROOT = Path(__file__).parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^]]*]\(([^)]+)\)")


def tracked_markdown_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "*.md"],
        cwd=REPOSITORY_ROOT,
        text=True,
    )
    return [REPOSITORY_ROOT / line for line in output.splitlines()]


def test_relative_markdown_links_resolve_to_tracked_paths() -> None:
    broken: list[str] = []
    for document in tracked_markdown_files():
        text = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.split("#", maxsplit=1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (document.parent / unquote(target)).resolve()
            if not resolved.exists():
                broken.append(
                    f"{document.relative_to(REPOSITORY_ROOT)} -> {raw_target}"
                )

    assert not broken, "broken Markdown links:\n" + "\n".join(broken)
