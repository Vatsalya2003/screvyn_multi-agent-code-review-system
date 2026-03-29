"""
AST Parser — extracts code structure using tree-sitter.

What this does:
    Takes raw source code → parses it into a syntax tree → extracts
    functions, classes, imports, and their line ranges → returns a
    structured summary that agents can use for better analysis.

Why tree-sitter?
    - Same parser used by VS Code and GitHub for syntax highlighting
    - Extremely fast: parses 10,000 lines in <50ms
    - Error-tolerant: still produces a tree even with syntax errors
    - Supports 50+ languages with the same API

How agents use this:
    Instead of just sending raw code to Gemini, we send:
    "This file has 3 functions: get_user (lines 10-15), get_orders
    (lines 17-30), process_payment (lines 32-50). It imports sqlite3
    and os. The class UserManager has 6 methods."

    This context helps the agent give more specific, accurate findings.

Supported languages (Phase 3):
    - Python  (tree-sitter-python)
    - JavaScript (tree-sitter-javascript)
    - Java (tree-sitter-java)

Adding a new language takes ~15 minutes — you just need to:
    1. pip install tree-sitter-{language}
    2. Add the language to LANGUAGE_CONFIGS
    3. Map its node types (function names, class names, etc.)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from tree_sitter import Language, Parser

logger = logging.getLogger(__name__)


# ─── Data Models ─────────────────────────────────────────────
#
# These dataclasses hold the extracted structure. They're simpler
# than Pydantic models because they're internal — only used between
# the parser and the agents, never sent over HTTP.
#


@dataclass
class FunctionInfo:
    """A function or method extracted from the AST."""
    name: str
    start_line: int
    end_line: int
    parameters: list[str] = field(default_factory=list)
    # Which class this method belongs to (None if top-level function)
    parent_class: Optional[str] = None


@dataclass
class ClassInfo:
    """A class extracted from the AST."""
    name: str
    start_line: int
    end_line: int
    methods: list[str] = field(default_factory=list)


@dataclass
class ImportInfo:
    """An import statement extracted from the AST."""
    module: str
    line: int


@dataclass
class ParseResult:
    """
    Complete AST parse result for a source file.

    This is what the parser returns and what agents consume.
    """
    language: str
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    total_lines: int = 0
    # True if tree-sitter found syntax errors (it still parses!)
    has_errors: bool = False

    def to_context_string(self) -> str:
        """
        Convert the parse result into a human-readable summary
        that gets appended to the agent's prompt.

        This is THE key function — it's what bridges AST parsing
        and LLM analysis. The format is designed to be:
        - Concise (doesn't waste tokens)
        - Informative (gives agents real structural insight)
        - Actionable (line numbers let agents pinpoint issues)
        """
        parts = []
        parts.append(f"Language: {self.language}")
        parts.append(f"Total lines: {self.total_lines}")

        if self.imports:
            module_names = [imp.module for imp in self.imports]
            parts.append(f"Imports: {', '.join(module_names)}")

        if self.functions:
            parts.append(f"\nFunctions ({len(self.functions)}):")
            for fn in self.functions:
                params = ", ".join(fn.parameters) if fn.parameters else "none"
                prefix = f"  {fn.parent_class}." if fn.parent_class else "  "
                parts.append(
                    f"{prefix}{fn.name}({params}) — lines {fn.start_line}-{fn.end_line}"
                )

        if self.classes:
            parts.append(f"\nClasses ({len(self.classes)}):")
            for cls in self.classes:
                methods = ", ".join(cls.methods) if cls.methods else "none"
                parts.append(
                    f"  {cls.name} (lines {cls.start_line}-{cls.end_line}) — "
                    f"methods: {methods}"
                )

        if self.has_errors:
            parts.append("\nNote: Source contains syntax errors (partial parse)")

        return "\n".join(parts)


# ─── Language Configuration ──────────────────────────────────
#
# Each language has different node type names in tree-sitter.
# Python calls a function "function_definition", JavaScript calls
# it "function_declaration" or "arrow_function", Java calls it
# "method_declaration". This config maps the abstract concepts
# (function, class, import) to each language's specific names.
#
# To add a new language:
#   1. Install: pip install tree-sitter-{lang}
#   2. Add an entry to LANGUAGE_CONFIGS below
#   3. Add the get_language call to _get_language()
#   4. That's it — the parser handles the rest
#

LANGUAGE_CONFIGS = {
    "python": {
        "function_types": ["function_definition"],
        "class_types": ["class_definition"],
        "import_types": ["import_statement", "import_from_statement"],
        # How to find the function/class name in the AST node
        "name_child_type": "identifier",
        # How to find function parameters
        "params_node_type": "parameters",
        "param_child_type": "identifier",
    },
    "javascript": {
        "function_types": [
            "function_declaration",      # function foo() {}
            "arrow_function",            # const foo = () => {}
            "method_definition",         # class method
        ],
        "class_types": ["class_declaration"],
        "import_types": ["import_statement"],
        "name_child_type": "identifier",
        "params_node_type": "formal_parameters",
        "param_child_type": "identifier",
    },
    "java": {
        "function_types": ["method_declaration", "constructor_declaration"],
        "class_types": ["class_declaration"],
        "import_types": ["import_declaration"],
        "name_child_type": "identifier",
        "params_node_type": "formal_parameters",
        "param_child_type": "identifier",
    },
}


def _get_language(lang_name: str) -> Optional[Language]:
    """
    Load the tree-sitter Language object for a given language.

    Why a function instead of a dict? Because importing the language
    modules has a startup cost. We only import what's needed.
    """
    try:
        if lang_name == "python":
            import tree_sitter_python
            return Language(tree_sitter_python.language())
        elif lang_name == "javascript":
            import tree_sitter_javascript
            return Language(tree_sitter_javascript.language())
        elif lang_name == "java":
            import tree_sitter_java
            return Language(tree_sitter_java.language())
        else:
            logger.warning("Unsupported language: %s", lang_name)
            return None
    except ImportError:
        logger.error("tree-sitter grammar not installed for: %s", lang_name)
        return None


def _extract_node_text(node, source_bytes: bytes) -> str:
    """
    Get the text content of an AST node.

    tree-sitter works with byte offsets, not character offsets.
    This converts the node's byte range back to a string.
    """
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _find_child_by_type(node, child_type: str):
    """Find the first direct child node of a specific type."""
    for child in node.children:
        if child.type == child_type:
            return child
    return None


def _find_children_by_type(node, child_type: str) -> list:
    """Find all direct children of a specific type."""
    return [child for child in node.children if child.type == child_type]


def _extract_name(node, config: dict, source_bytes: bytes) -> str:
    """
    Extract the name of a function, class, or method from its AST node.

    For most languages, the name is in a child node of type "identifier".
    For JavaScript arrow functions assigned to variables, the name is in
    the parent node (the variable declarator).
    """
    name_child = _find_child_by_type(node, config["name_child_type"])
    if name_child:
        return _extract_node_text(name_child, source_bytes)

    # JavaScript class methods use property_identifier for the name
    name_child = _find_child_by_type(node, "property_identifier")
    if name_child:
        return _extract_node_text(name_child, source_bytes)

    # JavaScript arrow functions: const foo = () => {}
    # The name is in the variable_declarator parent, not the arrow_function
    if node.type == "arrow_function" and node.parent:
        if node.parent.type == "variable_declarator":
            name_node = _find_child_by_type(node.parent, "identifier")
            if name_node:
                return _extract_node_text(name_node, source_bytes)

    return "<anonymous>"


def _extract_parameters(node, config: dict, source_bytes: bytes) -> list[str]:
    """
    Extract parameter names from a function node.

    Finds the parameters/formal_parameters child, then extracts
    all identifier children from it.
    """
    params_node = _find_child_by_type(node, config["params_node_type"])
    if not params_node:
        return []

    params = []
    for child in params_node.children:
        if child.type == config["param_child_type"]:
            param_name = _extract_node_text(child, source_bytes)
            # Skip 'self' and 'cls' in Python — they're noise
            if param_name not in ("self", "cls"):
                params.append(param_name)
        # Handle typed parameters (Java: "int count", Python: "x: int")
        elif child.type in ("typed_parameter", "formal_parameter"):
            id_node = _find_child_by_type(child, "identifier")
            if id_node:
                param_name = _extract_node_text(id_node, source_bytes)
                if param_name not in ("self", "cls"):
                    params.append(param_name)
    return params


def _extract_import_module(node, source_bytes: bytes, lang: str) -> str:
    """
    Extract the module name from an import statement.

    Python:     import sqlite3        → "sqlite3"
                from os import path   → "os"
    JavaScript: import X from 'Y'    → "Y"
    Java:       import java.util.List → "java.util.List"
    """
    if lang == "python":
        # "import X" → look for dotted_name or identifier child
        for child in node.children:
            if child.type in ("dotted_name", "identifier"):
                return _extract_node_text(child, source_bytes)
    elif lang == "javascript":
        # import ... from 'module-name'
        string_node = _find_child_by_type(node, "string")
        if string_node:
            text = _extract_node_text(string_node, source_bytes)
            return text.strip("'\"")
    elif lang == "java":
        # import java.util.List;
        scoped = _find_child_by_type(node, "scoped_identifier")
        if scoped:
            return _extract_node_text(scoped, source_bytes)

    # Fallback: return the full text of the import node
    return _extract_node_text(node, source_bytes).strip()


def _walk_tree(node, config: dict, source_bytes: bytes, lang: str, result: ParseResult, parent_class: Optional[str] = None):
    """
    Recursively walk the AST tree and extract structures.

    This is the core algorithm. It visits every node in the tree:
    - If the node is a function → extract it into result.functions
    - If the node is a class → extract it into result.classes,
      then walk its children to find methods
    - If the node is an import → extract it into result.imports
    - If the node has an ERROR type → mark has_errors

    Why recursive? Because code is nested. A method is inside a class,
    a function can be inside another function. The tree structure
    naturally captures this nesting.
    """
    # Check for syntax errors
    if node.type == "ERROR":
        result.has_errors = True

    # ── Functions ────────────────────────────────────────
    if node.type in config["function_types"]:
        name = _extract_name(node, config, source_bytes)
        params = _extract_parameters(node, config, source_bytes)
        fn_info = FunctionInfo(
            name=name,
            start_line=node.start_point[0] + 1,  # tree-sitter is 0-indexed
            end_line=node.end_point[0] + 1,
            parameters=params,
            parent_class=parent_class,
        )
        result.functions.append(fn_info)

        # If this is a method inside a class, add to the class's method list
        if parent_class:
            for cls in result.classes:
                if cls.name == parent_class:
                    cls.methods.append(name)

        # Don't recurse into functions to find nested functions
        # (keeps the output clean — nested functions are rare)
        return

    # ── Classes ──────────────────────────────────────────
    if node.type in config["class_types"]:
        name = _extract_name(node, config, source_bytes)
        cls_info = ClassInfo(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
        )
        result.classes.append(cls_info)

        # Recurse into the class body to find methods
        for child in node.children:
            _walk_tree(child, config, source_bytes, lang, result, parent_class=name)
        return

    # ── Imports ──────────────────────────────────────────
    if node.type in config["import_types"]:
        module = _extract_import_module(node, source_bytes, lang)
        result.imports.append(ImportInfo(
            module=module,
            line=node.start_point[0] + 1,
        ))
        # Imports don't have children to recurse into
        return

    # ── Everything else: recurse into children ───────────
    for child in node.children:
        _walk_tree(child, config, source_bytes, lang, result, parent_class)


# ─── Public API ──────────────────────────────────────────────


def parse_code(code: str, language: str) -> ParseResult:
    """
    Parse source code and extract its structure.

    This is the main entry point — the function agents call.
    Like analyze_security(), it NEVER crashes. If parsing fails,
    it returns an empty ParseResult.

    Args:
        code: Source code as a string
        language: Programming language ("python", "javascript", "java")

    Returns:
        ParseResult with functions, classes, imports, and metadata
    """
    result = ParseResult(
        language=language,
        total_lines=len(code.splitlines()),
    )

    # Check if we support this language
    config = LANGUAGE_CONFIGS.get(language)
    if not config:
        logger.warning(
            "No AST config for language '%s'. "
            "Supported: %s. Returning empty parse result.",
            language, list(LANGUAGE_CONFIGS.keys()),
        )
        return result

    # Load the tree-sitter language grammar
    ts_language = _get_language(language)
    if not ts_language:
        return result

    try:
        # Create parser and parse the code
        parser = Parser(ts_language)
        source_bytes = code.encode("utf-8")
        tree = parser.parse(source_bytes)

        # Walk the tree and extract structures
        _walk_tree(tree.root_node, config, source_bytes, language, result)

        logger.info(
            "AST parsed %s: %d functions, %d classes, %d imports, %d lines",
            language,
            len(result.functions),
            len(result.classes),
            len(result.imports),
            result.total_lines,
        )

    except Exception as e:
        logger.error("AST parsing failed for %s: %s", language, str(e)[:200])
        result.has_errors = True

    return result


def get_supported_languages() -> list[str]:
    """Return list of languages we can parse."""
    return list(LANGUAGE_CONFIGS.keys())
