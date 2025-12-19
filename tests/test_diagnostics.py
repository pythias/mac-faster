from datetime import datetime

from mac_faster.diagnostics import diagnose
from mac_faster.system_state import DiskUsage, ProcessUsage, SystemSnapshot


def make_snapshot(
    *,
    cpu_percent: float = 20,
    load_avg=(0.5, 0.5, 0.5),
    cpu_count: int = 8,
    memory_percent: float = 40,
    memory_used: int = 8 * 1024**3,
    memory_total: int = 32 * 1024**3,
    swap_percent: float = 0,
    disk_usages=None,
    top_cpu_processes=None,
    top_memory_processes=None,
    battery_percent=None,
    power_plugged=None,
) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=datetime.now(),
        cpu_percent=cpu_percent,
        load_avg=load_avg,
        cpu_count=cpu_count,
        memory_total=memory_total,
        memory_used=memory_used,
        memory_percent=memory_percent,
        swap_total=16 * 1024**3,
        swap_used=swap_percent / 100 * 16 * 1024**3,
        swap_percent=swap_percent,
        disk_io_read_bytes=0,
        disk_io_write_bytes=0,
        battery_percent=battery_percent,
        power_plugged=power_plugged,
        top_cpu_processes=top_cpu_processes or [],
        top_memory_processes=top_memory_processes or [],
        disk_usages=disk_usages or [],
    )


def test_cpu_bottleneck_detected():
    offenders = [
        ProcessUsage(pid=1, name="heavy-task", cpu_percent=140, memory_percent=10, rss_bytes=512, read_bytes=0, write_bytes=0)
    ]
    snapshot = make_snapshot(cpu_percent=92, load_avg=(6.0, 3.2, 2.1), cpu_count=4, top_cpu_processes=offenders)
    notes = diagnose(snapshot)
    assert any("CPU 热点" == note.title for note in notes)


def test_memory_pressure_detected():
    offenders = [
        ProcessUsage(pid=2, name="browser", cpu_percent=10, memory_percent=35, rss_bytes=2 * 1024**3, read_bytes=0, write_bytes=0)
    ]
    snapshot = make_snapshot(memory_percent=90, memory_used=29 * 1024**3, top_memory_processes=offenders)
    notes = diagnose(snapshot)
    assert any("内存压力" == note.title for note in notes)


def test_disk_usage_detected():
    disks = [DiskUsage(mount_point="/", total_gb=500, used_gb=460, percent=92)]
    snapshot = make_snapshot(disk_usages=disks)
    notes = diagnose(snapshot)
    assert any("磁盘空间不足" == note.title for note in notes)


def test_swap_warning_detected():
    snapshot = make_snapshot(swap_percent=50)
    notes = diagnose(snapshot)
    assert any("Swap 读写" == note.title for note in notes)


def test_battery_low_detected():
    snapshot = make_snapshot(battery_percent=15, power_plugged=False)
    notes = diagnose(snapshot)
    assert any("电量过低" == note.title for note in notes)


def test_no_bottleneck_when_normal():
    snapshot = make_snapshot()
    notes = diagnose(snapshot)
    assert notes == []
