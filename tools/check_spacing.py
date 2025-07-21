"""
Custom linting script to enforce spaces around equals signs in function call keyword arguments.

This enforces the style: func(param = value) instead of func(param=value)
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


class SpacingChecker(ast.NodeVisitor):
    """AST visitor to find function calls with keyword arguments."""

    def __init__(self, source_lines: List[str], filename: str):
        self.source_lines = source_lines
        self.filename = filename
        self.violations: List[Tuple[int, int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call nodes and check keyword argument spacing."""
        for keyword in node.keywords:
            if keyword.arg is not None:  # Skip **kwargs
                self._check_keyword_spacing(keyword)
        self.generic_visit(node)

    def _check_keyword_spacing(self, keyword: ast.keyword) -> None:
        """Check if a keyword argument has proper spacing around equals sign."""
        # Get the line content
        line_num = keyword.lineno - 1  # Convert to 0-based index
        if line_num >= len(self.source_lines):
            return

        line = self.source_lines[line_num]

        # Find the keyword argument in the line
        # Pattern: keyword_name = value (we want spaces around =)
        # We need to be careful about multiple keyword args on same line

        # Look for the keyword name followed by equals
        # keyword.arg is guaranteed to be not None due to check in visit_Call
        assert keyword.arg is not None
        keyword_pattern = rf"\b{re.escape(keyword.arg)}\s*=\s*"
        matches = list(re.finditer(keyword_pattern, line))

        if not matches:
            return

        # For each match, check if it has proper spacing
        for match in matches:
            start_pos = match.start()
            # Find the equals sign position
            equals_pos = line.find("=", start_pos)
            if equals_pos == -1:
                continue

            # Check spacing around equals sign
            has_space_before = equals_pos > 0 and line[equals_pos - 1] == " "
            has_space_after = equals_pos + 1 < len(line) and line[equals_pos + 1] == " "

            if not (has_space_before and has_space_after):
                # Calculate column position for the equals sign
                col = equals_pos
                violation_msg = f"Missing spaces around '=' in keyword argument '{keyword.arg}'"
                self.violations.append((keyword.lineno, col + 1, violation_msg))


def check_file(file_path: Path, fix: bool = False) -> List[Tuple[int, int, str]]:
    """Check a single Python file for spacing violations."""
    try:
        with open(file_path, "r", encoding = "utf-8") as f:
            content = f.read()

        source_lines = content.splitlines()

        # Parse the AST
        try:
            tree = ast.parse(content, filename = str(file_path))
        except SyntaxError as e:
            print(f"⚠️  Syntax error in {file_path}: {e}")
            return []

        # Check for violations
        checker = SpacingChecker(source_lines, str(file_path))
        checker.visit(tree)

        if fix and checker.violations:
            # Apply fixes
            fixed_content = fix_spacing_violations(content, checker.violations)
            with open(file_path, "w", encoding = "utf-8") as f:
                f.write(fixed_content)
            print(f"🔧 Fixed {len(checker.violations)} violations in {file_path}")

        return checker.violations

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return []


def fix_spacing_violations(content: str, violations: List[Tuple[int, int, str]]) -> str:
    """Fix spacing violations in the content."""
    lines = content.splitlines()

    # Process violations in reverse order to maintain line numbers
    for line_num, col, _ in sorted(violations, reverse = True):
        line_idx = line_num - 1  # Convert to 0-based
        if line_idx >= len(lines):
            continue

        line = lines[line_idx]

        # Find keyword arguments without proper spacing and fix them
        # Pattern to match: word=value or word= value or word =value
        fixed_line = re.sub(r"(\w+)\s*=\s*", r"\1 = ", line)
        lines[line_idx] = fixed_line

    return "\n".join(lines) + "\n" if content.endswith("\n") else "\n".join(lines)


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in directory, excluding common ignore patterns."""
    ignore_patterns = {".git", ".pytest_cache", "__pycache__", ".ruff_cache", "venv", ".venv", "node_modules", "build",
                       "dist"}

    python_files = []

    for path in directory.rglob("*.py"):
        # Skip if any parent directory matches ignore patterns
        if any(part in ignore_patterns for part in path.parts):
            continue
        python_files.append(path)

    return sorted(python_files)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description = "Check and fix spacing around equals signs in function call keyword arguments",
    )
    parser.add_argument(
        "paths",
        nargs = "*",
        default = ["."],
        help = "Files or directories to check (default: current directory)",
    )
    parser.add_argument("--fix", action = "store_true", help = "Automatically fix violations")
    parser.add_argument("--verbose", "-v", action = "store_true", help = "Show detailed progress information")

    args = parser.parse_args()

    all_violations = []
    files_checked = 0

    for path_str in args.paths:
        path = Path(path_str)

        if path.is_file() and path.suffix == ".py":
            # Single file
            files_to_check = [path]
        elif path.is_dir():
            # Directory
            files_to_check = find_python_files(path)
        else:
            print(f"⚠️  Skipping {path}: not a Python file or directory")
            continue

        for file_path in files_to_check:
            if args.verbose:
                print(f"Checking {file_path}...")

            violations = check_file(file_path, fix = args.fix)
            files_checked += 1

            if violations:
                all_violations.extend(violations)
                if not args.fix:  # Only show violations if not fixing
                    for line_num, col, msg in violations:
                        print(f"{file_path}:{line_num}:{col}: {msg}")

    # Summary
    if args.verbose:
        print(f"\n📊 Checked {files_checked} files")

    if all_violations:
        if args.fix:
            print(f"✅ Fixed {len(all_violations)} spacing violations")
        else:
            print(f"❌ Found {len(all_violations)} spacing violations")
            print("Run with --fix to automatically fix them")
            sys.exit(1)
    else:
        print("✅ No spacing violations found")


if __name__ == "__main__":
    main()
