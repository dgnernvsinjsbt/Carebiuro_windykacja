#!/usr/bin/env python3
"""Wrapper to run MOODENG test with progress output"""
import sys
import subprocess

# Run the test and capture output
result = subprocess.run([sys.executable, 'test_moodeng_reversal.py'],
                       capture_output=True, text=True, cwd='/workspaces/Carebiuro_windykacja')

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
