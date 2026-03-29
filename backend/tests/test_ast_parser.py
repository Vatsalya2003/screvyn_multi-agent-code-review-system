"""
Tests for the tree-sitter AST parser.

These tests are FAST (no API calls) — they only test parsing logic.
Run: pytest tests/test_ast_parser.py -v

What we test:
  - Python: functions, classes, methods, imports, parameters
  - JavaScript: regular functions, arrow functions, class methods, imports
  - Java: methods, class declarations, imports
  - Edge cases: empty files, syntax errors, unsupported languages
  - Context string generation (what agents actually receive)
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.ast_parser import parse_code, get_supported_languages


def load_fixture(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "fixtures", name)
    with open(path) as f:
        return f.read()


# ─── Python parsing tests ────────────────────────────────────


class TestPythonParsing:

    def test_extracts_functions(self):
        code = """
def hello():
    pass

def greet(name, age):
    return f"Hi {name}"
"""
        result = parse_code(code, "python")
        names = [f.name for f in result.functions]
        assert "hello" in names
        assert "greet" in names

    def test_extracts_function_parameters(self):
        code = """
def process(items, batch_size, verbose):
    pass
"""
        result = parse_code(code, "python")
        assert len(result.functions) == 1
        fn = result.functions[0]
        assert fn.name == "process"
        assert "items" in fn.parameters
        assert "batch_size" in fn.parameters
        assert "verbose" in fn.parameters

    def test_skips_self_parameter(self):
        code = """
class Foo:
    def bar(self, x, y):
        pass
"""
        result = parse_code(code, "python")
        methods = [f for f in result.functions if f.name == "bar"]
        assert len(methods) == 1
        assert "self" not in methods[0].parameters
        assert "x" in methods[0].parameters
        assert "y" in methods[0].parameters

    def test_extracts_classes(self):
        code = """
class UserService:
    def get_user(self):
        pass
    def delete_user(self):
        pass

class OrderService:
    def create_order(self):
        pass
"""
        result = parse_code(code, "python")
        class_names = [c.name for c in result.classes]
        assert "UserService" in class_names
        assert "OrderService" in class_names

    def test_class_methods_tracked(self):
        code = """
class UserService:
    def get_user(self):
        pass
    def delete_user(self):
        pass
"""
        result = parse_code(code, "python")
        user_service = [c for c in result.classes if c.name == "UserService"][0]
        assert "get_user" in user_service.methods
        assert "delete_user" in user_service.methods

    def test_methods_have_parent_class(self):
        code = """
class MyClass:
    def my_method(self):
        pass
"""
        result = parse_code(code, "python")
        method = [f for f in result.functions if f.name == "my_method"][0]
        assert method.parent_class == "MyClass"

    def test_top_level_function_has_no_parent(self):
        code = """
def standalone():
    pass
"""
        result = parse_code(code, "python")
        fn = result.functions[0]
        assert fn.parent_class is None

    def test_extracts_imports(self):
        code = """
import sqlite3
import os
from pathlib import Path
from typing import Optional
"""
        result = parse_code(code, "python")
        modules = [imp.module for imp in result.imports]
        assert "sqlite3" in modules
        assert "os" in modules

    def test_line_numbers_correct(self):
        code = """
import os

def first():
    pass

def second():
    pass
"""
        result = parse_code(code, "python")
        first_fn = [f for f in result.functions if f.name == "first"][0]
        second_fn = [f for f in result.functions if f.name == "second"][0]
        # first() starts before second()
        assert first_fn.start_line < second_fn.start_line

    def test_total_lines_counted(self):
        code = "line1\nline2\nline3\nline4\nline5\n"
        result = parse_code(code, "python")
        assert result.total_lines == 5

    def test_vulnerable_fixture_parses(self):
        """Our real test fixture should parse without errors."""
        code = load_fixture("vulnerable.py")
        result = parse_code(code, "python")
        assert len(result.functions) >= 3  # get_user, get_all_orders, process_data, etc.
        assert len(result.classes) >= 1    # UserManager
        assert len(result.imports) >= 1    # sqlite3, os, etc.
        assert result.has_errors is False


# ─── JavaScript parsing tests ────────────────────────────────


class TestJavaScriptParsing:

    def test_regular_function(self):
        code = "function greet(name) { return 'hi ' + name; }"
        result = parse_code(code, "javascript")
        assert len(result.functions) >= 1
        names = [f.name for f in result.functions]
        assert "greet" in names

    def test_arrow_function(self):
        code = "const add = (a, b) => a + b;"
        result = parse_code(code, "javascript")
        # Arrow functions assigned to variables
        names = [f.name for f in result.functions]
        assert "add" in names or len(result.functions) >= 1

    def test_class_methods(self):
        code = """
