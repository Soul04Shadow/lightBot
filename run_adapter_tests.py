"""
Test runner script for the adapter system.

This script helps you run different test suites easily.
"""

import sys
import os
import subprocess
import argparse

# Add current directory to Python path so tests can import modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def run_command(cmd, description):
    """Run a command and print results"""
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}\n")
    
    # Set up environment with PYTHONPATH
    env = os.environ.copy()
    project_root = os.path.dirname(os.path.abspath(__file__))
    env['PYTHONPATH'] = project_root
    
    # Use sys.executable to ensure we use the same Python as the runner
    # This handles venv correctly
    cmd = cmd.replace('python -m pytest', f'"{sys.executable}" -m pytest')
    
    result = subprocess.run(cmd, shell=True, env=env)
    
    if result.returncode != 0:
        print(f"\n❌ {description} FAILED")
        return False
    else:
        print(f"\n✅ {description} PASSED")
        return True


def main():
    parser = argparse.ArgumentParser(description='Run adapter system tests')
    parser.add_argument(
        'suite',
        nargs='?',
        choices=['unit', 'integration', 'all', 'quick'],
        default='quick',
        help='Test suite to run'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--coverage',
        '-c',
        action='store_true',
        help='Run with coverage report'
    )
    
    args = parser.parse_args()
    
    verbose_flag = '-v' if args.verbose else ''
    
    # Use python -m pytest to ensure we use the venv's pytest
    base_cmd = 'python -m pytest'
    coverage_prefix = f'{base_cmd} --cov=. --cov-report=html' if args.coverage else base_cmd
    
    results = []
    
    if args.suite in ['unit', 'all', 'quick']:
        print("\n🧪 Running Unit Tests...")
        
        tests = [
            ('test_adapter_base.py', 'Base Adapter Interface Tests'),
            ('test_adapter_factory.py', 'Adapter Factory Tests'),
            ('test_lighter_adapter.py', 'Lighter Adapter Tests'),
            ('test_market_data_provider.py', 'Market Data Provider Tests'),
        ]
        
        for test_file, description in tests:
            cmd = f'{coverage_prefix} tests/{test_file} {verbose_flag}'
            success = run_command(cmd, description)
            results.append((description, success))
    
    if args.suite in ['integration', 'all']:
        print("\n🌐 Running Integration Tests...")
        print("⚠️  WARNING: These tests make REAL API calls to testnet!")
        print("    They require valid credentials in .env file\n")
        
        cmd = f'python -m pytest tests/test_integration.py -m integration {verbose_flag}'
        success = run_command(cmd, 'Integration Tests')
        results.append(('Integration Tests', success))
    
    # Print summary
    print(f"\n{'='*70}")
    print("  TEST SUMMARY")
    print(f"{'='*70}\n")
    
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}  {description}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print(f"\n  Total: {passed}/{total} test suites passed")
    
    if args.coverage:
        print("\n📊 Coverage report generated in htmlcov/index.html")
    
    # Exit with error if any tests failed
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
