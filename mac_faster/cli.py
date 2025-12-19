"""Entry point for the mac-faster command line tool."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any, Dict

from .diagnostics import Bottleneck, diagnose
from .formatting import format_snapshot, render_table
from .system_state import SystemSnapshot, gather_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(
        description="快速查看 macOS 卡顿瓶颈和解决方案。",
    )
    parser.add_argument("--top", type=int, default=5, help="展示的高占用进程数量")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出原始数据和诊断结果")
    args = parser.parse_args()

    snapshot = gather_snapshot(top_n=args.top)
    bottlenecks = diagnose(snapshot)

    if args.json:
        print(_to_json(snapshot, bottlenecks))
        return

    print(format_snapshot(snapshot))
    if bottlenecks:
        print("\n可能的瓶颈：")
        print(_format_bottlenecks(bottlenecks))
    else:
        print("\n未发现明显瓶颈，性能正常。")


def _format_bottlenecks(bottlenecks: list[Bottleneck]) -> str:
    rows = [
        [bottleneck.title, bottleneck.issue, bottleneck.evidence, " / ".join(bottleneck.solutions)]
        for bottleneck in bottlenecks
    ]
    return render_table(["问题", "原因", "证据", "解决方案"], rows)


def _to_json(snapshot: SystemSnapshot, bottlenecks: list[Bottleneck]) -> str:
    snapshot_dict: Dict[str, Any] = asdict(snapshot)
    snapshot_dict["timestamp"] = snapshot.timestamp.isoformat()
    payload: Dict[str, Any] = {"snapshot": snapshot_dict, "bottlenecks": [asdict(b) for b in bottlenecks]}
    return json.dumps(payload, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
