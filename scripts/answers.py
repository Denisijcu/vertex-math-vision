"""Extracción y comparación de respuestas — la MISMA lógica para la base y para el LoRA.

Formatos que entiende: enteros, decimales (punto o coma), fracciones (a/b o \\frac{a}{b}),
múltiplos de pi (25\\pi, 25π, 25pi), horas (3:45) y letras de opción (A–E).
"""
import re
from fractions import Fraction

_BOX = re.compile(r"\\boxed\s*\{")


def extract_boxed(text: str):
    """Devuelve el contenido del ÚLTIMO \\boxed{...}, respetando llaves anidadas."""
    text = str(text or "")
    starts = [m.end() for m in _BOX.finditer(text)]
    if not starts:
        return None
    i = starts[-1]
    depth, out = 1, []
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return "".join(out).strip()
        out.append(c)
        i += 1
    return None


def extract_answer(text: str):
    """\\boxed primero; si no hay, la línea de 'Respuesta:' / 'Answer:'."""
    b = extract_boxed(text)
    if b is not None:
        return b
    m = re.findall(r"(?i)(?:respuesta(?: final)?|final answer|answer)\s*[:=]\s*(.+)", str(text or ""))
    if m:
        return m[-1].splitlines()[0].strip().strip("*` .")
    return None


def normalize(ans) -> str:
    s = str(ans or "").strip().lower()
    s = s.replace("$", "").replace("\\,", "").replace("\\!", "").replace("\\ ", "")
    s = re.sub(r"\\(?:text|mathrm|mathbf|textbf)\s*\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", s)
    s = s.replace("\\pi", "pi").replace("π", "pi")
    s = s.replace("\\%", "").replace("%", "").replace("^\\circ", "").replace("°", "").replace("\\circ", "")
    s = s.replace("−", "-").replace("\\cdot", "*").replace("\\times", "*")
    # unidades frecuentes al final
    s = re.sub(r"(cm|m|km|mm|kg|g|l|ml|min|h|usd|dólares|dolares|dollars|unidades|units|grados|degrees)\^?[23²³]?\s*$", "", s.strip())
    s = re.sub(r"^\s*[a-z]\s*=\s*", "", s)  # "x = 5" -> "5"
    s = re.sub(r"\s+", "", s)
    return s.strip(".,;:")


def _to_number(s: str):
    """Intenta convertir a Fraction; admite coma decimal, paréntesis y 'k*pi'."""
    t = s.replace("(", "").replace(")", "")
    if re.fullmatch(r"-?\d+,\d{1,2}", t):  # 12,5 / 12,50 -> decimal; 1,250 -> miles
        t = t.replace(",", ".")
    t = t.replace(",", "")  # separador de miles 1,250
    try:
        if "/" in t:
            a, b = t.split("/", 1)
            return Fraction(a) / Fraction(b)
        return Fraction(t)
    except (ValueError, ZeroDivisionError):
        return None


def _split_pi(s: str):
    if "pi" not in s:
        return s, False
    coef = s.replace("*pi", "").replace("pi", "")
    return (coef or "1") if coef not in ("-",) else "-1", True


def _time(s: str):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    return (int(m.group(1)) % 12, int(m.group(2))) if m else None


def same_answer(pred, gold) -> bool:
    if pred is None:
        return False
    p, g = normalize(pred), normalize(gold)
    if p == g:
        return True
    tp, tg = _time(p), _time(g)
    if tp and tg:
        return tp == tg
    if re.fullmatch(r"\(?[a-e]\)?", g):
        # "(C) 32%", "C) ...", "C. ...", "option C" -> C
        m = re.match(r"^(?:option|opción|opcion)?\(?([a-e])\)?(?:[).:]|$)", p)
        return bool(m) and m.group(1) == g.strip("()")
    p_c, p_pi = _split_pi(p)
    g_c, g_pi = _split_pi(g)
    if p_pi != g_pi:
        return False
    a, b = _to_number(p_c), _to_number(g_c)
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))


if __name__ == "__main__":
    casos = [
        ("**Respuesta:** \\boxed{3/4}", "3/4", True),
        ("\\boxed{\\frac{3}{4}}", "3/4", True),
        ("\\boxed{0.75}", "3/4", True),
        ("\\boxed{25\\pi \\text{ cm}^2}", "25\\pi", True),
        ("\\boxed{3:45}", "3:45", True),
        ("\\boxed{12,50}", "12.50", True),
        ("\\boxed{x = -2}", "-2", True),
        ("\\boxed{40^\\circ}", "40", True),
        ("Answer: 17", "17", True),
        ("\\boxed{18}", "17", False),
        ("\\boxed{(B)}", "B", True),
        ("\\boxed{1,250}", "1250", True),
        ("\\boxed{(C) $32\\%$}", "C", True),
        ("\\boxed{C}", "C", True),
        ("\\boxed{(B)}", "C", False),
        ("\\boxed{12}", "C", False),
    ]
    for txt, gold, esperado in casos:
        r = same_answer(extract_answer(txt), gold)
        assert r == esperado, (txt, gold, r)
    print("answers.py OK:", len(casos), "casos")
