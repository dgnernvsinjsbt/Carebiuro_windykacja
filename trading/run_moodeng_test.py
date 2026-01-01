#!/usr/bin/env python3
"""Run MOODENG reversal test and save results to file"""
import subprocess
import sys

# Run the test script and capture output
result = subprocess.run([sys.executable, 'test_moodeng_reversal.py'],
                       capture_output=True, text=True, timeout=300)

# Write to both stdout and file
output = result.stdout + result.stderr
print(output)

# Also save to file for verification
with open('/tmp/moodeng_test_results.txt', 'w') as f:
    f.write(output)

print("\n[RESULTS SAVED TO: /tmp/moodeng_test_results.txt]")
sys.exit(result.returncode)
