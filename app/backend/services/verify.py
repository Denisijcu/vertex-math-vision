"""Verificación con SymPy: calcula el problema por su cuenta y lo compara con la respuesta del modelo.

Qué puede verificar:
- Cuentas sin variables: 3 + 4·2, 2/3 + 1/6, √49, 15 % de 80 no (texto) → sin verificar.
- Ecuaciones de una variable: 2x + 3 = 7, x² − 5x + 6 = 0 (soluciones reales).
- Expresiones con variable y SIN signo igual: no tienen "valor de x" → "mal planteado",
  y se dice qué pasaría si se iguala a 0.

Todo lo demás (problemas de texto, relojes, gráficas, figuras) → "sin verificar": la app lo dice
en vez de fingir que comprobó algo.

SEGURIDAD: parse_expr de SymPy evalúa código. Por eso, antes de pasarle nada, el texto se limpia
y se valida con una lista blanca estricta de caracteres e identificadores. Nunca llega a SymPy
un texto con guiones bajos, comillas, corchetes, puntos de atributo ni nombres que no sean
variables de una letra o funciones permitidas.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from dataclasses import dataclass

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from services.answers import normalize, _to_number

TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
VARS = "xyzabcmnt"
FUNCS = {"sqrt": sp.sqrt}
CONSTS = {"pi": sp.pi}
LOCALS = {**{v: sp.Symbol(v, real=True) for v in VARS}, **FUNCS, **CONSTS}
ALLOWED_CHARS = re.compile(r"^[0-9a-z+\-*/^().=, ]+$")
TIMEOUT_S = 3.0
MAX_LEN = 120
_pool = ThreadPoolExecutor(max_workers=2)

NOTES = {
    "es": {
        "verified": "La calculadora comprobó el resultado.",
        "mismatch": "La calculadora obtiene otro resultado. Revisa los pasos.",
        "missing": "La calculadora encuentra más soluciones de las que dio el tutor.",
        "no_real": "No tiene solución en los números reales.",
        "ill_posed": "El ejercicio no tiene signo igual, así que x no tiene un único valor. Si lo igualamos a 0: {eq}.",
        "unverified": "Este tipo de problema no se puede comprobar con la calculadora. Revisa el resultado.",
        "steps_ok": "Las cuentas de los pasos están bien hechas, pero la calculadora no puede saber si el planteamiento es correcto (por ejemplo, si los datos se leyeron bien). Revísalo.",
        "steps_wrong": "Hay una cuenta mal en {where}: {expr} da {right}, no {claimed}. Revisa la respuesta.",
        "step_word": "el paso {n}", "check_word": "la comprobación", "steps_word": "los pasos",
    },
    "en": {
        "verified": "The calculator confirmed the result.",
        "mismatch": "The calculator gets a different result. Check the steps.",
        "missing": "The calculator finds more solutions than the tutor gave.",
        "no_real": "It has no solution in the real numbers.",
        "ill_posed": "The exercise has no equals sign, so x has no single value. If we set it equal to 0: {eq}.",
        "unverified": "This kind of problem can't be checked with the calculator. Review the result.",
        "steps_ok": "The arithmetic in the steps is correct, but the calculator can't tell whether the setup is right (for example, whether the data was read correctly). Check it.",
        "steps_wrong": "There's an arithmetic mistake in {where}: {expr} is {right}, not {claimed}. Review the answer.",
        "step_word": "step {n}", "check_word": "the check", "steps_word": "the steps",
    },
}


@dataclass
class Check:
    status: str                    # verified | mismatch | ill_posed | unverified
    sympy_answer: str | None = None
    note: str | None = None


# ───────────────────────── limpieza del texto ─────────────────────────

_REPL = [
    ("−", "-"), ("–", "-"), ("—", "-"), ("×", "*"), ("·", "*"), ("÷", "/"), ("∶", "/"),
    ("²", "^2"), ("³", "^3"), ("π", "pi"), ("√", "sqrt"), ("\\cdot", "*"), ("\\times", "*"),
    ("\\div", "/"), ("\\left", ""), ("\\right", ""), ("\\pi", "pi"), ("$", ""), ("{", "("), ("}", ")"),
]


def _latex_bits(s: str) -> str:
    s = re.sub(r"\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"((\1)/(\2))", s)
    s = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt(\1)", s)
    return s


def clean_math(s: str) -> str:
    s = _latex_bits(s or "")
    for a, b in _REPL:
        s = s.replace(a, b)
    s = s.lower()
    s = re.sub(r"sqrt\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", s)       # √49 → sqrt(49)
    s = re.sub(r"(?<=\d),(?=\d{1,2}\b)", ".", s)                 # 12,5 → 12.5
    s = re.sub(r"\s+", " ", s).strip(" .,:;?¿!¡")
    return s


def _identifiers_ok(s: str) -> bool:
    for word in re.findall(r"[a-z]+", s):
        if word in FUNCS or word in CONSTS:
            continue
        if not all(ch in VARS for ch in word):     # "xy" vale (se separa en x·y); "exec", "os"… no
            return False
    return True


def _safe(s: str) -> bool:
    if not s or len(s) > MAX_LEN or "__" in s or not ALLOWED_CHARS.match(s):
        return False
    if not _identifiers_ok(s):
        return False
    if s.count("=") > 1:
        return False
    # potencias gigantes (9^9^9) colgarían el servidor
    if re.search(r"\^\s*\(?\s*\d{3,}", s) or re.search(r"\^[^=]*\^", s):
        return False
    return any(ch.isdigit() for ch in s)


def extract_candidate(problem: str) -> str | None:
    """De la transcripción saca la línea con pinta de cuenta o ecuación (sin palabras)."""
    lines = [clean_math(l) for l in re.split(r"[\n;]|(?<=[?.])\s", problem or "") if l.strip()]
    best = None
    for line in lines:
        # quitar la numeración "1)" / "2." y todo lo que va antes de ":" ("1) Resuelve: x^2 + …")
        line = re.sub(r"^\s*\d+\s*(?:\)|\.(?!\d))\s*", "", line)
        if ":" in line:
            line = line.rsplit(":", 1)[1]
        # quitar palabras sueltas al inicio: "resuelve", "solve", "calcula", "cuánto vale x"
        line = re.sub(r"^[^0-9a-z(√-]*", "", line)
        line = re.sub(r"^(?:(?!sqrt|pi\b)[a-zñáéíóú]{3,}\s*:?\s*)+", "", line).strip()
        # "20 - 10 =", "15 - 3 = ?", "7 x 8 = ___": el hueco de la respuesta no es parte de la cuenta
        line = re.sub(r"\s*=\s*[?¿_.…□]*\s*$", "", line).strip()
        if _safe(line) and re.search(r"[+\-*/^=]|sqrt", line):
            if best is None or ("=" in line and "=" not in best) or len(line) > len(best):
                best = line
    return best


# ───────────────────────── cálculo con SymPy ─────────────────────────

def _parse(expr: str):
    return parse_expr(expr, local_dict=LOCALS, global_dict={"Integer": sp.Integer, "Float": sp.Float,
                                                            "Rational": sp.Rational, "Symbol": sp.Symbol,
                                                            "Function": sp.Function, "sqrt": sp.sqrt, "pi": sp.pi},
                      transformations=TRANSFORMS, evaluate=True)


def _run(fn, *args):
    return _pool.submit(fn, *args).result(timeout=TIMEOUT_S)


def _fmt(v) -> str:
    if v.is_Float:
        return f"{float(v):.6g}"
    if v.is_Integer or (v.is_Rational and not v.is_Integer):
        return str(v)
    return f"{sp.N(v, 6)}".rstrip("0").rstrip(".") if v.is_number else str(v)


def _solve(expr: str):
    """Devuelve ('value', número) | ('solutions', [números reales]) | ('no_eq', expresión, variable)."""
    if "=" in expr:
        left, right = expr.split("=")
        eq = _parse(left) - _parse(right)
        free = sorted(eq.free_symbols, key=str)
        if len(free) != 1:
            return ("unsupported",)
        sols = sp.solveset(eq, free[0], domain=sp.S.Reals)
        if sols == sp.S.EmptySet:
            return ("solutions", [])
        if not isinstance(sols, sp.FiniteSet):
            return ("unsupported",)
        return ("solutions", sorted(sols, key=lambda z: float(z)))
    val = _parse(expr)
    free = sorted(val.free_symbols, key=str)
    if not free:
        return ("value", sp.nsimplify(val) if val.is_Float else sp.simplify(val))
    if len(free) == 1:
        sols = sp.solveset(sp.Eq(val, 0), free[0], domain=sp.S.Reals)
        return ("no_eq", sp.expand(val), free[0], sols)
    return ("unsupported",)


# ───────────────────────── comparación con el modelo ─────────────────────────

NO_SOLUTION_WORDS = re.compile(r"no\s+existe|does\s+not\s+exist|no\s+(tiene\s+)?(hay\s+)?soluci|sin\s+soluci|no\s+real|no\s+solution|∅|\\emptyset|ninguna", re.I)


def _model_values(answer: str) -> list[tuple[float, int]] | None:
    """Números de la respuesta del modelo, con cuántos decimales escribió cada uno (para tolerar el redondeo)."""
    if answer is None:
        return None
    answer = re.sub(r"\\(?:text|mathrm)\s*\{([^{}]*)\}", r" \1 ", answer)   # "2 \text{ o } 3" → "2  o  3"
    parts = re.split(r",\s+|;|\s+(?:o|or|y|and)\s+|\\pm", answer)
    vals = []
    for p in parts:
        norm = normalize(p)
        n = _to_number(norm)
        if n is None:
            continue
        m = re.search(r"[.,](\d+)$", norm)
        vals.append((float(n), len(m.group(1)) if m else 0))
    return vals or None


def _close(m: tuple[float, int], b: float) -> bool:
    a, decimals = m
    tol = max(1e-6 * max(1.0, abs(b)), 0.5 * 10 ** -decimals if decimals else 0)
    return abs(a - b) <= tol


# ───────────────────────── cuentas dentro de los pasos ─────────────────────────

_NUM_TAIL = re.compile(r"[0-9.()\s+\-*/^]+$")
_NUM_HEAD = re.compile(r"^[0-9.()\s+\-*/^]+")
_STEP_LABEL = re.compile(r"^\s*\*\*\s*(paso|step)\s*(\d+)|^\s*\*\*\s*(comprobaci[oó]n|check)", re.I)


@dataclass
class StepIssue:
    where: str
    expr: str
    claimed: str
    right: str


def _numeric_ok(expr: str) -> bool:
    if not expr or len(expr) > MAX_LEN or not re.search(r"\d", expr):
        return False
    if re.search(r"\^\s*\(?\s*\d{3,}", expr) or re.search(r"\^[^=]*\^", expr):
        return False
    return expr.count("(") == expr.count(")")


def _equalities(line: str) -> list[tuple[str, str]]:
    """Pares (cuenta, resultado) solo con números: "120 - 40 = 80", "2^2 - 5*2 + 6 = 0".
    Se ignora todo lo que lleve letras pegadas (2x + 3 = 7) para no confundir ecuaciones con cuentas."""
    text = clean_math(re.sub(r"\*\*[^*]*\*\*", " ", line))      # fuera las etiquetas "**Paso 1:**"
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)          # 1,250 → 1250
    parts = text.split("=")
    pairs = []
    for left, right in zip(parts, parts[1:]):
        lm, rm = _NUM_TAIL.search(left), _NUM_HEAD.search(right)
        if not lm or not rm:
            continue
        # carácter PEGADO a la cuenta (sin espacio en medio): "2x+3" y "3:45" no son cuentas sueltas;
        # "Resto: 120 - 40" o "arrived 80 + 25" sí (hay un espacio).
        g = lm.group()
        start = lm.start() + (len(g) - len(g.lstrip()))
        h = rm.group()
        end = rm.start() + len(h.rstrip())
        before, after = left[:start], right[end:]
        if before and (before[-1].isalnum() or before[-1] in ")^:"):
            continue                                            # "2x+3", "3:45 + 15" → no es una cuenta suelta
        if after and (after[0].isalpha() or after[0] in "(^:"):
            continue                                            # "= 4x", "= 4:00" → no es un número suelto
        expr, value = lm.group().strip(), rm.group().strip()
        if not re.match(r"[\d(]", expr):
            continue                                            # "- 3 + 4" (resto de "2x - 3 + 4"): incompleta
        if not re.search(r"\d\s*[+\-*/^]\s*[\d(]", expr) or not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
            continue                                            # tiene que haber una operación de verdad
        if _numeric_ok(expr):
            pairs.append((expr, value))
    return pairs


def check_steps(steps: str, lang: str = "es") -> tuple[int, StepIssue | None, list[float]]:
    """Revisa las cuentas numéricas de los pasos. Devuelve (cuántas revisó, primer error o None, resultados)."""
    notes = NOTES[lang]
    where = notes["steps_word"]
    checked = 0
    results: list[float] = []
    for line in (steps or "").splitlines():
        m = _STEP_LABEL.match(line)
        if m:
            where = notes["step_word"].format(n=m.group(2)) if m.group(2) else notes["check_word"]
        if re.search(r"\*\*\s*(respuesta|answer)", line, re.I):
            continue
        for expr, claimed in _equalities(line):
            try:
                val = _run(lambda e=expr: _parse(e))
            except Exception:
                continue
            if not (val.is_real and val.is_finite):
                continue
            checked += 1
            decimals = len(claimed.split(".")[1]) if "." in claimed else 0
            if not _close((float(claimed), decimals), float(val)):
                return checked, StepIssue(where, expr.replace("**", "^"), claimed, _fmt(sp.nsimplify(val) if val.is_Float else val)), results
            results.append(float(val))
    return checked, None, results


def check(problem: str, model_answer: str | None, lang: str = "es", steps: str = "") -> Check:
    """Verifica el problema y, si no se puede, revisa al menos las cuentas de los pasos."""
    result = _check_problem(problem, model_answer, lang)
    if result.status not in ("unverified", "mismatch") or not steps:
        return result
    notes = NOTES[lang]
    checked, issue, results = check_steps(steps, lang)
    if issue:
        msg = notes["steps_wrong"].format(where=issue.where, expr=issue.expr, right=issue.right, claimed=issue.claimed)
        if result.status == "mismatch":
            return Check("mismatch", result.sympy_answer, f"{result.note} {msg}")
        return Check("steps_wrong", None, msg)
    # "Cuentas correctas" solo si la respuesta final sale de una de esas cuentas. Si el modelo calcula
    # 5, 6 y 7 pero contesta 4, las cuentas están bien sumadas pero no respaldan nada: sin verificar.
    answers = _model_values(model_answer) or []
    backed = any(_close(a, r) for a in answers for r in results)
    if result.status == "unverified" and checked and backed:
        return Check("steps_ok", None, notes["steps_ok"])
    return result


def _check_problem(problem: str, model_answer: str | None, lang: str = "es") -> Check:
    notes = NOTES[lang]
    cand = extract_candidate(problem)
    if cand is None:
        return Check("unverified", note=notes["unverified"])
    try:
        res = _run(_solve, cand)
    except (FutTimeout, Exception):
        return Check("unverified", note=notes["unverified"])

    kind = res[0]
    if kind == "unsupported":
        return Check("unverified", note=notes["unverified"])

    if kind == "no_eq":
        expr, var, sols = res[1], res[2], res[3]
        eq_txt = f"{sp.sstr(expr)} = 0 → " + (
            (notes["no_real"].rstrip(".").lower()) if sols == sp.S.EmptySet
            else f"{var} = " + ", ".join(_fmt(s) for s in sols) if isinstance(sols, sp.FiniteSet) else "?"
        )
        return Check("ill_posed", sympy_answer=None, note=notes["ill_posed"].format(eq=eq_txt.replace("**", "^")))

    if kind == "value":
        val = res[1]
        if not (val.is_real and val.is_finite):     # 1/0, raíz de negativo…
            return Check("unverified", note=notes["unverified"])
        sym = _fmt(sp.Float(val)) if "." in cand and not val.is_Integer else _fmt(val)
        mv = _model_values(model_answer)
        if mv and len(mv) == 1 and _close(mv[0], float(val)):
            return Check("verified", sym, notes["verified"])
        return Check("mismatch", sym, notes["mismatch"])

    # ecuación
    sols = res[1]
    if not sols:
        if model_answer and NO_SOLUTION_WORDS.search(model_answer):
            return Check("verified", notes["no_real"], notes["verified"])
        return Check("mismatch", notes["no_real"], notes["mismatch"] + " " + notes["no_real"])
    sym = ", ".join(_fmt(s) for s in sols)
    mv = _model_values(model_answer)
    if not mv:
        return Check("mismatch", sym, notes["mismatch"])
    target = [float(s) for s in sols]
    if not all(any(_close(m, t) for t in target) for m in mv):
        return Check("mismatch", sym, notes["mismatch"])
    if not all(any(_close(m, t) for m in mv) for t in target):
        return Check("mismatch", sym, notes["missing"])
    return Check("verified", sym, notes["verified"])
