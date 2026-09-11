#!/usr/bin/env python3
"""Gravitas verification runner.

Runs the appropriate verification chain for the detected project type
and emits a machine-parseable VERDICT: PASS or VERDICT: FAIL.

Usage: python verify.py [--lang LANG] [--cmd CMD]
"""
import json
import subprocess
import sys
import argparse
from pathlib import Path


VERIFICATION_CHAINS = {
    "typescript": "tsc --noEmit && eslint . && vitest run",
    "python": "mypy . && ruff check . && pytest",
    "rust": "cargo check && cargo clippy && cargo test",
    "go": "go vet ./... && go test ./...",
    "java": "./mvnw verify",
    "csharp": "dotnet build && dotnet test",
    "ruby": "bundle exec rubocop && bundle exec rspec",
    "php": "composer phpstan && composer test",
}


def detect_language() -> str:
    cwd = Path.cwd()
    checks = [
        ("typescript", "tsconfig.json"),
        ("python", "pyproject.toml"),
        ("python", "setup.py"),
        ("rust", "Cargo.toml"),
        ("go", "go.mod"),
        ("java", "pom.xml"),
        ("java", "build.gradle"),
        ("csharp", ".sln"),
        ("ruby", "Gemfile"),
        ("php", "composer.json"),
    ]
    for lang, marker in checks:
        if (cwd / marker).exists():
            return lang
    return "unknown"


def run_verification(command: str) -> tuple[bool, str]:
    """Run the verification command and return (success, output)."""
    import shlex
    try:
        commands = [cmd.strip() for cmd in command.split("&&")]
        full_output = ""
        for cmd in commands:
            parts = shlex.split(cmd)
            result = subprocess.run(parts, capture_output=True, text=True, timeout=300)
            full_output += result.stdout + result.stderr
            if result.returncode != 0:
                return False, full_output
        return True, full_output
    except subprocess.TimeoutExpired:
        return False, "ERROR: verification timed out after 300 seconds"
    except Exception as e:
        return False, f"ERROR: {e}"


def main():
    parser = argparse.ArgumentParser(description="Gravitas verification runner")
    parser.add_argument("--lang", help="Override language detection")
    parser.add_argument("--cmd", help="Override verification command")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    language = args.lang or detect_language()

    if args.cmd:
        command = args.cmd
    elif language in VERIFICATION_CHAINS:
        command = VERIFICATION_CHAINS[language]
    else:
        print(f"VERDICT: FAIL -- language '{language}' not recognized")
        print("Specify --lang or --cmd to run verification manually.")
        sys.exit(1)

    print(f"Language: {language}")
    print(f"Command:  {command}")
    print("Running...")
    print("-" * 60)

    success, output = run_verification(command)

    print(output)
    print("-" * 60)

    if args.json:
        result = {
            "language": language,
            "command": command,
            "success": success,
            "output": output,
            "verdict": "PASS" if success else "FAIL",
        }
        print(json.dumps(result, indent=2))
    else:
        if success:
            print("VERDICT: PASS")
        else:
            print("VERDICT: FAIL -- see output above")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
