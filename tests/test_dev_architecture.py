from pathlib import Path

from app.devtools import redact_connection_url, required_paths_exist


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_default_compose_is_infra_only() -> None:
    text = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "\n  db:\n" in text
    assert "\n  redis:\n" in text
    assert "\n  minio:\n" in text
    assert "\n  api:\n" not in text
    assert "\n  worker:\n" not in text
    assert "\n  beat:\n" not in text


def test_optional_app_compose_contains_containerized_services() -> None:
    text = (REPO_ROOT / "docker-compose.app.yml").read_text()
    assert "\n  api:\n" in text
    assert "\n  worker:\n" in text
    assert "\n  beat:\n" in text
    assert "@db:5432/arterial" in text
    assert "redis://redis:6379/1" in text
    assert "http://minio:9000" in text


def test_env_template_uses_localhost_targets() -> None:
    text = (REPO_ROOT / ".env.example").read_text()
    assert "@localhost:5432/arterial" in text
    assert "redis://localhost:6379/0" in text
    assert "http://localhost:9000" in text
    assert "@db:5432/arterial" not in text
    assert "redis://redis:6379/0" not in text
    assert "http://minio:9000" not in text


def test_redact_connection_url_masks_password() -> None:
    redacted = redact_connection_url("postgresql+psycopg2://arterial:secret@localhost:5432/arterial")
    assert redacted == "postgresql+psycopg2://arterial:***@localhost:5432/arterial"


def test_required_paths_exist_reports_missing_and_present(tmp_path: Path) -> None:
    existing = tmp_path / "present.txt"
    existing.write_text("ok")
    missing = tmp_path / "missing.txt"

    checks = required_paths_exist([existing, missing])

    assert checks[0].ok is True
    assert checks[1].ok is False
    assert checks[0].detail.endswith("present.txt")
    assert checks[1].detail.endswith("missing.txt")
