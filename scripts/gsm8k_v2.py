"""Reescribe las soluciones de GSM8K (data/gsm8k/train.jsonl) al formato v2, sin volver a renderizar
las imágenes: primero lo que piden, luego los datos, después los pasos de GSM8K. Sin comprobación inventada:
GSM8K no trae una, y una frase de relleno enseñaría a "comprobar" sin comprobar nada.

En la v1, el modelo aprendió de GSM8K a contestar a la carrera, saltándose el paso de entender el problema.

Uso (desde E:\\vertex-math-vision):
    venv\\Scripts\\python.exe scripts\\gsm8k_v2.py
"""
import json
import re
from pathlib import Path

SRC = Path("data/gsm8k/train.jsonl")
DST = Path("data/gsm8k/train_v2.jsonl")


def split_question(q):
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", q.strip()) if s.strip()]
    if len(sents) < 2:
        return q.strip(), None
    asked = sents[-1]
    known = " ".join(sents[:-1])
    return asked, known


def main():
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    out = []
    for r in rows:
        steps = re.findall(r"\*\*Step \d+:\*\* (.+)", r["response"])
        asked, known = split_question(r["question"])
        parts = [f"**What I need to find:** {asked}"]
        if known:
            parts.append(f"**What I know:** {known}")
        parts += [f"**Step {i + 1}:** {s}" for i, s in enumerate(steps)]
        r = dict(r, response="\n".join(parts) + f"\n\n**Answer:** $\\boxed{{{r['answer']}}}$")
        out.append(r)
    with open(DST, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[+] {len(out)} soluciones de GSM8K en formato v2 -> {DST}")
    print(out[0]["response"])


if __name__ == "__main__":
    main()
