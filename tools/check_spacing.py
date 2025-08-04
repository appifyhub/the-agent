"""
Custom linting script to enforce spacing rules:
1. Spaces around equals signs in function call keyword arguments: func(param = value)
2. Exactly one blank line after class declarations: class Foo:\n\n    def __init__(self):
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


class SpacingChecker(ast.NodeVisitor):
    """AST visitor to find function calls with keyword arguments and class spacing."""

    def __init__(self, source_lines: List[str], filename: str):
        self.source_lines = source_lines
        self.filename = filename
        self.violations: List[Tuple[int, int, str]] = []
        self.class_inheritance_map: dict[str, set[str]] = {}  # class_name -> set of base class names

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call nodes and check keyword argument spacing."""
        for keyword in node.keywords:
            if keyword.arg is not None:  # Skip **kwargs
                self._check_keyword_spacing(keyword)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition nodes and check for blank line after class declaration."""
        # Build inheritance map first
        self._build_inheritance_info(node)
        self._check_class_spacing(node)
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

    def _check_class_spacing(self, node: ast.ClassDef) -> None:
        """Check if a class definition has exactly one blank line after the class declaration."""
        # Skip enum classes and exception classes
        if self._is_enum_or_exception_class(node):
            return

        # Find the line with the colon (end of class declaration)
        class_start_line = node.lineno - 1  # Convert to 0-based index

        # Find the line that ends with a colon (class declaration line)
        colon_line_idx = None
        for i in range(class_start_line, min(class_start_line + 3, len(self.source_lines))):
            if i < len(self.source_lines) and self.source_lines[i].rstrip().endswith(":"):
                colon_line_idx = i
                break

        if colon_line_idx is None:
            return

        # Check if there's exactly one blank line after the class declaration
        next_line_idx = colon_line_idx + 1
        if next_line_idx >= len(self.source_lines):
            return

        # Check if the next line is a docstring (allow zero blank lines in this case)
        if next_line_idx < len(self.source_lines):
            next_line = self.source_lines[next_line_idx].strip()
            if next_line.startswith('"""') or next_line.startswith("'''"):
                return  # Docstring immediately after class is OK
            # The next line should be blank for non-docstring content
            if next_line != "":
                # No blank line after class declaration
                violation_msg = f"Expected exactly one blank line after class '{node.name}' declaration"
                self.violations.append((next_line_idx + 1, 1, violation_msg))

    def _build_inheritance_info(self, node: ast.ClassDef) -> None:
        """Build inheritance information for this class."""
        base_names = set()
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_names.add(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle cases like pydantic.BaseModel
                if isinstance(base.value, ast.Name):
                    base_names.add(f"{base.value.id}.{base.attr}")
                else:
                    base_names.add(base.attr)  # Fallback to just the attribute name
        self.class_inheritance_map[node.name] = base_names

    def _inherits_from_pydantic(self, class_name: str) -> bool:
        """Check if a class inherits from Pydantic BaseModel, either directly or transitively."""
        visited = set()

        def check_recursive(cls_name: str) -> bool:
            if cls_name in visited:
                return False  # Avoid infinite loops
            visited.add(cls_name)
            bases = self.class_inheritance_map.get(cls_name, set())

            # Check direct inheritance
            for base in bases:
                if base in {"BaseModel", "pydantic.BaseModel"}:
                    return True

            # Check transitive inheritance (only within this file)
            for base in bases:
                if base in self.class_inheritance_map and check_recursive(base):
                    return True
            return False

        return check_recursive(class_name)

    def _is_enum_or_exception_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is an enum, exception, dataclass, or Pydantic model."""
        # Check for @dataclass decorator (with or without arguments)
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                return True
            elif isinstance(decorator, ast.Call):
                # Handle @dataclass(...) with arguments
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "dataclass":
                    return True
                elif isinstance(decorator.func, ast.Attribute):
                    # Handle @dataclasses.dataclass(...)
                    if (
                        isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id == "dataclasses"
                        and decorator.func.attr == "dataclass"
                    ):
                        return True
            elif isinstance(decorator, ast.Attribute):
                # Handle cases like dataclasses.dataclass (without arguments)
                if (
                    isinstance(decorator.value, ast.Name)
                    and decorator.value.id == "dataclasses"
                    and decorator.attr == "dataclass"
                ):
                    return True

        # Check if this class inherits from Pydantic BaseModel (transitively)
        if self._inherits_from_pydantic(node.name):
            return True

        # Check base classes for enum and exception patterns
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                if base_name in {"Enum", "IntEnum", "Flag", "IntFlag", "Exception", "BaseException"}:
                    return True
                if base_name.endswith(("Error", "Exception")):
                    return True
            elif isinstance(base, ast.Attribute):
                # Handle cases like enum.Enum
                if isinstance(base.value, ast.Name) and base.value.id == "enum":
                    return True

        # Check if class name suggests it's an exception
        if node.name.endswith(("Error", "Exception")):
            return True

        return False


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

    # Separate class spacing violations from keyword spacing violations
    class_violations = []
    keyword_violations = []

    for violation in violations:
        line_num, col, msg = violation
        if "blank line after class" in msg:
            class_violations.append(violation)
        else:
            keyword_violations.append(violation)

    # Fix class spacing violations first (in reverse order to maintain line numbers)
    for line_num, col, _ in sorted(class_violations, reverse = True):
        line_idx = line_num - 1  # Convert to 0-based
        if line_idx >= 0 and line_idx < len(lines):
            # Insert a blank line before the current line
            lines.insert(line_idx, "")

    # Fix keyword spacing violations
    for line_num, col, _ in sorted(keyword_violations, reverse = True):
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
        description = "Check and fix spacing rules: equals signs in keyword arguments and blank lines after class declarations",
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
