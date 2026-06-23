"""Worker process used by HmsGuiSession.safe_invoke_action."""

from __future__ import annotations

import argparse
import json
import sys

from .session import HmsGuiSession


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hwnd", required=True, type=int)
    parser.add_argument("--target", required=True)
    parser.add_argument("--action", default="click")
    parser.add_argument("--jre-bin", default=None)
    parser.add_argument("--role-filter", default=None)
    parser.add_argument("--allow-disabled", action="store_true")
    parser.add_argument("--require-visible", action="store_true")
    parser.add_argument("--ancestor-name", default=None)
    parser.add_argument("--ancestor-role-filter", default=None)
    args = parser.parse_args(argv)

    with HmsGuiSession(hwnd=args.hwnd, jre_bin=args.jre_bin) as session:
        result = session.invoke_action(
            args.target,
            action_name=args.action,
            role_filter=args.role_filter,
            require_enabled=not args.allow_disabled,
            require_visible=args.require_visible,
            ancestor_name=args.ancestor_name,
            ancestor_role_filter=args.ancestor_role_filter,
        )
    print(json.dumps(result.to_dict()))
    return 0 if result.ok else 2


if __name__ == "__main__":
    sys.exit(main())
