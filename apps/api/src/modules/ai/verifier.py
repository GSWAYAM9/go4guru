"""Deterministic Math, Physics Unit, and Chemistry Stoichiometry Verifier (Module 7)."""

from __future__ import annotations

import ast
import re
from collections import Counter

import pint
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from src.modules.ai.schemas import VerificationCheckResult

_UREG = pint.UnitRegistry()

_ALLOWED_SYMPY_LOCALS: dict[str, object] = {
    "x": sp.Symbol("x"),
    "y": sp.Symbol("y"),
    "z": sp.Symbol("z"),
    "t": sp.Symbol("t"),
    "n": sp.Symbol("n"),
    "pi": sp.pi,
    "e": sp.E,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "sqrt": sp.sqrt,
    "log": sp.log,
    "exp": sp.exp,
    "Abs": sp.Abs,
    "diff": sp.diff,
    "integrate": sp.integrate,
}

_TRANSFORMS = (*standard_transformations, implicit_multiplication_application, convert_xor)

_UNSAFE_AST_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Attribute,
    ast.Lambda,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)


def _safe_normalize_math(raw: str) -> str:
    cleaned = raw.strip().replace("$", "")
    if len(cleaned) > 200:
        raise ValueError("Expression exceeds maximum safe length (200 chars).")
    if "__" in cleaned:
        raise ValueError("Dunder syntax is disallowed.")
    tree = ast.parse(cleaned.replace("^", "**"), mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, _UNSAFE_AST_NODES):
            raise ValueError(f"Disallowed AST node: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_SYMPY_LOCALS:
                raise ValueError("Disallowed function call in expression.")
    return cleaned


def _parse_safe_sympy(expr_text: str) -> sp.Expr:
    normalized = _safe_normalize_math(expr_text)
    parsed = parse_expr(
        normalized,
        local_dict=_ALLOWED_SYMPY_LOCALS,
        global_dict={
            "__builtins__": {},
            "Integer": sp.Integer,
            "Float": sp.Float,
            "Rational": sp.Rational,
            "Symbol": sp.Symbol,
        },
        transformations=_TRANSFORMS,
        evaluate=True,
    )
    if not isinstance(parsed, sp.Basic):
        raise ValueError("Parsed result is not a symbolic SymPy object.")
    return sp.sympify(parsed)


def verify_math_expression(expr_or_eq: str) -> VerificationCheckResult:
    """Safely evaluate arithmetic/algebraic expression or solve equation using SymPy."""
    raw = expr_or_eq.strip()
    if not raw:
        return VerificationCheckResult(
            verified=False,
            status="not_applicable",
            verifier_type="sympy_math",
            details="No mathematical expression supplied.",
        )

    try:
        if "=" in raw and raw.count("=") == 1:
            lhs_raw, rhs_raw = raw.split("=", 1)
            lhs = _parse_safe_sympy(lhs_raw)
            rhs = _parse_safe_sympy(rhs_raw)
            diff_expr = sp.simplify(lhs - rhs)
            if diff_expr == 0:
                return VerificationCheckResult(
                    verified=True,
                    status="verified",
                    verifier_type="sympy_math",
                    expression_or_equation=raw,
                    computed_value="Identity holds (LHS == RHS)",
                    details="Algebraic identity verified via SymPy simplify(LHS - RHS) == 0.",
                )
            free_syms = sorted(diff_expr.free_symbols, key=lambda s: str(s))
            if not free_syms:
                return VerificationCheckResult(
                    verified=False,
                    status="verification_failed",
                    verifier_type="sympy_math",
                    expression_or_equation=raw,
                    computed_value=str(diff_expr),
                    details=f"Numeric mismatch: LHS - RHS simplifies to {diff_expr}, not 0.",
                )
            sols = sp.solve(diff_expr, free_syms[0])
            return VerificationCheckResult(
                verified=True,
                status="verified",
                verifier_type="sympy_math",
                expression_or_equation=raw,
                computed_value=f"{free_syms[0]} = {[sp.simplify(s) for s in sols]}",
                details="Solved equation deterministically via SymPy.",
            )

        expr = _parse_safe_sympy(raw)
        simplified = sp.simplify(expr)
        return VerificationCheckResult(
            verified=True,
            status="verified",
            verifier_type="sympy_math",
            expression_or_equation=raw,
            computed_value=str(simplified),
            details="Expression simplified and evaluated deterministically via SymPy.",
        )
    except Exception as exc:
        return VerificationCheckResult(
            verified=False,
            status="verification_failed",
            verifier_type="sympy_math",
            expression_or_equation=raw,
            details=f"SymPy verification rejected input: {exc}",
        )


def check_algebraic_equivalence(candidate: str, expected: str) -> VerificationCheckResult:
    """Deterministically prove whether two algebraic expressions represent the same function."""
    try:
        e1 = _parse_safe_sympy(candidate)
        e2 = _parse_safe_sympy(expected)
        diff = sp.simplify(e1 - e2)
        eq = diff == 0
        return VerificationCheckResult(
            verified=bool(eq),
            status="verified" if eq else "verification_failed",
            verifier_type="sympy_math",
            expression_or_equation=f"{candidate} == {expected}",
            computed_value=str(diff),
            details="Equivalent" if eq else f"Difference simplifies to {diff}",
        )
    except Exception as exc:
        return VerificationCheckResult(
            verified=False,
            status="verification_failed",
            verifier_type="sympy_math",
            details=f"Comparison error: {exc}",
        )


def verify_physics_units(lhs_unit: str, rhs_unit: str) -> VerificationCheckResult:
    """Check SI/physical dimensional compatibility using Pint."""
    try:
        q_lhs = _UREG.Quantity(1, lhs_unit.strip())
        q_rhs = _UREG.Quantity(1, rhs_unit.strip())
        compatible = bool(q_lhs.dimensionality == q_rhs.dimensionality)
        return VerificationCheckResult(
            verified=compatible,
            status="verified" if compatible else "verification_failed",
            verifier_type="pint_physics",
            expression_or_equation=f"[{lhs_unit}] == [{rhs_unit}]",
            unit_ok=compatible,
            computed_value=str(q_lhs.dimensionality),
            details=(
                f"Dimensions match ({q_lhs.dimensionality})."
                if compatible
                else f"Dimensional mismatch: {q_lhs.dimensionality} vs {q_rhs.dimensionality}."
            ),
        )
    except Exception as exc:
        return VerificationCheckResult(
            verified=False,
            status="verification_failed",
            verifier_type="pint_physics",
            unit_ok=False,
            details=f"Pint unit check failed: {exc}",
        )


_TOKEN_RE = re.compile(r"([A-Z][a-z]?)(\d*)")
_FORMULA_COEFF_RE = re.compile(r"^(\d*)\s*(.+)$")


def _parse_species_atoms(formula: str) -> tuple[int, Counter[str]]:
    clean = formula.strip()
    m = _FORMULA_COEFF_RE.match(clean)
    if not m:
        raise ValueError(f"Invalid chemical species: {formula}")
    coeff = int(m.group(1)) if m.group(1) else 1
    body = m.group(2).strip()

    # Expand simple parenthesized groups like Ca(OH)2 -> CaO2H2 iteratively
    paren_re = re.compile(r"\(([A-Za-z0-9]+)\)(\d*)")
    while "(" in body:
        pm = paren_re.search(body)
        if not pm:
            raise ValueError(f"Unbalanced parentheses in chemical formula: {formula}")
        inner, mult_s = pm.group(1), pm.group(2)
        mult = int(mult_s) if mult_s else 1
        expanded = "".join(
            f"{el}{(int(cnt) if cnt else 1) * mult}" for el, cnt in _TOKEN_RE.findall(inner)
        )
        body = body[: pm.start()] + expanded + body[pm.end() :]

    atoms: Counter[str] = Counter()
    consumed = 0
    for match in _TOKEN_RE.finditer(body):
        if match.start() != consumed:
            raise ValueError(f"Unexpected characters in formula: {formula}")
        consumed = match.end()
        el = match.group(1)
        cnt = int(match.group(2)) if match.group(2) else 1
        atoms[el] += cnt * coeff
    if consumed != len(body) or not atoms:
        raise ValueError(f"Could not parse chemical formula: {formula}")
    return coeff, atoms


def verify_chemical_equation(equation: str) -> VerificationCheckResult:
    """Deterministically verify mass/atom conservation across reactants -> products."""
    normalized = equation.replace("→", "->").replace("=", "->")
    if "->" not in normalized:
        return VerificationCheckResult(
            verified=False,
            status="verification_failed",
            verifier_type="chem_stoichiometry",
            expression_or_equation=equation,
            details="Chemical equation must separate reactants and products with '->'.",
        )
    try:
        left_s, right_s = normalized.split("->", 1)
        left_counts: Counter[str] = Counter()
        right_counts: Counter[str] = Counter()
        for part in left_s.split("+"):
            _, atoms = _parse_species_atoms(part)
            left_counts.update(atoms)
        for part in right_s.split("+"):
            _, atoms = _parse_species_atoms(part)
            right_counts.update(atoms)

        balanced = left_counts == right_counts
        return VerificationCheckResult(
            verified=balanced,
            status="verified" if balanced else "verification_failed",
            verifier_type="chem_stoichiometry",
            expression_or_equation=equation.strip(),
            computed_value=(
                "Balanced"
                if balanced
                else f"Reactants={dict(left_counts)} vs Products={dict(right_counts)}"
            ),
            details=(
                "All element atom counts conserved across reaction arrow."
                if balanced
                else "Stoichiometry mismatch between reactants and products."
            ),
        )
    except Exception as exc:
        return VerificationCheckResult(
            verified=False,
            status="verification_failed",
            verifier_type="chem_stoichiometry",
            expression_or_equation=equation,
            details=f"Could not parse chemical equation: {exc}",
        )
