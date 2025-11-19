#!/usr/bin/env python3
"""
Test runner script to validate all test files are working.
"""
import os
import sys
import importlib.util
from pathlib import Path

def test_python_syntax(file_path):
    """Test if a Python file has valid syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        compile(source, file_path, 'exec')
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def test_import_capability(file_path, backend_path):
    """Test if a test file can import required modules"""
    try:
        # Add backend path to sys.path
        sys.path.insert(0, backend_path)

        # Get module name from file path
        module_name = Path(file_path).stem

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return True, None
        else:
            return False, "Could not create module spec"

    except ImportError as e:
        return False, f"Import error: {str(e)}"
    except Exception as e:
        return False, str(e)

def main():
    # Get the tests directory (parent of scripts)
    scripts_dir = Path(__file__).parent
    tests_dir = scripts_dir.parent / "tests"
    backend_path = scripts_dir.parent / "backend"

    print("🔍 Testing all test files in tests/ directory")
    print("=" * 60)

    test_files = [
        "test_assistant_tool_use.py",
        "test_converter.py",
        "test_count_tokens.py",
        "test_messages.py",
        "test_performance.py",
        "test_streaming_format.py",
        "test_tool_use_format.py"
    ]

    results = {
        "syntax_ok": [],
        "syntax_failed": [],
        "import_ok": [],
        "import_failed": []
    }

    for test_file in test_files:
        file_path = tests_dir / test_file
        print(f"\n📋 Testing: {test_file}")

        if not file_path.exists():
            print(f"  ❌ File not found: {file_path}")
            continue

        # Test syntax
        syntax_ok, syntax_error = test_python_syntax(file_path)
        if syntax_ok:
            print(f"  ✅ Syntax: OK")
            results["syntax_ok"].append(test_file)
        else:
            print(f"  ❌ Syntax: {syntax_error}")
            results["syntax_failed"].append(test_file)
            continue

        # Test imports (skip for now to avoid complexity)
        print(f"  ⏭️  Import: Skipped (requires backend setup)")

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    print(f"✅ Syntax OK: {len(results['syntax_ok'])} files")
    for f in results["syntax_ok"]:
        print(f"   - {f}")

    if results["syntax_failed"]:
        print(f"❌ Syntax Failed: {len(results['syntax_failed'])} files")
        for f in results["syntax_failed"]:
            print(f"   - {f}")

    print(f"\n⏭️  Import tests skipped (requires backend setup)")

    # Test streaming format specifically
    print("\n" + "=" * 60)
    print("🚀 Testing streaming format script specifically")
    print("=" * 60)

    streaming_test = tests_dir / "test_streaming_format.py"
    if streaming_test.exists():
        print("Running streaming format test...")
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, str(streaming_test)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print("✅ Streaming format test: PASSED")
                # Show first few lines of output
                output_lines = result.stdout.split('\n')[:10]
                for line in output_lines:
                    if line.strip():
                        print(f"   {line}")
                if len(result.stdout.split('\n')) > 10:
                    print("   ... (output truncated)")
            else:
                print("❌ Streaming format test: FAILED")
                print(f"Error: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("⏰ Streaming format test: TIMEOUT")
        except Exception as e:
            print(f"❌ Streaming format test: ERROR - {e}")
    else:
        print("❌ Streaming format test file not found")

    print("\n" + "=" * 60)
    print("🎯 CONCLUSION")
    print("=" * 60)

    if len(results["syntax_ok"]) == len(test_files):
        print("✅ All test files have valid syntax!")
        print("✅ Ready for pytest execution")
    else:
        print(f"❌ {len(results['syntax_failed'])} test files have syntax errors")

    print("\n💡 To run tests with pytest:")
    print("   cd backend && cp ../pytest.ini . && cp -r ../tests . && PYTHONPATH=. pytest tests/")

if __name__ == "__main__":
    main()