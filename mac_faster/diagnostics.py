"""Generate actionable diagnostics for a macOS system snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .system_state import DiskUsage, ProcessUsage, SystemSnapshot


@dataclass
class Bottleneck:
    title: str
    issue: str
    evidence: str
    solutions: Sequence[str]


def diagnose(snapshot: SystemSnapshot) -> List[Bottleneck]:
    """Analyze a system snapshot and return likely bottlenecks with fixes."""
    bottlenecks: List[Bottleneck] = []

    bottlenecks.extend(_diagnose_cpu(snapshot))
    bottlenecks.extend(_diagnose_memory(snapshot))
    bottlenecks.extend(_diagnose_disk(snapshot.disk_usages))
    bottlenecks.extend(_diagnose_swap(snapshot.swap_percent))
    battery_note = _diagnose_battery(snapshot)
    if battery_note:
        bottlenecks.append(battery_note)

    return bottlenecks


def _diagnose_cpu(snapshot: SystemSnapshot) -> List[Bottleneck]:
    findings: List[Bottleneck] = []
    load_1m, load_5m, _ = snapshot.load_avg
    overloaded = snapshot.cpu_percent >= 85 or load_1m >= snapshot.cpu_count * 1.5
    if overloaded:
        offenders = _top_process_summary(snapshot.top_cpu_processes)
        findings.append(
            Bottleneck(
                title="CPU 热点",
                issue="CPU 长时间占用高，正在拖慢系统响应。",
                evidence=f"总占用 {snapshot.cpu_percent:.0f}% ，1 分钟平均负载 {load_1m:.2f}（{snapshot.cpu_count} 核心）。{offenders}",
                solutions=[
                    "在活动监视器中强制退出占用高的进程，或在终端执行 `kill <pid>`。",
                    "关闭或暂停正在进行的大量编译、转码、虚拟机等任务。",
                    "升级重负载应用，避免兼容层或模拟器导致的额外 CPU 消耗。",
                ],
            )
        )
    elif load_1m > snapshot.cpu_count:
        findings.append(
            Bottleneck(
                title="CPU 负载偏高",
                issue="负载超过可用核心数，存在短时堵塞。",
                evidence=f"1 分钟平均负载 {load_1m:.2f}，核心数 {snapshot.cpu_count}。",
                solutions=[
                    "检查是否有后台编译或脚本任务忘记关闭。",
                    "减少同时运行的 Docker/虚拟机实例数量。",
                ],
            )
        )
    return findings


def _diagnose_memory(snapshot: SystemSnapshot) -> List[Bottleneck]:
    findings: List[Bottleneck] = []
    if snapshot.memory_percent >= 85:
        offenders = _top_process_summary(snapshot.top_memory_processes)
        findings.append(
            Bottleneck(
                title="内存压力",
                issue="可用内存不足，系统可能在频繁换页导致卡顿。",
                evidence=f"内存占用 {snapshot.memory_percent:.0f}% ，已用 {snapshot.memory_used / (1024**3):.1f} GiB。{offenders}",
                solutions=[
                    "关闭占用高的应用或浏览器标签页，减少并行打开的工程。",
                    "在活动监视器中查看“内存压力”是否持续偏高，必要时重启占用高的服务。",
                    "升级内存容量或启用通用控制/Sidecar 等功能时减少后台虚拟机数量。",
                ],
            )
        )
    return findings


def _diagnose_disk(disks: Sequence[DiskUsage]) -> List[Bottleneck]:
    findings: List[Bottleneck] = []
    for disk in disks:
        if disk.percent >= 85:
            findings.append(
                Bottleneck(
                    title="磁盘空间不足",
                    issue=f"{disk.mount_point} 分区空间告急，写入和虚拟内存会变慢。",
                    evidence=f"使用率 {disk.percent:.0f}% （已用 {disk.used_gb:.1f} / {disk.total_gb:.1f} GiB）。",
                    solutions=[
                        "清理 Xcode DerivedData、Pod 缓存、Docker 镜像等临时文件。",
                        "将大型视频、安装包移动到外置硬盘或 iCloud。",
                        "开启“优化 Mac 存储”并清空废纸篓。",
                    ],
                )
            )
    return findings


def _diagnose_swap(swap_percent: float) -> List[Bottleneck]:
    if swap_percent < 15:
        return []
    severity = "频繁" if swap_percent >= 40 else "明显"
    return [
        Bottleneck(
            title="Swap 读写",
            issue=f"出现{severity}的虚拟内存读写，说明物理内存紧张。",
            evidence=f"交换分区占用 {swap_percent:.0f}% 。",
            solutions=[
                "减少常驻后台的 Electron/浏览器应用数量。",
                "关闭占用内存高的容器或模拟器，释放内存后观察卡顿是否缓解。",
            ],
        )
    ]


def _diagnose_battery(snapshot: SystemSnapshot) -> Bottleneck | None:
    if snapshot.battery_percent is None:
        return None
    if not snapshot.power_plugged and snapshot.battery_percent < 20:
        return Bottleneck(
            title="电量过低",
            issue="电池电量低于 20%，系统可能自动降频。",
            evidence=f"当前电量 {snapshot.battery_percent:.0f}% ，未连接电源。",
            solutions=[
                "连接电源适配器，避免 macOS 自动降低性能。",
                "在设置里关闭“低电量模式”。",
            ],
        )
    return None


def _top_process_summary(processes: Sequence[ProcessUsage]) -> str:
    if not processes:
        return "未能识别高占用进程。"
    offenders = ", ".join(
        f"{proc.name} (pid {proc.pid}, {proc.cpu_percent:.0f}% CPU, {proc.memory_percent:.0f}% 内存)"
        for proc in processes[:3]
    )
    return f"主要占用：{offenders}。"
