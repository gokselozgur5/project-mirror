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


def run_policy_after_historical_deletion(
    tmp_path: Path,
    *,
    filename: str,
    content: str = "",
) -> subprocess.CompletedProcess[str]:
    repository = tmp_path / "repository"
    scripts = repository / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy(REPOSITORY_ROOT / "scripts" / "check-repository.sh", scripts)
    (repository / filename).write_text(content, encoding="utf-8")

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
    git(repository, "rm", "--quiet", filename)
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

    return subprocess.run(
        ["bash", "scripts/check-repository.sh"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )


def test_privacy_check_rejects_media_deleted_from_current_tree(tmp_path: Path) -> None:
    result = run_policy_after_historical_deletion(tmp_path, filename="private.mov")

    assert result.returncode == 1
    assert "detected in Git history" in result.stderr


def test_privacy_check_rejects_credential_deleted_from_current_tree(
    tmp_path: Path,
) -> None:
    fake_credential = "gh" + "p_" + "A" * 24
    result = run_policy_after_historical_deletion(
        tmp_path,
        filename="removed-secret.txt",
        content=fake_credential,
    )

    assert result.returncode == 1
    assert "probable credential detected in Git history" in result.stderr
