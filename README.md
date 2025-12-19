# mac-faster

一款面向 macOS 的终端小工具，可以快速查看系统卡顿的瓶颈并给出解决方案。

## 功能

- 收集 CPU、负载、内存、Swap、磁盘使用等核心指标。
- 自动列出占用最高的进程，帮助定位“卡在哪儿”。
- 生成可读的诊断建议，指导清理和优化步骤。
- 支持 JSON 输出，方便集成到监控或日志系统。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用

```bash
python -m mac_faster.cli --top 5
# 或获取 JSON 数据
python -m mac_faster.cli --json
```

输出示例：

```
时间：2024-06-20 15:06:12
CPU：92% | 负载 (1/5/15)：5.40 / 3.21 / 2.11
内存：88% | 已用 30.1 GiB / 32.0 GiB
Swap：40% | 已用 6.0 GiB / 15.0 GiB
磁盘：
挂载点 | 已用 / 总计          | 占用
/      | 450.2 / 500.1 GiB | 90%
CPU 占用 Top：
PID  | 进程 | CPU | 内存 | 常驻内存
1234 | Xcode | 120% | 12% | 1.5 GiB
```

## 诊断逻辑

- **CPU**：负载或占用高于阈值时，列出前三名热点进程，并建议关闭或优化。
- **内存**：占用超过 85% 时提示，结合 Swap 使用给出释放建议。
- **磁盘空间**：分区占用超过 85% 时提醒清理。
- **电池**：在低电量且未接电源时提示可能的降频行为。

## 开发

```bash
pip install -r requirements-dev.txt
pytest
```

贡献与反馈欢迎提交 Issue / PR。
