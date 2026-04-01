using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using FlaUI.Core.AutomationElements;
using FlaUI.UIA3;

// ===== 知识点 =====
// 这个程序的作用：通过命令行参数指定一个窗口，用 FlaUI 获取它的控件树，以 JSON 输出。
//
// FlaUI 是什么？
//   Windows 上每个应用的按钮、文本框、菜单等都是"控件"，它们组成一棵树（类似网页的 DOM 树）。
//   Windows 提供了 UI Automation 接口来读取这棵树，FlaUI 是这个接口的 C# 封装库。
//   UIA3 是 UI Automation 的第三代版本，支持更多控件类型。
//
// 为什么输出 JSON 到 stdout？
//   这样 Python 可以通过子进程启动这个程序，读取 stdout 就能拿到结构化数据。
//   这是最简单的跨语言通信方式，不需要网络、不需要额外依赖。

// 设置 UTF-8 输出，确保中文不会乱码
Console.OutputEncoding = Encoding.UTF8;

// JSON 序列化配置：驼峰命名 + 中文不转义 + 格式化
var jsonOptions = new JsonSerializerOptions
{
    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    WriteIndented = true,
    Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
};

try
{
    // ===== 知识点：顶层语句 (Top-level statements) =====
    // .NET 6+ 的 C# 支持顶层语句，不用写 Main 方法，直接写代码。
    // 编译器会隐式提供 args 变量，就是命令行参数数组。

    if (args.Length == 0 || args[0] == "--help")
    {
        PrintUsage();
        return;
    }

    if (args[0] == "inspect")
    {
        HandleInspect(args.Skip(1).ToArray());
    }
    else
    {
        OutputError($"未知命令: {args[0]}，使用 --help 查看帮助");
    }
}
catch (Exception ex)
{
    OutputError($"未处理的异常: {ex.Message}");
}

// ===== 命令处理 =====

void HandleInspect(string[] inspectArgs)
{
    // 解析 --name 或 --process 参数
    string? windowName = null;
    string? processName = null;
    int maxDepth = 5; // 默认最多遍历 5 层，防止控件树太深导致卡死

    for (int i = 0; i < inspectArgs.Length; i++)
    {
        switch (inspectArgs[i])
        {
            case "--name":
                if (i + 1 < inspectArgs.Length) windowName = inspectArgs[++i];
                break;
            case "--process":
                if (i + 1 < inspectArgs.Length) processName = inspectArgs[++i];
                break;
            case "--depth":
                if (i + 1 < inspectArgs.Length && int.TryParse(inspectArgs[++i], out var d)) maxDepth = d;
                break;
        }
    }

    if (windowName == null && processName == null)
    {
        OutputError("请指定 --name <窗口标题> 或 --process <进程名>");
        return;
    }

    // ===== 知识点：UIA3Automation =====
    // UIA3Automation 是 FlaUI 的入口对象，通过它可以访问整个 Windows 桌面的控件树。
    // using 语句确保用完后自动释放资源（COM 对象需要正确释放）。
    using var automation = new UIA3Automation();

    AutomationElement? targetWindow = null;

    if (processName != null)
    {
        // 按进程名查找：先找到进程 ID，再在桌面子窗口中匹配
        var processes = Process.GetProcessesByName(processName.Replace(".exe", ""));
        if (processes.Length == 0)
        {
            OutputError($"找不到进程: {processName}");
            return;
        }

        // ===== 知识点：通过进程 ID 匹配窗口 =====
        // 每个窗口控件都有 ProcessId 属性，表示它属于哪个进程。
        // 我们在桌面的所有子窗口中找到属于目标进程的那个窗口。
        var targetPid = processes[0].Id;
        var desktop = automation.GetDesktop();
        var allWindows = desktop.FindAllChildren();
        targetWindow = allWindows.FirstOrDefault(w =>
        {
            try { return w.Properties.ProcessId.Value == targetPid; }
            catch { return false; }
        });
    }
    else if (windowName != null)
    {
        // 按窗口标题查找：在桌面的子窗口中搜索
        // ===== 知识点：GetDesktop() =====
        // GetDesktop() 返回桌面根元素，它的子元素就是所有顶层窗口。
        // FindAllChildren() 获取所有子元素，然后我们手动匹配标题。
        var desktop = automation.GetDesktop();
        var allWindows = desktop.FindAllChildren();

        // 支持模糊匹配：窗口标题包含指定文本就算命中
        targetWindow = allWindows.FirstOrDefault(w =>
            w.Name != null && w.Name.Contains(windowName, StringComparison.OrdinalIgnoreCase));
    }

    if (targetWindow == null)
    {
        OutputError($"找不到窗口: {windowName ?? processName}");
        return;
    }

    // 递归遍历控件树并输出 JSON
    var tree = BuildUITree(targetWindow, maxDepth, 0);
    var result = new InspectResult
    {
        Success = true,
        Window = targetWindow.Name ?? "",
        Tree = tree,
    };

    Console.WriteLine(JsonSerializer.Serialize(result, jsonOptions));
}

