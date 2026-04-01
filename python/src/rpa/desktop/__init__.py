"""桌面自动化模块 — 通过子进程调用 C# DesktopAgent 服务。

知识点：subprocess（子进程）
    Python 的 subprocess 模块可以启动另一个程序（比如 .exe），
    并读取它的输出。这是最简单的跨语言通信方式：
    - Python 启动 C# 程序，传入命令行参数
    - C# 程序把结果以 JSON 格式打印到 stdout（标准输出）
    - Python 读取 stdout，用 json.loads() 解析成字典

    就像你在命令行里运行一个程序然后看它打印的内容一样，
    只不过这里是用代码自动完成的。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


class DesktopAgentError(Exception):
    """DesktopAgent 调用失败时抛出的异常。"""
    pass


class DesktopAgent:
    """C# DesktopAgent 的 Python 封装。

    用法：
        agent = DesktopAgent()  # 自动检测 exe 路径
        result = agent.inspect(name="Notepad")
        print(result["tree"]["children"])
    """

    def __init__(self, exe_path: str | Path | None = None, timeout: int = 30):
        """初始化 DesktopAgent。

        参数：
            exe_path: C# DesktopAgent.exe 的路径。如果不指定，会自动检测。
            timeout:  等待 C# 程序响应的超时时间（秒）。
        """
        if exe_path is not None:
            self.exe_path = Path(exe_path)
        else:
            # 自动检测：从 python/src/rpa/desktop/__init__.py 向上找到项目根目录
            # __init__.py → desktop/ → rpa/ → src/ → python/ → 项目根/
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            self.exe_path = (
                project_root
                / "csharp"
                / "src"
                / "DesktopAgent"
                / "bin"
                / "Debug"
                / "net8.0-windows"
                / "DesktopAgent.exe"
            )

        self.timeout = timeout

    def inspect(
        self,
        *,
        name: str | None = None,
        process: str | None = None,
        depth: int = 5,
    ) -> dict:
        """获取指定窗口的控件树。

        参数：
            name:    按窗口标题查找（模糊匹配）
            process: 按进程名查找
            depth:   控件树遍历深度（默认 5）

        返回：
            包含控件树的字典，结构如下：
            {
                "success": true,
                "window": "窗口标题",
                "tree": { "name": "...", "controlType": "...", "children": [...] }
            }
        """
        if name is None and process is None:
            raise DesktopAgentError("必须指定 name 或 process 参数")

        # 构建命令行参数
        cmd_args = ["inspect"]
        if name is not None:
            cmd_args += ["--name", name]
        if process is not None:
            cmd_args += ["--process", process]
        cmd_args += ["--depth", str(depth)]

        return self._run(cmd_args)

    def _run(self, cmd_args: list[str]) -> dict:
        """调用 C# 程序并解析 JSON 输出。

        知识点：subprocess.run() 的关键参数
            - capture_output=True  捕获程序的输出（不打印到终端）
            - text=True            把输出当文本处理（而不是原始字节）
            - encoding='utf-8'     强制用 UTF-8 编码（Windows 默认是 GBK，中文会乱码）
            - timeout=30           超过 30 秒没结束就强制终止
        """
        if not self.exe_path.exists():
            raise DesktopAgentError(
                f"找不到 DesktopAgent.exe: {self.exe_path}\n"
                f"请先编译 C# 项目: cd csharp && dotnet build"
            )

        cmd = [str(self.exe_path)] + cmd_args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            raise DesktopAgentError(
                f"DesktopAgent 执行超时（{self.timeout}秒）"
            )
        except FileNotFoundError:
            raise DesktopAgentError(f"找不到可执行文件: {self.exe_path}")

        # 解析 JSON 输出
        stdout = result.stdout.strip()
        if not stdout:
            raise DesktopAgentError(
                f"DesktopAgent 没有输出。\n"
                f"stderr: {result.stderr}"
            )

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            raise DesktopAgentError(
                f"DesktopAgent 输出了无效的 JSON:\n{stdout[:500]}\n"
                f"JSON 解析错误: {e}"
            )

        # 检查业务层面的错误
        if not data.get("success"):
            raise DesktopAgentError(data.get("error", "未知错误"))

        return data
