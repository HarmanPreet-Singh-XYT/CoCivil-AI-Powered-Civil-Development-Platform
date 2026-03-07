#!/usr/bin/env python3
from __future__ import annotations

import argparse

from app.config import settings
from app.devtools import (
    describe_service_target,
    redact_connection_url,
    render_preflight_checks,
    raise_for_failed_checks,
    run_preflight_checks,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify local Arterial infrastructure and config targets.")
    parser.add_argument(
        "--services",
        nargs="+",
        choices=("db", "redis", "s3"),
        default=("db", "redis", "s3"),
        help="Service checks to run.",
    )
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Skip the Docker daemon check.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    check_redis_backend = "redis" in args.services
    check_s3 = "s3" in args.services

    print("Active local targets:")
    print(f"  database: {redact_connection_url(settings.DATABASE_URL_SYNC)}")
    if check_redis_backend:
        print(f"  redis: {describe_service_target(settings.REDIS_URL, 6379)}")
    if check_s3:
        print(f"  object storage: {describe_service_target(settings.S3_ENDPOINT_URL, 9000)}")

    checks = run_preflight_checks(
        require_docker=not args.skip_docker,
        check_database="db" in args.services,
        check_redis_backend=check_redis_backend,
        check_s3=check_s3,
    )
    print("")
    print(render_preflight_checks(checks))
    try:
        raise_for_failed_checks(checks)
    except RuntimeError as exc:
        raise SystemExit(f"Preflight failed: {exc}") from exc
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
