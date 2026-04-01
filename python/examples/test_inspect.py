"""验证脚本：测试 Python ↔ C# 子进程通信。

运行方式：
    cd python
    uv run python examples/test_inspect.py

前提条件：
    1. 已编译 C# 项目: cd csharp && dotnet build
    2. 已打开记事本（或任意窗口）
"""

from rpa.desktop import DesktopAgent, DesktopAgentError


def print_tree(node: dict, indent: int = 0) -> None:
    """以缩进格式打印控件树，方便人眼阅读。

    输出格式示例：
        [Window] 无标题 - Notepad  (className=Notepad)
          [Document] 文本编辑器  (className=RichEditD2DPT)
          [MenuBar] MenuBar  (automationId=MenuBar)
            [MenuItem] 文件  (automationId=File)
            [MenuItem] 编辑  (automationId=Edit)
    """
    prefix = "  " * indent

    # 组装显示信息
    control_type = node.get("controlType", "?")
    name = node.get("name", "")
    automation_id = node.get("automationId", "")
    class_name = node.get("className", "")

    # 显示名称（如果有的话）
    label = name if name else "(无名称)"

    # 附加信息
    extra_parts = []
    if automation_id:
        extra_parts.append(f"automationId={automation_id}")
    if class_name:
        extra_parts.append(f"className={class_name}")
    extra = f"  ({', '.join(extra_parts)})" if extra_parts else ""

    print(f"{prefix}[{control_type}] {label}{extra}")

    # 递归打印子控件
    for child in node.get("children", []):
        print_tree(child, indent + 1)


def main() -> None:
    print("=" * 60)
    print("  Python ↔ C# 子进程通信验证")
    print("=" * 60)
    print()

    agent = DesktopAgent()
    print(f"DesktopAgent 路径: {agent.exe_path}")
    print(f"文件存在: {agent.exe_path.exists()}")
    print()

    # 测试 1：按窗口名查找记事本
    print("--- 测试: 查找包含 'Notepad' 的窗口 ---")
    try:
        result = agent.inspect(name="Notepad")
        print(f"找到窗口: {result['window']}")
        print()
        print("控件树:")
        print_tree(result["tree"])
        print()
        print("✓ 测试通过！成功获取控件树。")
    except DesktopAgentError as e:
        print(f"✗ 测试失败: {e}")
        print()
        print("提示: 请确保记事本已打开。")

    print()
    print("=" * 60)
    print("  验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
