"""Prepara los problemas que NO salen del generador:

  1. GSM8K (train, inglés, MIT) renderizado como foto de tarea -> datos de ENTRENAMIENTO.
  2. MGSM (test, español e inglés: los MISMOS problemas en los dos idiomas) -> solo EXAMEN.
  3. MathVision testmini, niveles 1-2 (Canguro de primaria) -> solo EXAMEN, nunca se entrena.

y arma el examen fijo data/eval/eval_manifest.jsonl junto con el examen sintético.

Uso (desde E:\\vertex-math-vision, después de gen_synth.py):
    venv\\Scripts\\python.exe scripts\\prepare_text_problems.py
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

from datasets import load_dataset
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from gen_synth import GENERIC, font, photo_effect, text_font, wrap  # noqa: E402

MGSM_PARQUET = "hf://datasets/juletxara/mgsm@refs%2Fconvert%2Fparquet/{lang}/test/0000.parquet"


def render_text_problem(text, r, title=None):
    """Enunciado de texto como hoja de tarea (y a veces como foto de celular)."""
    W = 680
    f = font(text_font(r), r.choice([22, 24, 26]))
    tmp = ImageDraw.Draw(Image.new("RGB", (W, 10)))
    lines = []
    for para in text.split("\n"):
        lines += wrap(tmp, para, f, W - 70) or [""]
    lh = int(f.size * 1.45)
    top = 30 + (lh if title else 0)
    img = Image.new("RGB", (W, top + lh * len(lines) + 30), "white")
    d = ImageDraw.Draw(img)
    if r.random() < 0.5:  # hoja de cuaderno con renglones
        for y in range(top + lh - 6, img.height, lh):
            d.line([(20, y), (W - 20, y)], fill="#c7d7f0", width=1)
        d.line([(50, 0), (50, img.height)], fill="#f2b8b8", width=2)
    if title:
        d.text((60, 22), title, font=font("bold", f.size), fill="black")
    ink = r.choice(["black", "#1f2a44", "#202020"])
    for i, ln in enumerate(lines):
        d.text((60, top + i * lh), ln, font=f, fill=ink)
    if r.random() < 0.6:
        img = photo_effect(img, r)
    return img


def gsm8k_steps(answer_text):
    body, final = answer_text.split("####")
    final = final.strip().replace(",", "")
    steps = []
    for ln in body.strip().split("\n"):
        ln = re.sub(r"<<[^>]*>>", "", ln).strip()
        if ln:
            steps.append(ln)
    return steps, final


def build_gsm8k(n, out: Path, seed=7):
    ds = load_dataset("openai/gsm8k", "main", split="train")
    r = random.Random(seed)
    idx = list(range(len(ds)))
    r.shuffle(idx)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for k, i in enumerate(idx[:n]):
        ex = ds[i]
        steps, final = gsm8k_steps(ex["answer"])
        title = r.choice([None, f"Problem {r.randint(1, 30)}.", f"Exercise {r.randint(1, 30)}"])
        img = render_text_problem(ex["question"], r, title)
        rel = f"images/gsm8k-{k:05d}.jpg"
        img.convert("RGB").save(out / rel, quality=90)
        body = "\n".join(f"**Step {j + 1}:** {s}" for j, s in enumerate(steps))
        rows.append(dict(id=f"gsm8k-{k:05d}", source="gsm8k", family="word_problem", lang="en", band="primaria",
                         image=rel, prompt=r.choice(GENERIC["en"]), question=ex["question"],
                         response=f"{body}\n\n**Answer:** $\\boxed{{{final}}}$", answer=final, gsm8k_idx=i))
    with open(out / "train.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[+] GSM8K: {len(rows)} problemas de entrenamiento en {out}")
    return rows


def build_mgsm(n, out: Path, seed=11):
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for lang in ("es", "en"):
        ds = load_dataset("parquet", data_files=MGSM_PARQUET.format(lang=lang), split="train")
        for i in range(min(n, len(ds))):
            ex = ds[i]
            r = random.Random(seed * 1000 + i)  # misma presentación en los dos idiomas
            img = render_text_problem(ex["question"], r)
            rel = f"images/mgsm-{lang}-{i:03d}.jpg"
            img.convert("RGB").save(out / rel, quality=90)
            rows.append(dict(id=f"mgsm-{lang}-{i:03d}", source=f"mgsm_{lang}", lang=lang, band="primaria",
                             image=f"{out.as_posix()}/{rel}", prompt=random.Random(i).choice(GENERIC[lang]),
                             answer=str(ex["answer_number"])))
    print(f"[+] MGSM: {len(rows)} problemas de examen (es + en)")
    return rows


def build_mathvision(levels, out: Path):
    ds = load_dataset("MathLLMs/MathVision", split="testmini")
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for ex in ds:
        if ex["level"] not in levels or ex["decoded_image"] is None:
            continue
        q = re.sub(r"<image\d*>", "", ex["question"]).strip()
        if ex["options"]:
            q += "\n\nOptions:\n" + "\n".join(f"({'ABCDE'[i]}) {o}" for i, o in enumerate(ex["options"][:5]))
            q += "\n\nAnswer with the letter of the correct option."
        rel = f"images/mv-{ex['id']}.jpg"
        ex["decoded_image"].convert("RGB").save(out / rel, quality=92)
        rows.append(dict(id=f"mathvision-{ex['id']}", source="mathvision", lang="en", band=f"nivel{ex['level']}",
                         image=f"{out.as_posix()}/{rel}", prompt=q, answer=str(ex["answer"]).strip()))
    print(f"[+] MathVision testmini niveles {sorted(levels)}: {len(rows)} problemas de examen")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gsm8k", type=int, default=3000, help="problemas de GSM8K para entrenar")
    ap.add_argument("--mgsm", type=int, default=100, help="problemas de MGSM por idioma para el examen")
    ap.add_argument("--synth-eval", type=int, default=300, help="problemas del examen sintético que entran al examen fijo")
    args = ap.parse_args()

    build_gsm8k(args.gsm8k, Path("data/gsm8k"))
    eval_rows = []
    synth = [json.loads(l) for l in open("data/synth/eval.jsonl", encoding="utf-8")]
    for row in synth[: args.synth_eval]:
        eval_rows.append(dict(id=row["id"], source="synth", lang=row["lang"], band=row["band"], family=row["family"],
                              image=f"data/synth/{row['image']}", prompt=row["prompt"], answer=row["answer"]))
    eval_rows += build_mgsm(args.mgsm, Path("data/eval_mgsm"))
    eval_rows += build_mathvision({1, 2}, Path("data/eval_mathvision"))

    out = Path("data/eval")
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "eval_manifest.jsonl", "w", encoding="utf-8") as f:
        for row in eval_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"[+] Examen fijo: {len(eval_rows)} problemas -> {out / 'eval_manifest.jsonl'}")
    print("    por fuente:", dict(Counter(r["source"] for r in eval_rows)))
    print("    por idioma:", dict(Counter(r["lang"] for r in eval_rows)))


if __name__ == "__main__":
    main()
