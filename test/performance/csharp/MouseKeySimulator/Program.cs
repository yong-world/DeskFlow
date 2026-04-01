using System;
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace MouseKeySimulator;

public class Program
{
    public static void Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.WriteLine("Usage: MouseKeySimulator <command_json>");
            Console.WriteLine("Example: MouseKeySimulator '{\"type\":\"mouse_move\",\"x\":100,\"y\":200}'");
            return;
        }

        var json = args[0];
        var command = JsonSerializer.Deserialize<Command>(json);

        if (command == null)
        {
            Console.WriteLine("{\"success\":false,\"error\":\"Invalid JSON\"}");
            return;
        }

        var sw = Stopwatch.StartNew();
        var result = ExecuteCommand(command);
        sw.Stop();

        result.DurationMs = sw.Elapsed.TotalMilliseconds;
        Console.WriteLine(JsonSerializer.Serialize(result));
    }

    private static Result ExecuteCommand(Command command)
    {
        try
        {
            switch (command.Type)
            {
                case "mouse_move":
                    if (command.X.HasValue && command.Y.HasValue)
                    {
                        InputSimulator.MoveMouse(command.X.Value, command.Y.Value);
                        var pos = InputSimulator.GetMousePosition();
                        return new Result
                        {
                            Success = true,
                            ActualX = pos.X,
                            ActualY = pos.Y
                        };
                    }
                    break;

                case "left_click":
                    InputSimulator.LeftClick();
                    return new Result { Success = true };

                case "right_click":
                    InputSimulator.RightClick();
                    return new Result { Success = true };

                case "type_key":
                    if (command.KeyCode.HasValue)
                    {
                        InputSimulator.TypeKey(command.KeyCode.Value);
                        return new Result { Success = true };
                    }
                    break;
            }

            return new Result { Success = false, Error = "Invalid command parameters" };
        }
        catch (Exception ex)
        {
            return new Result { Success = false, Error = ex.Message };
        }
    }
}

public class Command
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = "";

    [JsonPropertyName("x")]
    public int? X { get; set; }

    [JsonPropertyName("y")]
    public int? Y { get; set; }

    [JsonPropertyName("key_code")]
    public ushort? KeyCode { get; set; }
}

public class Result
{
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    [JsonPropertyName("error")]
    public string? Error { get; set; }

    [JsonPropertyName("duration_ms")]
    public double DurationMs { get; set; }

    [JsonPropertyName("actual_x")]
    public int? ActualX { get; set; }

    [JsonPropertyName("actual_y")]
    public int? ActualY { get; set; }
}
