import subprocess
import json
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any

# Path to the C# executable
SIMULATOR_PATH = Path(__file__).parent.parent / "csharp" / "MouseKeySimulator" / "bin" / "Debug" / "net8.0-windows" / "MouseKeySimulator.exe"


class PerformanceTest:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single command and return the result"""
        cmd_json = json.dumps(command)
        result = subprocess.run(
            [str(SIMULATOR_PATH), cmd_json],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        return json.loads(result.stdout)

    def test_mouse_move_accuracy(self, iterations: int = 100):
        """Test mouse movement accuracy"""
        print(f"\n=== Testing Mouse Move Accuracy ({iterations} iterations) ===")

        errors = []
        durations = []

        for i in range(iterations):
            target_x, target_y = 500 + i, 300 + i
            command = {"type": "mouse_move", "x": target_x, "y": target_y}

            result = self.execute_command(command)

            if result["success"]:
                actual_x = result.get("actual_x", 0)
                actual_y = result.get("actual_y", 0)
                error = abs(target_x - actual_x) + abs(target_y - actual_y)
                errors.append(error)
                durations.append(result["duration_ms"])
            else:
                print(f"  Failed: {result.get('error')}")

        if errors:
            print(f"  Average position error: {statistics.mean(errors):.2f} pixels")
            print(f"  Max position error: {max(errors)} pixels")
            print(f"  Average duration: {statistics.mean(durations):.3f} ms")
            print(f"  Min duration: {min(durations):.3f} ms")
            print(f"  Max duration: {max(durations):.3f} ms")

        self.results.append({
            "test": "mouse_move_accuracy",
            "iterations": iterations,
            "avg_error": statistics.mean(errors) if errors else None,
            "avg_duration_ms": statistics.mean(durations) if durations else None
        })

    def test_click_throughput(self, iterations: int = 100):
        """Test click operation throughput"""
        print(f"\n=== Testing Click Throughput ({iterations} iterations) ===")

        durations = []
        start_time = time.perf_counter()

        for _ in range(iterations):
            command = {"type": "left_click"}
            result = self.execute_command(command)

            if result["success"]:
                durations.append(result["duration_ms"])
            else:
                print(f"  Failed: {result.get('error')}")

        total_time = time.perf_counter() - start_time

        if durations:
            print(f"  Total time: {total_time:.3f} seconds")
            print(f"  Throughput: {iterations / total_time:.2f} clicks/second")
            print(f"  Average duration: {statistics.mean(durations):.3f} ms")
            print(f"  Std deviation: {statistics.stdev(durations):.3f} ms")

        self.results.append({
            "test": "click_throughput",
            "iterations": iterations,
            "total_time_s": total_time,
            "throughput": iterations / total_time if total_time > 0 else 0,
            "avg_duration_ms": statistics.mean(durations) if durations else None
        })

    def test_keyboard_input(self, iterations: int = 50):
        """Test keyboard input performance"""
        print(f"\n=== Testing Keyboard Input ({iterations} iterations) ===")

        durations = []
        # Test with 'A' key (VK_A = 0x41)
        key_code = 0x41

        for _ in range(iterations):
            command = {"type": "type_key", "key_code": key_code}
            result = self.execute_command(command)

            if result["success"]:
                durations.append(result["duration_ms"])
            else:
                print(f"  Failed: {result.get('error')}")

        if durations:
            print(f"  Average duration: {statistics.mean(durations):.3f} ms")
            print(f"  Min duration: {min(durations):.3f} ms")
            print(f"  Max duration: {max(durations):.3f} ms")

        self.results.append({
            "test": "keyboard_input",
            "iterations": iterations,
            "avg_duration_ms": statistics.mean(durations) if durations else None
        })

    def save_results(self, filename: str = "performance_results.json"):
        """Save test results to JSON file"""
        output_path = Path(__file__).parent / filename
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n=== Results saved to {output_path} ===")


def main():
    print("=== DeskFlow Playback Performance Test ===")
    print(f"Simulator path: {SIMULATOR_PATH}")

    if not SIMULATOR_PATH.exists():
        print(f"\nError: Simulator not found at {SIMULATOR_PATH}")
        print("Please build the C# project first:")
        print("  cd test/performance/csharp/MouseKeySimulator")
        print("  dotnet build")
        return

    test = PerformanceTest()

    # Run tests
    test.test_mouse_move_accuracy(iterations=100)
    test.test_click_throughput(iterations=100)
    test.test_keyboard_input(iterations=50)

    # Save results
    test.save_results()

    print("\n=== All tests completed ===")


if __name__ == "__main__":
    main()

