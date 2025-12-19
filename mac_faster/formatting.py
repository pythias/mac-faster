"""Console-friendly formatting utilities."""

from __future__ import annotations

from typing import Iterable, Sequence

from .system_state import DiskUsage, ProcessUsage, SystemSnapshot


def format_bytes(num: float) -> str:
    suffixes = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(num)
    for suffix in suffixes:
        if value < 1024 or suffix == suffixes[-1]:
            return f"{value:.1f} {suffix}"
        value /= 1024
    return f"{value:.1f} TiB"


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    lines = []
    lines.append(_format_row(headers, widths))
    lines.append(_format_row(["-" * w for w in widths], widths))
    for row in rows:
        lines.append(_format_row(row, widths))
    return "\n".join(lines)


def format_process_table(processes: Iterable[ProcessUsage]) -> str:
    rows = [
        [
            str(proc.pid),
            proc.name,
            f"{proc.cpu_percent:.0f}%",
            f"{proc.memory_percent:.0f}%",
            format_bytes(proc.rss_bytes),
        ]
        for proc in processes
    ]
    return render_table(["PID", "进程", "CPU", "内存", "常驻内存"], rows) if rows else "无进程数据"


def format_disk_table(disks: Iterable[DiskUsage]) -> str:
    rows = [
        [disk.mount_point, f"{disk.used_gb:.1f} / {disk.total_gb:.1f} GiB", f"{disk.percent:.0f}%"]
        for disk in disks
    ]
    return render_table(["挂载点", "已用 / 总计", "占用"], rows) if rows else "无磁盘数据"


def format_snapshot(snapshot: SystemSnapshot) -> str:
    lines = [
        f"时间：{snapshot.timestamp:%Y-%m-%d %H:%M:%S}",
        f"CPU：{snapshot.cpu_percent:.0f}% | 负载 (1/5/15)：{snapshot.load_avg[0]:.2f} / {snapshot.load_avg[1]:.2f} / {snapshot.load_avg[2]:.2f}",
        f"内存：{snapshot.memory_percent:.0f}% | 已用 {format_bytes(snapshot.memory_used)} / {format_bytes(snapshot.memory_total)}",
        f"Swap：{snapshot.swap_percent:.0f}% | 已用 {format_bytes(snapshot.swap_used)} / {format_bytes(snapshot.swap_total)}",
    ]
    if snapshot.disk_usages:
        lines.append("磁盘：")
        lines.append(format_disk_table(snapshot.disk_usages))
    lines.append("CPU 占用 Top：")
    lines.append(format_process_table(snapshot.top_cpu_processes))
    lines.append("内存占用 Top：")
    lines.append(format_process_table(snapshot.top_memory_processes))
    return "\n".join(lines)


def _format_row(row: Sequence[str], widths: Sequence[int]) -> str:
    padded = [cell.ljust(width) for cell, width in zip(row, widths)]
    return " | ".join(padded)
