"""Examen fijo: mide un modelo (base o base + LoRA) sobre data/eval/eval_manifest.jsonl.

La base y el LoRA usan exactamente el mismo prompt, la misma generación (greedy) y el mismo
extractor de respuesta (scripts/answers.py). Se puede cortar y retomar: salta lo ya hecho.

Uso (desde E:\\vertex-math-vision):
    venv\\Scripts\\python.exe scripts\\eval_fixed.py --tag base
    venv\\Scripts\\python.exe scripts\\eval_fixed.py --tag lora --lora models\\lora_adapters\\vertex-math-vision-v1
    venv\\Scripts\\python.exe scripts\\eval_fixed.py --tag base --limit 40      (prueba rápida)
"""
from unsloth import FastVisionModel  # Unsloth primero

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import torch
from dotenv import load_dotenv
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from answers import extract_answer, same_answer  # noqa: E402
from gen_synth import SYSTEM_PROMPT  # noqa: E402

load_dotenv()
BASE_MODEL = os.getenv("BASE_MODEL", "unsloth/Qwen3-VL-2B-Instruct-unsloth-bnb-4bit")
MAX_DIM = int(os.getenv("MAX_VIEW_DIM", 640))

_ES = re.compile(r"\b(el|la|los|las|que|de|es|por|para|entonces|respuesta|paso|cada|hay|son|con)\b", re.I)
_EN = re.compile(r"\b(the|is|of|so|then|answer|step|each|there|are|with|and|to)\b", re.I)


def language_of(text):
    es, en = len(_ES.findall(text)), len(_EN.findall(text))
    return "es" if es > en else "en"


def load_image(path):
    img = Image.open(path).convert("RGB")
    img.thumbnail((MAX_DIM, MAX_DIM), Image.Resampling.LANCZOS)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="nombre de la corrida: base, lora-v1, ...")
    ap.add_argument("--lora", default=None, help="carpeta del adaptador LoRA (vacío = modelo base)")
    ap.add_argument("--manifest", default="data/eval/eval_manifest.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-new-tokens", type=int, default=512)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.manifest, encoding="utf-8")]
    if args.limit:
        # muestra estratificada: un poco de cada fuente
        by = defaultdict(list)
        for row in rows:
            by[row["source"]].append(row)
        rows = []
        per = max(1, args.limit // len(by))
        for src in by:
            rows += by[src][:per]

    out_dir = Path("outputs_eval")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"fixed_{args.tag}.jsonl"
    done = {}
    if out_path.exists():
        for l in open(out_path, encoding="utf-8"):
            r = json.loads(l)
            done[r["id"]] = r

    print(f"[*] Modelo: {args.lora or BASE_MODEL}")
    model, tokenizer = FastVisionModel.from_pretrained(args.lora or BASE_MODEL, load_in_4bit=True)
    FastVisionModel.for_inference(model)

    t0 = time.time()
    with open(out_path, "a", encoding="utf-8") as fout:
        for n, row in enumerate(rows, 1):
            if row["id"] in done:
                continue
            img = load_image(row["image"])
            messages = [
                {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": row["prompt"]}]},
            ]
            text = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
            inputs = tokenizer(img, text, add_special_tokens=False, return_tensors="pt").to("cuda")
            with torch.inference_mode():
                out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False, use_cache=True)
            reply = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            pred = extract_answer(reply)
            rec = dict(id=row["id"], source=row["source"], lang=row["lang"], band=row.get("band"), family=row.get("family"),
                       answer=row["answer"], pred=pred, correct=same_answer(pred, row["answer"]),
                       boxed="\\boxed" in reply, lang_ok=language_of(reply) == row["lang"], reply=reply)
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fout.flush()
            done[row["id"]] = rec
            el = time.time() - t0
            print(f"[{n}/{len(rows)}] {row['id']}: {'OK ' if rec['correct'] else 'MAL'} pred={pred!r} gold={row['answer']!r} ({el / 60:.1f} min)")

    # ---- resumen
    res = [done[r["id"]] for r in rows if r["id"] in done]
    groups = defaultdict(list)
    for r in res:
        groups["TOTAL"].append(r)
        groups[f"fuente={r['source']}"].append(r)
        groups[f"idioma={r['lang']}"].append(r)
        if r.get("family"):
            groups[f"familia={r['family']}"].append(r)
    summary_path = out_dir / f"fixed_{args.tag}_resumen.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["grupo", "n", "aciertos", "exactitud_%", "con_boxed_%", "idioma_correcto_%"])
        for g in sorted(groups, key=lambda k: (k != "TOTAL", k)):
            rs = groups[g]
            acc = sum(r["correct"] for r in rs)
            w.writerow([g, len(rs), acc, round(100 * acc / len(rs), 1),
                        round(100 * sum(r["boxed"] for r in rs) / len(rs), 1),
                        round(100 * sum(r["lang_ok"] for r in rs) / len(rs), 1)])
            if not g.startswith("familia="):
                print(f"{g:28s} {acc:4d}/{len(rs):<4d} = {100 * acc / len(rs):5.1f}%   idioma OK {100 * sum(r['lang_ok'] for r in rs) / len(rs):5.1f}%")
    print(f"[+] Detalle: {out_path}\n[+] Resumen: {summary_path}")


if __name__ == "__main__":
    main()
