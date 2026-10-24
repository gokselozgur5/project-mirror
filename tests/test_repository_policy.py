import shutil
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )


def test_privacy_check_rejects_media_deleted_from_current_tree(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    scripts = repository / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy(REPOSITORY_ROOT / "scripts" / "check-repository.sh", scripts)
    private_media = repository / "private.mov"
    private_media.touch()

    git(repository, "init", "--quiet")
    git(repository, "add", ".")
    git(
        repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "add fixture",
    )
    git(repository, "rm", "--quiet", "private.mov")
    git(
        repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "remove fixture",
    )

    result = subprocess.run(
        ["bash", "scripts/check-repository.sh"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "detected in Git history" in result.stderr
