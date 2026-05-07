from __future__ import annotations

import argparse
import json
from pathlib import Path

from .browser import TistoryBrowser
from .config import DEFAULT_CONFIG, ensure_folders, load_config, write_default_config
from .publisher import run_publish, setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(prog="tistory-auto-publisher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create config.json and working folders.")
    init_parser.add_argument("--config", default="config.json")

    auth_parser = subparsers.add_parser("auth", help="Open browser for first manual login and 2FA.")
    auth_parser.add_argument("--config", default="config.json")

    publish_parser = subparsers.add_parser("publish", help="Publish due posts from the queue folder.")
    publish_parser.add_argument("--config", default="config.json")
    publish_parser.add_argument("--dry-run", action="store_true")

    doctor_parser = subparsers.add_parser("doctor", help="Check local configuration.")
    doctor_parser.add_argument("--config", default="config.json")

    args = parser.parse_args()

    if args.command == "init":
        config_path = Path(args.config).expanduser().resolve()
        created = write_default_config(config_path)
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["_base_dir"] = str(created.parent)
        ensure_folders(config)
        print(f"Created {created}")
        print("Edit blog_name and Telegram settings before publishing.")
        return 0

    if args.command == "auth":
        config, _ = load_config(args.config)
        ensure_folders(config)
        logger = setup_logging(config)
        with TistoryBrowser(config, logger) as browser:
            browser.auth()
        print("Login session saved.")
        return 0

    if args.command == "publish":
        return run_publish(args.config, dry_run=args.dry_run)

    if args.command == "doctor":
        config, _ = load_config(args.config)
        ensure_folders(config)
        print(f"Config OK: {Path(args.config).expanduser().resolve()}")
        print(f"Blog: {config['blog_name']}")
        try:
            import playwright  # noqa: F401

            print("Playwright: installed")
        except ImportError:
            print("Playwright: missing. Run 'py -m pip install -r requirements.txt'")
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
