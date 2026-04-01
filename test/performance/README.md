# 键鼠操作性能测试

测试框架的键鼠回放性能，包括模拟操作的准确性、延迟和吞吐量。

## 架构

- **C# 程序** (`csharp/MouseKeySimulator`) - 使用 Win32 API SendInput 模拟键鼠操作
- **Python 脚本** (`python/test_playback_performance.py`) - 测试编排、数据收集和性能分析

## 测试指标

- **延迟** - 从发送指令到执行完成的时间
- **准确性** - 鼠标位置偏差、按键顺序正确性
- **吞吐量** - 每秒可执行的操作数
- **稳定性** - 连续执行的成功率

## 快速开始

```bash
# 构建 C# 程序
cd test/performance/csharp/MouseKeySimulator
dotnet build

# 运行 Python 测试
cd test/performance/python
pip install -r requirements.txt
python test_playback_performance.py
```
