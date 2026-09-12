#!/usr/bin/env python3
"""Gravitas project detector.

Detects the project type, language, and complexity tier to inform
budget profile selection. Outputs a JSON summary to stdout.
"""
import json
import os
import sys
from pathlib import Path


LANGUAGE_MARKERS = {
    "typescript": ["tsconfig.json", "package.json"],
    "python": ["pyproject.toml", "setup.py", "requirements.txt", "poetry.lock"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
    "java": ["pom.xml", "build.gradle"],
    "csharp": [".csproj", ".sln"],
    "ruby": ["Gemfile"],
    "php": ["composer.json"],
}

TEST_MARKERS = {
    "typescript": ["vitest.config", "jest.config", "*.test.ts", "*.spec.ts"],
    "python": ["pytest.ini", "conftest.py", "tests/"],
    "rust": ["tests/"],
    "go": ["*_test.go"],
    "java": ["src/test/"],
}

VERIFICATION_COMMANDS = {
    "typescript": "tsc --noEmit && eslint . && vitest run",
    "python": "mypy . && ruff check . && pytest",
    "rust": "cargo check && cargo clippy && cargo test",
    "go": "go vet ./... && go test ./...",
    "java": "./mvnw verify",
    "csharp": "dotnet build && dotnet test",
    "ruby": "bundle exec rubocop && bundle exec rspec",
    "php": "composer phpstan && composer test",
}


def detect_language(root: Path) -> str:
    for lang, markers in LANGUAGE_MARKERS.items():
        for marker in markers:
            if marker.startswith("*"):
                ext = marker[1:]
                matches = list(root.rglob(f"*{ext}"))
                if matches:
                    return lang
            elif (root / marker).exists():
                return lang
    return "unknown"


def count_source_files(root: Path, language: str) -> int:
    extensions = {
        "typescript": [".ts", ".tsx"],
        "python": [".py"],
        "rust": [".rs"],
        "go": [".go"],
        "java": [".java"],
        "csharp": [".cs"],
        "ruby": [".rb"],
        "php": [".php"],
    }.get(language, [])

    count = 0
    exclude = {"node_modules", ".git", "__pycache__", "target", "dist", "build"}
    for ext in extensions:
        for path in root.rglob(f"*{ext}"):
            if not any(ex in path.parts for ex in exclude):
                count += 1
    return count


def suggest_budget(source_count: int, has_tests: bool) -> str:
    if source_count < 10:
        return "eco"
    elif source_count < 50:
        return "balanced"
    elif source_count < 200:
        return "balanced"
    else:
        return "deep"


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    language = detect_language(root)
    source_count = count_source_files(root, language)
    has_tests = (root / "tests").exists() or (root / "test").exists() or (root / "spec").exists()
    verification_cmd = VERIFICATION_COMMANDS.get(language, "[language not detected — add manually]")
    suggested_budget = suggest_budget(source_count, has_tests)

    result = {
        "language": language,
        "source_files": source_count,
        "has_tests": has_tests,
        "verification_command": verification_cmd,
        "suggested_budget": suggested_budget,
        "root": str(root),
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
