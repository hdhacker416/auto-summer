from __future__ import annotations

import argparse
import json
import sys

from .account import SummerAccount
from .adb import Adb


def _account_from_args(args) -> SummerAccount:
    return SummerAccount(
        serial=args.serial,
        execute=getattr(args, "execute", False),
        max_batch=getattr(args, "max_batch", 5),
        audit_log=getattr(args, "audit_log", None),
    )


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def cmd_device_status(args) -> int:
    devices = Adb.list_devices()
    payload = {"devices": devices}
    if args.serial or devices:
        account = _account_from_args(args)
        payload["focus"] = account.device.current_focus()
        payload["ime"] = account.device.get_default_ime()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_friends_list(args) -> int:
    account = _account_from_args(args)
    friends = account.get_friend_list(limit=args.limit)
    print(json.dumps([friend.nickname for friend in friends], ensure_ascii=False, indent=2))
    return 0


def cmd_strangers_list(args) -> int:
    account = _account_from_args(args)
    strangers = account.get_stranger_list(limit=args.limit)
    print(
        json.dumps(
            [
                {
                    "nickname": stranger.nickname,
                    "school": stranger.school,
                    "age": stranger.age,
                    "distance": stranger.distance,
                    "bio": stranger.bio,
                }
                for stranger in strangers
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_messages_send_top(args) -> int:
    account = _account_from_args(args)
    results = account.messages.send_to_top_conversations(
        args.text,
        limit=args.limit,
        skip_names=set(args.skip_name or []),
    )
    print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))
    account.close()
    return 0


def cmd_input_text(args) -> int:
    account = _account_from_args(args)
    account.device.require_foreground()

    if not args.execute:
        account.device.audit.record(
            "dry_run_input_focused",
            text=args.text,
            clear=args.clear,
        )
        print(
            json.dumps(
                {
                    "input": False,
                    "dry_run": True,
                    "clear": args.clear,
                    "text_length": len(args.text),
                    "detail": "dry-run; add --execute to input text into the focused field",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    with account.device.adb_keyboard():
        account.device.input_text(args.text, clear=args.clear, mutating=True)
    account.close()
    print(
        json.dumps(
            {
                "input": True,
                "dry_run": False,
                "clear": args.clear,
                "text_length": len(args.text),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="summerbot")
    parser.add_argument("--serial", help="ADB device serial")
    parser.add_argument("--audit-log", help="Optional JSONL audit log path")
    parser.add_argument("--max-batch", type=int, default=5)

    subparsers = parser.add_subparsers(dest="group", required=True)

    device = subparsers.add_parser("device")
    device_sub = device.add_subparsers(dest="command", required=True)
    device_status = device_sub.add_parser("status")
    device_status.set_defaults(func=cmd_device_status)

    friends = subparsers.add_parser("friends")
    friends_sub = friends.add_subparsers(dest="command", required=True)
    friends_list = friends_sub.add_parser("list")
    friends_list.add_argument("--limit", type=int, default=5)
    friends_list.set_defaults(func=cmd_friends_list)

    strangers = subparsers.add_parser("strangers")
    strangers_sub = strangers.add_subparsers(dest="command", required=True)
    strangers_list = strangers_sub.add_parser("list")
    strangers_list.add_argument("--limit", type=int, default=5)
    strangers_list.set_defaults(func=cmd_strangers_list)

    messages = subparsers.add_parser("messages")
    messages_sub = messages.add_subparsers(dest="command", required=True)
    send_top = messages_sub.add_parser("send-top")
    send_top.add_argument("--limit", type=int, default=5)
    send_top.add_argument("--text", required=True)
    send_top.add_argument("--skip-name", action="append")
    send_top.add_argument("--execute", action="store_true")
    send_top.set_defaults(func=cmd_messages_send_top)

    input_parser = subparsers.add_parser("input")
    input_sub = input_parser.add_subparsers(dest="command", required=True)
    input_text = input_sub.add_parser("text")
    input_text.add_argument("--text", required=True)
    input_text.add_argument(
        "--clear",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Clear the focused field before inputting text.",
    )
    input_text.add_argument("--execute", action="store_true")
    input_text.set_defaults(func=cmd_input_text)

    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
