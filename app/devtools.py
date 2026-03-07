from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit

import redis
from sqlalchemy import create_engine, text

from app.config import settings


@dataclass(slots=True)
class PreflightCheck:
    name: str
    ok: bool
    detail: str


def redact_connection_url(url: str) -> str:
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    if parsed.port is not None:
        hostname = f"{hostname}:{parsed.port}"

    if parsed.username:
        credentials = parsed.username
        if parsed.password is not None:
            credentials = f"{credentials}:***"
        hostname = f"{credentials}@{hostname}"

    sanitized = SplitResult(
        scheme=parsed.scheme,
        netloc=hostname,
        path=parsed.path,
        query=parsed.query,
        fragment=parsed.fragment,
    )
    return urlunsplit(sanitized)


def describe_service_target(url: str, default_port: int) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    return f"{host}:{port}"


def required_paths_exist(paths: list[Path] | tuple[Path, ...]) -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    for path in paths:
        resolved = path.resolve()
        exists = resolved.exists()
        checks.append(
            PreflightCheck(
                name=f"required file {path.name}",
                ok=exists,
                detail=str(resolved),
            )
        )
    return checks


def check_docker_daemon() -> PreflightCheck:
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        return PreflightCheck("docker daemon", False, "docker CLI is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        return PreflightCheck("docker daemon", False, "docker info timed out")

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "docker info failed").strip()
        return PreflightCheck("docker daemon", False, detail)
    version = (result.stdout or "").strip() or "reachable"
    return PreflightCheck("docker daemon", True, f"server {version}")


def check_tcp_endpoint(name: str, url: str, default_port: int, timeout_seconds: float = 2.0) -> PreflightCheck:
    parsed = urlsplit(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return PreflightCheck(name, True, f"{host}:{port} reachable")
    except OSError as exc:
        return PreflightCheck(name, False, f"{host}:{port} unreachable ({exc})")


def check_database_connection(timeout_seconds: float = 5.0) -> PreflightCheck:
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True, connect_args={"connect_timeout": int(timeout_seconds)})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - exact driver errors vary by environment
        return PreflightCheck("database query", False, str(exc))
    finally:
        engine.dispose()
    return PreflightCheck("database query", True, "SELECT 1 succeeded")


def check_redis_connection(timeout_seconds: float = 2.0) -> PreflightCheck:
    client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=timeout_seconds, socket_timeout=timeout_seconds)
    try:
        client.ping()
    except Exception as exc:  # pragma: no cover - exact driver errors vary by environment
        return PreflightCheck("redis ping", False, str(exc))
    finally:
        try:
            client.close()
        except Exception:  # pragma: no cover - defensive cleanup
            pass
    return PreflightCheck("redis ping", True, "PING succeeded")


def run_preflight_checks(
    *,
    require_docker: bool = False,
    check_database: bool = True,
    check_redis_backend: bool = False,
    check_s3: bool = False,
    required_paths: list[Path] | tuple[Path, ...] | None = None,
) -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    if require_docker:
        checks.append(check_docker_daemon())
    if check_database:
        checks.append(check_tcp_endpoint("database port", settings.DATABASE_URL_SYNC, 5432))
        checks.append(check_database_connection())
    if check_redis_backend:
        checks.append(check_tcp_endpoint("redis port", settings.REDIS_URL, 6379))
        checks.append(check_redis_connection())
    if check_s3:
        checks.append(check_tcp_endpoint("object storage port", settings.S3_ENDPOINT_URL, 9000))
    if required_paths:
        checks.extend(required_paths_exist(required_paths))
    return checks


def assert_preflight_checks(
    *,
    require_docker: bool = False,
    check_database: bool = True,
    check_redis_backend: bool = False,
    check_s3: bool = False,
    required_paths: list[Path] | tuple[Path, ...] | None = None,
) -> list[PreflightCheck]:
    checks = run_preflight_checks(
        require_docker=require_docker,
        check_database=check_database,
        check_redis_backend=check_redis_backend,
        check_s3=check_s3,
        required_paths=required_paths,
    )
    raise_for_failed_checks(checks)
    return checks


def raise_for_failed_checks(checks: list[PreflightCheck]) -> None:
    failures = [check for check in checks if not check.ok]
    if failures:
        message = "; ".join(f"{check.name}: {check.detail}" for check in failures)
        raise RuntimeError(message)


def render_preflight_checks(checks: list[PreflightCheck]) -> str:
    lines = []
    for check in checks:
        status = "ok" if check.ok else "fail"
        lines.append(f"[{status}] {check.name}: {check.detail}")
    return "\n".join(lines)
