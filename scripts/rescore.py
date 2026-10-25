"""Vuelve a calificar un examen ya corrido (outputs_eval/fixed_<tag>.jsonl) con el answers.py actual,
sin volver a generar. Sirve cuando se mejora el extractor: se recalifica la base y el LoRA por igual.

Uso (desde E:\\vertex-math-vision):
    venv\\Scripts\\python.exe scripts\\rescore.py base
    venv\\Scripts\\python.exe scripts\\rescore.py base lora-v1      (tabla comparativa)
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from answers import extract_answer, same_answer  # noqa: E402


def score(tag):
    path = Path("outputs_eval") / f"fixed_{tag}.jsonl"
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    changed = 0
    for r in rows:
        pred = extract_answer(r["reply"])
        ok = same_answer(pred, r["answer"])
        changed += ok != r["correct"]
        r["pred"], r["correct"] = pred, ok
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    groups = defaultdict(list)
    for r in rows:
        groups["TOTAL"].append(r)
        groups[f"fuente={r['source']}"].append(r)
        groups[f"idioma={r['lang']}"].append(r)
        if r.get("family"):
            groups[f"familia={r['family']}"].append(r)
    with open(Path("outputs_eval") / f"fixed_{tag}_resumen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["grupo", "n", "aciertos", "exactitud_%", "con_boxed_%", "idioma_correcto_%"])
        for g in sorted(groups, key=lambda k: (k != "TOTAL", k)):
            rs = groups[g]
            acc = sum(r["correct"] for r in rs)
            w.writerow([g, len(rs), acc, round(100 * acc / len(rs), 1), round(100 * sum(r["boxed"] for r in rs) / len(rs), 1),
                        round(100 * sum(r["lang_ok"] for r in rs) / len(rs), 1)])
    print(f"[{tag}] {len(rows)} respuestas recalificadas, {changed} cambiaron de veredicto")
    return {g: (sum(r["correct"] for r in rs), len(rs)) for g, rs in groups.items()}


def main():
    tags = sys.argv[1:] or ["base"]
    res = {t: score(t) for t in tags}
    keys = sorted(res[tags[0]], key=lambda k: (k != "TOTAL", not k.startswith("fuente"), not k.startswith("idioma"), k))
    print(f"\n{'grupo':26s}" + "".join(f"{t:>16s}" for t in tags) + ("   diferencia" if len(tags) == 2 else ""))
    for k in keys:
        cells = []
        for t in tags:
            a, n = res[t].get(k, (0, 0))
            cells.append(f"{a:4d}/{n:<4d}{100 * a / max(n, 1):5.1f}%")
        diff = ""
        if len(tags) == 2 and k in res[tags[1]]:
            (a0, n0), (a1, n1) = res[tags[0]][k], res[tags[1]][k]
            diff = f"   {100 * (a1 / n1 - a0 / n0):+6.1f}"
        print(f"{k:26s}" + "".join(f"{c:>16s}" for c in cells) + diff)


if __name__ == "__main__":
    main()
