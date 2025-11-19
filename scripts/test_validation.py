#!/usr/bin/env python3
"""
简单的pytest验证脚本
"""
import subprocess
import sys
import os

def main():
    # 检查当前目录
    print(f"当前工作目录: {os.getcwd()}")

    # 尝试运行pytest --collect-only来验证测试发现
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "tests/"],
            cwd="backend",
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": ".:app"}
        )

        print(f"pytest收集结果:")
        print(f"返回码: {result.returncode}")
        print(f"标准输出:\n{result.stdout}")
        if result.stderr:
            print(f"标准错误:\n{result.stderr}")

        if result.returncode == 0:
            print("✅ 测试收集成功")
        else:
            print("❌ 测试收集失败")
            return False

    except Exception as e:
        print(f"执行pytest时出错: {e}")
        return False

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)