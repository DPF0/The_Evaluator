"""Static code analysis for Jupyter notebooks."""
import ast
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class CodeMetrics:
    """Static code analysis metrics."""
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    num_cells: int = 0
    num_code_cells: int = 0
    num_errors: int = 0
    num_warnings: int = 0
    cyclomatic_complexity: int = 0
    has_magic_commands: bool = False
    has_ignored_errors: bool = False
    has_print_statements: bool = False
    has_vectorized_ops: bool = False
    has_loop_patterns: bool = False
    unused_imports: list[str] = None
    style_issues: list[str] = None

    def __post_init__(self):
        if self.unused_imports is None:
            self.unused_imports = []
        if self.style_issues is None:
            self.style_issues = []


def extract_code_cells(notebook_json: dict) -> list[str]:
    """Extract all code cells from a notebook."""
    cells = notebook_json.get("cells", [])
    code_cells = []
    for cell in cells:
        if cell.get("cell_type") == "code":
            source = cell.get("source", "")
            if isinstance(source, list):
                source = "".join(str(line) for line in source)
            code_cells.append(source)
    return code_cells


def analyze_code(notebook_json: dict) -> CodeMetrics:
    """Perform static analysis on notebook code cells."""
    code_cells = extract_code_cells(notebook_json)
    metrics = CodeMetrics(
        num_cells=len(notebook_json.get("cells", [])),
        num_code_cells=len(code_cells),
    )

    all_code = "\n".join(code_cells)

    # Basic line counts
    lines = all_code.split("\n")
    metrics.total_lines = len(lines)
    for line in lines:
        stripped = line.strip()
        if not stripped:
            metrics.blank_lines += 1
        elif stripped.startswith("#"):
            metrics.comment_lines += 1
        else:
            metrics.code_lines += 1

    # Check for magic commands
    if re.search(r"^%|%matplotlib|%timeit|%load", all_code, re.MULTILINE):
        metrics.has_magic_commands = True

    # Check for ignored errors
    if re.search(r"#\s*noqa|#\s*type:\s*ignore|#\s*pyright:\s*ignore", all_code):
        metrics.has_ignored_errors = True

    # Check for print statements (may indicate debugging)
    if re.search(r"\bprint\s*\(", all_code):
        metrics.has_print_statements = True

    # Check for vectorized operations vs loops
    vectorized_patterns = [
        r"np\.(sum|mean|std|var|max|min|argmax|argmin|dot|matmul|einsum)",
        r"np\.(add|subtract|multiply|divide|power)",
        r"np\.(where|clip|round|floor|ceil)",
        r"\[.*\]\s*\.\s*reshape\(",
    ]
    loop_patterns = [
        r"\bfor\b.*\bin\b",
        r"\bwhile\b",
        r"\.append\s*\(",
    ]

    if any(re.search(p, all_code) for p in vectorized_patterns):
        metrics.has_vectorized_ops = True
    if any(re.search(p, all_code) for p in loop_patterns):
        metrics.has_loop_patterns = True

    # Parse AST for complexity and imports
    try:
        tree = ast.parse(all_code)
        metrics.cyclomatic_complexity = _calculate_complexity(tree)
        metrics.unused_imports = _find_unused_imports(tree, all_code)
        metrics.style_issues = _check_style_issues(tree, all_code)
    except SyntaxError:
        metrics.num_errors += 1
        metrics.style_issues.append("Syntax error in code")

    return metrics


def _calculate_complexity(tree: ast.AST) -> int:
    """Calculate cyclomatic complexity of the code."""
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
    return complexity


def _find_unused_imports(tree: ast.AST, code: str) -> list[str]:
    """Find potentially unused imports."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imports.append((name, alias.name))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imports.append((name, alias.name))

    unused = []
    for local_name, full_name in imports:
        # Check if the import is used in the code (excluding import statements)
        pattern = r'\b' + re.escape(local_name) + r'\b'
        matches = re.findall(pattern, code)
        if len(matches) <= 1:  # Only appears in import statement
            unused.append(full_name)
    return unused


def _check_style_issues(tree: ast.AST, code: str) -> list[str]:
    """Check for common style issues."""
    issues = []

    # Check for long lines
    for i, line in enumerate(code.split("\n"), 1):
        if len(line) > 120:
            issues.append(f"Line {i}: Line too long ({len(line)} chars)")

    # Check for multiple statements per line
    if re.search(r";.*;", code):
        issues.append("Multiple statements on same line")

    # Check for bare except
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append("Bare except clause (use specific exceptions)")

    # Check for mutable default arguments
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append(f"Mutable default argument in {node.name}")

    return issues


def format_metrics_for_llm(metrics: CodeMetrics) -> str:
    """Format metrics as text for LLM evaluation."""
    lines = [
        "## Análisis Estático del Código",
        f"- Celdas totales: {metrics.num_cells} ({metrics.num_code_cells} de código)",
        f"- Líneas de código: {metrics.code_lines}",
        f"- Complejidad ciclomática: {metrics.cyclomatic_complexity}",
    ]

    if metrics.has_vectorized_ops:
        lines.append("- ✅ Usa operaciones vectorizadas de NumPy")
    if metrics.has_loop_patterns:
        lines.append("- ⚠️  Usa bucles (posible oportunidad para vectorizar)")
    if metrics.has_print_statements:
        lines.append("- ⚠️  Usa print() (posible código de depuración)")
    if metrics.has_ignored_errors:
        lines.append("- ⚠️  Tiene errores ignorados (#noqa, #type: ignore)")

    if metrics.unused_imports:
        lines.append(f"- ❌ Imports no usados: {', '.join(metrics.unused_imports[:5])}")

    if metrics.style_issues:
        lines.append(f"- Estilo: {'; '.join(metrics.style_issues[:3])}")

    return "\n".join(lines)
