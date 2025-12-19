"""Entry point for the mac-faster command line tool."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any, Dict

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .diagnostics import Bottleneck, diagnose
from .formatting import format_bytes, format_snapshot, render_table
from .system_state import SystemSnapshot, gather_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(
        description="快速查看 macOS 卡顿瓶颈和解决方案。",
    )
    parser.add_argument("--top", type=int, default=5, help="展示的高占用进程数量")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出原始数据和诊断结果")
    parser.add_argument("--ui", action="store_true", help="以 Rich 风格输出更美观的终端 UI")
    args = parser.parse_args()

    snapshot = gather_snapshot(top_n=args.top)
    bottlenecks = diagnose(snapshot)

    if args.json:
        print(_to_json(snapshot, bottlenecks))
        return

    if args.ui:
        _render_rich(snapshot, bottlenecks)
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


def _render_rich(snapshot: SystemSnapshot, bottlenecks: list[Bottleneck]) -> None:
    console = Console()

    console.print(Panel(f"系统快照 - {snapshot.timestamp:%Y-%m-%d %H:%M:%S}", style="bold cyan"))

    summary = Table(show_header=False, box=box.ROUNDED)
    summary.add_row(
        "CPU",
        f"{snapshot.cpu_percent:.0f}% | 负载(1/5/15)：{snapshot.load_avg[0]:.2f}/{snapshot.load_avg[1]:.2f}/{snapshot.load_avg[2]:.2f}",
    )
    summary.add_row(
        "内存", f"{snapshot.memory_percent:.0f}% | 已用 {format_bytes(snapshot.memory_used)} / {format_bytes(snapshot.memory_total)}"
    )
    summary.add_row(
        "Swap", f"{snapshot.swap_percent:.0f}% | 已用 {format_bytes(snapshot.swap_used)} / {format_bytes(snapshot.swap_total)}"
    )
    console.print(summary)

    if snapshot.disk_usages:
        disk_table = Table(title="磁盘占用", box=box.SIMPLE_HEAD)
        disk_table.add_column("挂载点", style="bold")
        disk_table.add_column("已用 / 总计")
        disk_table.add_column("占用", justify="right")
        for disk in snapshot.disk_usages:
            disk_table.add_row(disk.mount_point, f"{disk.used_gb:.1f} / {disk.total_gb:.1f} GiB", f"{disk.percent:.0f}%")
        console.print(disk_table)

    console.print(_rich_process_table("CPU 占用 Top", snapshot.top_cpu_processes))
    console.print(_rich_process_table("内存占用 Top", snapshot.top_memory_processes))

    if bottlenecks:
        issues = Table(title="可能的瓶颈", box=box.SIMPLE_HEAD)
        issues.add_column("问题", style="bold red")
        issues.add_column("原因")
        issues.add_column("证据")
        issues.add_column("解决方案")
        for bottleneck in bottlenecks:
            issues.add_row(
                bottleneck.title,
                bottleneck.issue,
                bottleneck.evidence,
                "\n".join(bottleneck.solutions),
            )
        console.print(issues)
    else:
        console.print(Panel("未发现明显瓶颈，性能正常。", style="bold green"))


def _rich_process_table(title: str, processes: list[Any]) -> Table:
    table = Table(title=title, box=box.SIMPLE_HEAD)
    table.add_column("PID", justify="right")
    table.add_column("进程")
    table.add_column("CPU", justify="right")
    table.add_column("内存", justify="right")
    table.add_column("常驻内存", justify="right")

    if not processes:
        table.add_row("-", "无进程数据", "-", "-", "-")
        return table

    for proc in processes:
        table.add_row(
            str(proc.pid),
            proc.name,
            f"{proc.cpu_percent:.0f}%",
            f"{proc.memory_percent:.0f}%",
            format_bytes(proc.rss_bytes),
        )
    return table


if __name__ == "__main__":
    main()