class UserController {
    handleLogin(req, res) {
        return res.send('ok');
    }
    handleLogout(req, res) {
        return res.send('bye');
    }
}
"""
        result = parse_code(code, "javascript")
        class_names = [c.name for c in result.classes]
        assert "UserController" in class_names

    def test_vulnerable_fixture_parses(self):
        code = load_fixture("vulnerable.js")
        result = parse_code(code, "javascript")
        assert len(result.functions) >= 2
        assert result.total_lines > 0


# ─── Java parsing tests ──────────────────────────────────────


class TestJavaParsing:

    def test_class_and_methods(self):
        code = """
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
    public int subtract(int a, int b) {
        return a - b;
    }
}
"""
        result = parse_code(code, "java")
        class_names = [c.name for c in result.classes]
        assert "Calculator" in class_names
        fn_names = [f.name for f in result.functions]
        assert "add" in fn_names
        assert "subtract" in fn_names

    def test_imports(self):
        code = """
import java.util.List;
import java.sql.Connection;

public class App {
    public void run() {}
}
"""
        result = parse_code(code, "java")
        assert len(result.imports) >= 2

    def test_vulnerable_fixture_parses(self):
        code = load_fixture("vulnerable.java")
        result = parse_code(code, "java")
        assert len(result.classes) >= 1
        assert len(result.functions) >= 2


# ─── Edge cases ──────────────────────────────────────────────


class TestEdgeCases:

    def test_empty_code(self):
        result = parse_code("", "python")
        assert result.total_lines == 0
        assert result.functions == []
        assert result.classes == []

    def test_syntax_error_still_parses(self):
        """tree-sitter is error-tolerant — it should still extract what it can."""
        code = """
def valid_function():
    pass

def broken(
    # missing closing paren and body

def another_valid():
    return 42
"""
        result = parse_code(code, "python")
        # Should still find at least the valid functions
        names = [f.name for f in result.functions]
        assert "valid_function" in names

    def test_unsupported_language(self):
        """Unsupported language should return empty result, not crash."""
        result = parse_code("fn main() {}", "rust")
        assert result.language == "rust"
        assert result.functions == []
        assert result.classes == []

    def test_single_line_code(self):
        code = "x = 1"
        result = parse_code(code, "python")
        assert result.total_lines == 1


# ─── Context string tests ────────────────────────────────────


class TestContextString:

    def test_context_includes_functions(self):
        code = """
def hello(name):
    pass
"""
        result = parse_code(code, "python")
        context = result.to_context_string()
        assert "hello" in context
        assert "name" in context

    def test_context_includes_classes(self):
        code = """
class MyService:
    def do_thing(self):
        pass
"""
        result = parse_code(code, "python")
        context = result.to_context_string()
        assert "MyService" in context
        assert "do_thing" in context

    def test_context_includes_imports(self):
        code = "import sqlite3\nimport os\n"
        result = parse_code(code, "python")
        context = result.to_context_string()
        assert "sqlite3" in context
        assert "os" in context

    def test_full_fixture_context(self):
        """The context for our vulnerable fixture should be rich and informative."""
        code = load_fixture("vulnerable.py")
        result = parse_code(code, "python")
        context = result.to_context_string()

        print(f"\n--- Context string for vulnerable.py ---\n{context}\n---")

        assert "python" in context.lower()
        assert "get_user" in context
        assert "UserManager" in context
        assert "sqlite3" in context