// ===== 递归构建控件树 =====
// 这是核心函数：从一个控件开始，递归地获取所有子控件的信息。
//
// 知识点：为什么要限制深度？
//   有些应用的控件树非常深（比如浏览器渲染的网页内容），
//   不限制深度的话可能会遍历几千个节点，导致程序卡死或输出巨大的 JSON。
//   maxDepth=5 对于大多数场景够用了。

UITreeNode BuildUITree(AutomationElement element, int maxDepth, int currentDepth)
{
    // 安全地读取属性——有些控件不支持某些属性，会抛异常，所以用 try-catch 包裹
    string name = "";
    string controlType = "";
    string automationId = "";
    string className = "";
    int x = 0, y = 0, width = 0, height = 0;

    try { name = element.Name ?? ""; } catch { }
    try { controlType = element.ControlType.ToString(); } catch { }
    try { automationId = element.AutomationId ?? ""; } catch { }
    try { className = element.ClassName ?? ""; } catch { }
    try
    {
        var rect = element.BoundingRectangle;
        x = (int)rect.X; y = (int)rect.Y;
        width = (int)rect.Width; height = (int)rect.Height;
    }
    catch { }

    var node = new UITreeNode
    {
        Name = name,
        ControlType = controlType,
        AutomationId = automationId,
        ClassName = className,
        BoundingRect = new BoundingRect { X = x, Y = y, Width = width, Height = height },
    };

    // 还没到最大深度，继续遍历子控件
    if (currentDepth < maxDepth)
    {
        try
        {
            var children = element.FindAllChildren();
            foreach (var child in children)
            {
                node.Children.Add(BuildUITree(child, maxDepth, currentDepth + 1));
            }
        }
        catch
        {
            // 有些控件获取子元素会报错（比如跨进程的控件），跳过就好
        }
    }

    return node;
}

void PrintUsage()
{
    Console.WriteLine("""
        DesktopAgent — 桌面自动化服务

        用法:
          DesktopAgent inspect --name <窗口标题>     按标题查找窗口并获取控件树
          DesktopAgent inspect --process <进程名>     按进程名查找
          DesktopAgent inspect --name <标题> --depth 3  限制遍历深度（默认5）

        示例:
          DesktopAgent inspect --name "记事本"
          DesktopAgent inspect --process notepad
          DesktopAgent inspect --name "Excel" --depth 3
        """);
}

void OutputError(string message)
{
    var error = new { success = false, error = message };
    Console.WriteLine(JsonSerializer.Serialize(error, jsonOptions));
}

// ===== 数据模型 =====
// 这些类定义了输出 JSON 的结构。
// JsonPropertyName 特性指定 JSON 中的字段名（用小写驼峰风格）。

class InspectResult
{
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    [JsonPropertyName("window")]
    public string Window { get; set; } = "";

    [JsonPropertyName("tree")]
    public UITreeNode? Tree { get; set; }
}

class UITreeNode
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("controlType")]
    public string ControlType { get; set; } = "";

    [JsonPropertyName("automationId")]
    public string AutomationId { get; set; } = "";

    [JsonPropertyName("className")]
    public string ClassName { get; set; } = "";

    [JsonPropertyName("boundingRect")]
    public BoundingRect BoundingRect { get; set; } = new();

    [JsonPropertyName("children")]
    public List<UITreeNode> Children { get; set; } = new();
}

class BoundingRect
{
    [JsonPropertyName("x")]
    public int X { get; set; }

    [JsonPropertyName("y")]
    public int Y { get; set; }

    [JsonPropertyName("width")]
    public int Width { get; set; }

    [JsonPropertyName("height")]
    public int Height { get; set; }
}
