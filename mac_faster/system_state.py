"""Collect system state for macOS laptops to diagnose slowdowns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import os
import time
from typing import Iterable, List, Optional, Tuple

import psutil


@dataclass
class ProcessUsage:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    rss_bytes: int
    read_bytes: int
    write_bytes: int


@dataclass
class DiskUsage:
    mount_point: str
    total_gb: float
    used_gb: float
    percent: float


@dataclass
class SystemSnapshot:
    timestamp: datetime
    cpu_percent: float
    load_avg: Tuple[float, float, float]
    cpu_count: int
    memory_total: int
    memory_used: int
    memory_percent: float
    swap_total: int
    swap_used: int
    swap_percent: float
    disk_io_read_bytes: int
    disk_io_write_bytes: int
    battery_percent: Optional[float]
    power_plugged: Optional[bool]
    top_cpu_processes: List[ProcessUsage] = field(default_factory=list)
    top_memory_processes: List[ProcessUsage] = field(default_factory=list)
    disk_usages: List[DiskUsage] = field(default_factory=list)


def gather_snapshot(top_n: int = 5) -> SystemSnapshot:
    """Collect a snapshot of the current system health."""
    cpu_count = psutil.cpu_count() or 0
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    cpu_percent = psutil.cpu_percent(interval=0.3)
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk_counters = psutil.disk_io_counters()
    battery = psutil.sensors_battery()

    processes = list(psutil.process_iter())
    _prime_cpu_percent(processes)
    process_usages = _process_usage(processes)

    disk_usages = _disk_usage_summary()

    return SystemSnapshot(
        timestamp=datetime.now(),
        cpu_percent=cpu_percent,
        load_avg=load_avg,
        cpu_count=cpu_count,
        memory_total=memory.total,
        memory_used=memory.used,
        memory_percent=memory.percent,
        swap_total=swap.total,
        swap_used=swap.used,
        swap_percent=swap.percent,
        disk_io_read_bytes=disk_counters.read_bytes if disk_counters else 0,
        disk_io_write_bytes=disk_counters.write_bytes if disk_counters else 0,
        battery_percent=battery.percent if battery else None,
        power_plugged=battery.power_plugged if battery else None,
        top_cpu_processes=sorted(process_usages, key=lambda p: p.cpu_percent, reverse=True)[:top_n],
        top_memory_processes=sorted(
            process_usages, key=lambda p: p.memory_percent, reverse=True
        )[:top_n],
        disk_usages=disk_usages,
    )


def _prime_cpu_percent(processes: Iterable[psutil.Process]) -> None:
    for proc in processes:
        try:
            proc.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    time.sleep(0.1)


def _process_usage(processes: Iterable[psutil.Process]) -> List[ProcessUsage]:
    usage: List[ProcessUsage] = []
    for proc in processes:
        try:
            with proc.oneshot():
                cpu = proc.cpu_percent(None)
                mem_percent = proc.memory_percent()
                mem_info = proc.memory_info()
                try:
                    io_counters = proc.io_counters() if proc.is_running() else None
                    read_bytes = io_counters.read_bytes if io_counters else 0
                    write_bytes = io_counters.write_bytes if io_counters else 0
                except (AttributeError, psutil.AccessDenied):
                    # Some processes may not support io_counters or require special permissions
                    read_bytes = 0
                    write_bytes = 0
                usage.append(
                    ProcessUsage(
                        pid=proc.pid,
                        name=proc.name(),
                        cpu_percent=cpu,
                        memory_percent=mem_percent,
                        rss_bytes=mem_info.rss,
                        read_bytes=read_bytes,
                        write_bytes=write_bytes,
                    )
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return usage


def _disk_usage_summary() -> List[DiskUsage]:
    disk_usages: List[DiskUsage] = []
    for partition in psutil.disk_partitions(all=False):
        if "rw" not in partition.opts:
            continue
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        disk_usages.append(
            DiskUsage(
                mount_point=partition.mountpoint,
                total_gb=round(usage.total / (1024**3), 2),
                used_gb=round(usage.used / (1024**3), 2),
                percent=usage.percent,
            )
        )
    return disk_usages
