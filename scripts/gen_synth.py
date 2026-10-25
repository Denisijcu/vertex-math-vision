"""Generador sintético bilingüe (es/en) de problemas de matemática escolar con imagen.

Cada muestra trae: la imagen (diagrama o "foto" del ejercicio), el texto del estudiante,
una solución paso a paso en el idioma del estudiante y la respuesta exacta.
Todo se calcula aquí, así que la respuesta siempre es correcta y los datos son 100% nuestros.

Uso (desde E:\\vertex-math-vision):
    venv\\Scripts\\python.exe scripts\\gen_synth.py --train 12000 --eval 600

Salida:
    data/synth/images/*.jpg
    data/synth/train.jsonl   data/synth/eval.jsonl
"""
import argparse
import hashlib
import json
import math
import random
from fractions import Fraction
from math import gcd
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------- fuentes
_FONT_CANDIDATES = {
    "sans": ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
    "bold": ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "hand": ["C:/Windows/Fonts/comic.ttf", "C:/Windows/Fonts/segoepr.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"],
    "serif": ["C:/Windows/Fonts/times.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"],
}
_font_cache = {}


def font(kind="sans", size=20):
    key = (kind, size)
    if key not in _font_cache:
        for path in _FONT_CANDIDATES[kind]:
            if Path(path).exists():
                _font_cache[key] = ImageFont.truetype(path, size)
                break
        else:
            _font_cache[key] = ImageFont.load_default(size=size)
    return _font_cache[key]


def text_font(r):
    return r.choice(["sans", "sans", "hand", "serif"])


# --------------------------------------------------------------------------- utilidades
def L(lang, es, en):
    return es if lang == "es" else en


def fmt_num(x):
    """Número sin ceros sobrantes: 12 / 12.5 / 12.25 (siempre punto decimal)."""
    if isinstance(x, Fraction):
        x = float(x)
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".")


def fmt_money(x):
    return f"{x:.2f}"


def frac_str(fr: Fraction):
    return str(fr.numerator) if fr.denominator == 1 else f"{fr.numerator}/{fr.denominator}"


def canvas(w=512, h=384, bg="white"):
    img = Image.new("RGB", (w, h), bg)
    return img, ImageDraw.Draw(img)


def ctext(d, xy, s, f, fill="black"):
    """Texto centrado en xy."""
    box = d.textbbox((0, 0), s, font=f)
    d.text((xy[0] - (box[2] - box[0]) / 2, xy[1] - (box[3] - box[1]) / 2 - box[1]), s, font=f, fill=fill)


def wrap(d, s, f, width):
    lines, cur = [], ""
    for word in s.split():
        test = (cur + " " + word).strip()
        if d.textlength(test, font=f) <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


COLORS = {
    "rojo": ("red", "#d62828"), "azul": ("blue", "#1d4ed8"), "verde": ("green", "#15803d"),
    "amarillo": ("yellow", "#eab308"), "morado": ("purple", "#7e22ce"), "naranja": ("orange", "#ea580c"),
}

# --------------------------------------------------------------------------- familias
# Cada familia devuelve: dict(img, q_es, q_en, steps_es, steps_en, answer, band, key)
# band: "primaria" | "secundaria". key: identifica el problema (para no repetirlo entre train y eval).

SHAPES = [("círculos", "circles", "circle"), ("cuadrados", "squares", "square"),
          ("triángulos", "triangles", "triangle"), ("estrellas", "stars", "star")]


def _draw_shape(d, kind, cx, cy, s, color):
    if kind == "circle":
        d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=color, outline="black", width=2)
    elif kind == "square":
        d.rectangle([cx - s, cy - s, cx + s, cy + s], fill=color, outline="black", width=2)
    elif kind == "triangle":
        d.polygon([(cx, cy - s), (cx - s, cy + s), (cx + s, cy + s)], fill=color, outline="black")
    else:
        pts = []
        for k in range(10):
            rad = s if k % 2 == 0 else s * 0.45
            a = -math.pi / 2 + k * math.pi / 5
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
        d.polygon(pts, fill=color, outline="black")


def fam_counting(r):
    (a_es, a_en, a_kind), (b_es, b_en, b_kind) = r.sample(SHAPES, 2)
    na, nb = r.randint(3, 12), r.randint(2, 10)
    img, d = canvas(512, 384)
    s = 18
    placed = []
    items = [a_kind] * na + [b_kind] * nb
    r.shuffle(items)
    colors = [c[1] for c in COLORS.values()]
    for kind in items:
        for _ in range(500):
            x, y = r.randint(30, 482), r.randint(30, 354)
            if all((x - px) ** 2 + (y - py) ** 2 > (2.6 * s) ** 2 for px, py in placed):
                placed.append((x, y))
                _draw_shape(d, kind, x, y, s, r.choice(colors))
                break
        else:
            return None
    var = r.choice(["count", "total", "diff"])
    if var == "count":
        q_es, q_en = f"¿Cuántos {a_es} hay en la imagen?", f"How many {a_en} are in the picture?"
        se = [f"Cuento los {a_es} uno por uno: hay {na}."]
        sn = [f"I count the {a_en} one by one: there are {na}."]
        ans = na
    elif var == "total":
        q_es = f"¿Cuántas figuras hay en total entre {a_es} y {b_es}?"
        q_en = f"How many shapes are there in total ({a_en} and {b_en})?"
        se = [f"Cuento los {a_es}: hay {na}.", f"Cuento los {b_es}: hay {nb}.", f"Sumo: {na} + {nb} = {na + nb}."]
        sn = [f"Count the {a_en}: there are {na}.", f"Count the {b_en}: there are {nb}.", f"Add: {na} + {nb} = {na + nb}."]
        ans = na + nb
    else:
        if na == nb:
            return None
        big_es, big_en, small_es, small_en, nbig, nsmall = (a_es, a_en, b_es, b_en, na, nb) if na > nb else (b_es, b_en, a_es, a_en, nb, na)
        q_es = f"¿Cuántos {big_es} más que {small_es} hay?"
        q_en = f"How many more {big_en} than {small_en} are there?"
        se = [f"Hay {nbig} {big_es}.", f"Hay {nsmall} {small_es}.", f"Resto: {nbig} - {nsmall} = {nbig - nsmall}."]
        sn = [f"There are {nbig} {big_en}.", f"There are {nsmall} {small_en}.", f"Subtract: {nbig} - {nsmall} = {nbig - nsmall}."]
        ans = nbig - nsmall
    look_es = f"En la imagen hay figuras de dos tipos, {a_es} y {b_es}, mezcladas y de varios colores."
    look_en = f"The picture shows two kinds of shapes, {a_en} and {b_en}, mixed together in several colors."
    if var == "count":
        ck_es = f"Vuelvo a contar los {a_es} en otro orden, de izquierda a derecha, y otra vez me da {na}."
        ck_en = f"I count the {a_en} again in a different order, left to right, and get {na} again."
    elif var == "total":
        ck_es = f"{na + nb} - {nb} = {na}, que son los {a_es}. Cuadra."
        ck_en = f"{na + nb} - {nb} = {na}, which is the number of {a_en}. It checks out."
    else:
        ck_es = f"{nsmall} + {nbig - nsmall} = {nbig}. Cuadra."
        ck_en = f"{nsmall} + {nbig - nsmall} = {nbig}. It checks out."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=str(ans),
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en,
                band="primaria", key=f"count|{a_kind}{na}|{b_kind}{nb}|{var}|{r.random():.6f}")


def fam_clock(r):
    h, m = r.randint(1, 12), r.choice(range(0, 60, 5))
    img, d = canvas(400, 400)
    cx, cy, R = 200, 200, 170
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline="black", width=5, fill="#fffdf5")
    f = font("bold", 30)
    for n in range(1, 13):
        a = math.radians(n * 30 - 90)
        ctext(d, (cx + 0.80 * R * math.cos(a), cy + 0.80 * R * math.sin(a)), str(n), f)
    for k in range(60):
        a = math.radians(k * 6 - 90)
        r1 = R * (0.92 if k % 5 == 0 else 0.96)
        d.line([(cx + r1 * math.cos(a), cy + r1 * math.sin(a)), (cx + R * math.cos(a), cy + R * math.sin(a))], fill="black", width=2)
    ah = math.radians(((h % 12) + m / 60) * 30 - 90)
    am = math.radians(m * 6 - 90)
    d.line([(cx, cy), (cx + 0.50 * R * math.cos(ah), cy + 0.50 * R * math.sin(ah))], fill="black", width=10)
    d.line([(cx, cy), (cx + 0.78 * R * math.cos(am), cy + 0.78 * R * math.sin(am))], fill="#1d4ed8", width=5)
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill="black")
    mark = m // 5 if m else 12
    t = f"{h}:{m:02d}"
    se = [f"La aguja corta (la de las horas) está en el {h}" + (f" o un poco después, hacia el {h % 12 + 1}" if m else "") + f", así que la hora es {h}.",
          f"La aguja larga (la de los minutos) apunta al {mark}: {mark if m else 0} × 5 = {m} minutos."]
    sn = [f"The short hand (hours) points at {h}" + (f" or a bit past it, toward {h % 12 + 1}" if m else "") + f", so the hour is {h}.",
          f"The long hand (minutes) points at {mark}: {mark if m else 0} × 5 = {m} minutes."]
    if r.random() < 0.5:
        q_es, q_en = "¿Qué hora marca el reloj?", "What time does the clock show?"
        se.append(f"La hora es {t}.")
        sn.append(f"The time is {t}.")
        ans = t
        ck_es = f"A las {t} la aguja larga tiene que estar en el {mark} y la corta en el {h}" + (f" o pasada del {h}" if m else "") + ", que es lo que se ve."
        ck_en = f"At {t} the long hand must be on {mark} and the short hand on {h}" + (f" or past {h}" if m else "") + ", which is what the picture shows."
    else:
        k = r.choice([10, 15, 20, 25, 30, 40, 45, 50, 75, 90])
        tot = h * 60 + m + k
        h2, m2 = (tot // 60 - 1) % 12 + 1, tot % 60
        ans = f"{h2}:{m2:02d}"
        q_es = f"¿Qué hora será dentro de {k} minutos?"
        q_en = f"What time will it be in {k} minutes?"
        hk, mk = divmod(k, 60)
        if hk:
            se += [f"Ahora son las {t}.", f"{k} minutos = {hk} hora y {mk} minutos.", f"{t} + {hk} h = {(h + hk - 1) % 12 + 1}:{m:02d}; y sumo {mk} minutos más: {ans}."]
            sn += [f"Now it is {t}.", f"{k} minutes = {hk} hour and {mk} minutes.", f"{t} + {hk} h = {(h + hk - 1) % 12 + 1}:{m:02d}; then add {mk} more minutes: {ans}."]
        else:
            se += [f"Ahora son las {t}.", f"Sumo los minutos: {m} + {k} = {m + k}" + (f"; como pasa de 60, son {m + k} - 60 = {m2} minutos de la hora siguiente." if m + k >= 60 else "."), f"La hora será {ans}."]
            sn += [f"Now it is {t}.", f"Add the minutes: {m} + {k} = {m + k}" + (f"; that is over 60, so it is {m + k} - 60 = {m2} minutes into the next hour." if m + k >= 60 else "."), f"The time will be {ans}."]
        ck_es = f"Vuelvo hacia atrás: {ans} menos {k} minutos son las {t}. Cuadra."
        ck_en = f"Going back: {ans} minus {k} minutes is {t}. It checks out."
    look_es = "Es un reloj de agujas: la aguja corta y gruesa marca las horas y la larga marca los minutos."
    look_en = "It is an analog clock: the short, thick hand shows the hours and the long hand shows the minutes."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=ans, band="primaria",
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en,
                key=f"clock|{h}:{m}|{q_en}")


def fam_fraction(r):
    n = r.choice([2, 3, 4, 5, 6, 8, 10, 12])
    k = r.randint(1, n - 1)
    color = r.choice([c[1] for c in COLORS.values()])
    img, d = canvas(480, 360)
    shaded = set(r.sample(range(n), k)) if r.random() < 0.5 else set(range(k))
    pie = r.random() < 0.5
    if pie:
        cx, cy, R = 240, 180, 150
        for i in range(n):
            a0, a1 = -90 + i * 360 / n, -90 + (i + 1) * 360 / n
            d.pieslice([cx - R, cy - R, cx + R, cy + R], a0, a1, fill=color if i in shaded else "white", outline="black", width=3)
    else:
        x0, w, y0, hgt = 30, 420, 120, 120
        for i in range(n):
            d.rectangle([x0 + i * w / n, y0, x0 + (i + 1) * w / n, y0 + hgt], fill=color if i in shaded else "white", outline="black", width=3)
    fr = Fraction(k, n)
    g = gcd(k, n)
    q_es, q_en = "¿Qué fracción de la figura está coloreada? Simplifica si se puede.", "What fraction of the shape is shaded? Simplify if possible."
    se = [f"La figura está dividida en {n} partes iguales.", f"Hay {k} {'parte coloreada' if k == 1 else 'partes coloreadas'}, así que la fracción es {k}/{n}."]
    sn = [f"The shape is divided into {n} equal parts.", f"{k} {'part is' if k == 1 else 'parts are'} shaded, so the fraction is {k}/{n}."]
    if g > 1:
        se.append(f"Simplifico dividiendo arriba y abajo entre {g}: {k}/{n} = {frac_str(fr)}.")
        sn.append(f"Simplify by dividing top and bottom by {g}: {k}/{n} = {frac_str(fr)}.")
    forma_es, forma_en = ("un círculo", "a circle") if pie else ("una barra", "a bar")
    look_es = f"Hay {forma_es} dividido en partes iguales; algunas partes están coloreadas."
    look_en = f"There is {forma_en} split into equal parts; some parts are shaded."
    if g > 1:
        ck_es = f"{fr.numerator} × {g} = {k} y {fr.denominator} × {g} = {n}, así que {frac_str(fr)} = {k}/{n}."
        ck_en = f"{fr.numerator} × {g} = {k} and {fr.denominator} × {g} = {n}, so {frac_str(fr)} = {k}/{n}."
    else:
        ck_es = f"{k} y {n} no tienen ningún divisor común aparte del 1, así que {k}/{n} ya está simplificada."
        ck_en = f"{k} and {n} have no common factor other than 1, so {k}/{n} is already in simplest form."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=frac_str(fr), band="primaria",
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en,
                key=f"frac|{n}|{sorted(shaded)}|{pie}|{color}")


CATS = [
    [("Perros", "Dogs"), ("Gatos", "Cats"), ("Peces", "Fish"), ("Pájaros", "Birds"), ("Conejos", "Rabbits")],
    [("Manzanas", "Apples"), ("Peras", "Pears"), ("Uvas", "Grapes"), ("Mangos", "Mangoes"), ("Fresas", "Strawberries")],
    [("Fútbol", "Soccer"), ("Béisbol", "Baseball"), ("Natación", "Swimming"), ("Tenis", "Tennis"), ("Baloncesto", "Basketball")],
    [("Lunes", "Monday"), ("Martes", "Tuesday"), ("Miércoles", "Wednesday"), ("Jueves", "Thursday"), ("Viernes", "Friday")],
]


def fam_barchart(r, lang):
    cats = r.choice(CATS)[: r.randint(4, 5)]
    names = [c[0] if lang == "es" else c[1] for c in cats]
    step = r.choice([1, 2, 5])
    vals = [r.randint(1, 10) * step for _ in names]
    img, d = canvas(560, 420)
    x0, y0, x1, y1 = 70, 30, 540, 340
    top = max(vals) + step
    f = font("sans", 15)
    for v in range(0, top + 1, step):
        y = y1 - (y1 - y0) * v / top
        d.line([(x0, y), (x1, y)], fill="#dddddd", width=1)
        ctext(d, (x0 - 22, y), str(v), f)
    d.line([(x0, y0), (x0, y1), (x1, y1)], fill="black", width=2)
    bw = (x1 - x0) / len(names)
    col = r.choice([c[1] for c in COLORS.values()])
    for i, (nm, v) in enumerate(zip(names, vals)):
        bx = x0 + i * bw + bw * 0.2
        d.rectangle([bx, y1 - (y1 - y0) * v / top, bx + bw * 0.6, y1], fill=col, outline="black")
        ctext(d, (bx + bw * 0.3, y1 + 18), nm, f)
    title = L(lang, "Votos de la clase", "Class votes")
    ctext(d, (300, 12), title, font("bold", 17))
    var = r.choice(["read", "diff", "total", "mean"])
    i, j = r.sample(range(len(names)), 2)
    band = "primaria"
    if var == "read":
        q = L(lang, f"Según la gráfica, ¿cuántos votos tiene {names[i]}?", f"According to the chart, how many votes does {names[i]} have?")
        st = [L(lang, f"Busco la barra de {names[i]} y miro hasta dónde llega en el eje vertical: {vals[i]}.",
                f"Find the bar for {names[i]} and read its height on the vertical axis: {vals[i]}.")]
        ans = vals[i]
        ck = L(lang, f"La barra de {names[i]} termina justo en la línea del {vals[i]}.", f"The {names[i]} bar ends exactly on the {vals[i]} line.")
    elif var == "diff":
        if vals[i] == vals[j]:
            return None
        a, b = (i, j) if vals[i] > vals[j] else (j, i)
        q = L(lang, f"¿Cuántos votos más tiene {names[a]} que {names[b]}?", f"How many more votes does {names[a]} have than {names[b]}?")
        st = [L(lang, f"{names[a]} tiene {vals[a]} votos.", f"{names[a]} has {vals[a]} votes."),
              L(lang, f"{names[b]} tiene {vals[b]} votos.", f"{names[b]} has {vals[b]} votes."),
              L(lang, f"Resto: {vals[a]} - {vals[b]} = {vals[a] - vals[b]}.", f"Subtract: {vals[a]} - {vals[b]} = {vals[a] - vals[b]}.")]
        ans = vals[a] - vals[b]
        ck = L(lang, f"{vals[b]} + {ans} = {vals[a]}. Cuadra.", f"{vals[b]} + {ans} = {vals[a]}. It checks out.")
    elif var == "total":
        q = L(lang, "¿Cuántos votos hay en total?", "How many votes are there in total?")
        st = [L(lang, "Leo cada barra: ", "Read each bar: ") + ", ".join(f"{n} = {v}" for n, v in zip(names, vals)) + ".",
              L(lang, "Sumo: ", "Add: ") + " + ".join(map(str, vals)) + f" = {sum(vals)}."]
        ans = sum(vals)
        acc, parts = 0, []
        for v in vals:
            acc += v
            parts.append(str(acc))
        st[-1] = L(lang, "Sumo poco a poco: ", "Add step by step: ") + " → ".join(parts) + f". Total = {ans}."
        ck = L(lang, "Sumo en orden inverso: ", "Add in reverse order: ") + " + ".join(map(str, vals[::-1])) + f" = {ans}. " + L(lang, "Cuadra.", "It checks out.")
    else:
        if sum(vals) % len(vals):
            return None
        band = "secundaria"
        q = L(lang, "¿Cuál es la media (promedio) de votos por categoría?", "What is the mean (average) number of votes per category?")
        st = [L(lang, "Sumo todos los valores: ", "Add all the values: ") + " + ".join(map(str, vals)) + f" = {sum(vals)}.",
              L(lang, f"Divido entre el número de categorías ({len(vals)}): {sum(vals)} ÷ {len(vals)} = {sum(vals) // len(vals)}.",
                f"Divide by the number of categories ({len(vals)}): {sum(vals)} ÷ {len(vals)} = {sum(vals) // len(vals)}.")]
        ans = sum(vals) // len(vals)
        ck = L(lang, f"{ans} × {len(vals)} = {sum(vals)}. Cuadra.", f"{ans} × {len(vals)} = {sum(vals)}. It checks out.")
    look = L(lang, f"Es una gráfica de barras con {len(names)} categorías: {', '.join(names)}. El eje vertical va de {step} en {step}.",
             f"It is a bar chart with {len(names)} categories: {', '.join(names)}. The vertical axis goes up by {step}.")
    return dict(img=img, q=q, steps=st, answer=str(ans), band=band, look=look, check=ck, key=f"bar|{names}|{vals}|{var}|{i}|{j}")


def fam_rectangle(r):
    img, d = canvas(520, 380)
    f = font("sans", 22)
    unit = r.choice(["cm", "m"])
    if r.random() < 0.65:
        a, b = r.randint(2, 15), r.randint(2, 12)
        sc = min(380 / a, 260 / b)
        x0, y0 = (520 - a * sc) / 2, (380 - b * sc) / 2
        d.rectangle([x0, y0, x0 + a * sc, y0 + b * sc], outline="black", width=4, fill="#e0f2fe")
        ctext(d, (x0 + a * sc / 2, y0 + b * sc + 20), f"{a} {unit}", f)
        ctext(d, (x0 - 38, y0 + b * sc / 2), f"{b} {unit}", f)
        if r.random() < 0.5:
            q_es, q_en = "¿Cuál es el área del rectángulo?", "What is the area of the rectangle?"
            se = ["El área de un rectángulo es base × altura.", f"Área = {a} × {b} = {a * b} {unit}²."]
            sn = ["The area of a rectangle is base × height.", f"Area = {a} × {b} = {a * b} {unit}²."]
            ans = a * b
            ck_es, ck_en = f"{a * b} ÷ {a} = {b}, que es la altura. Cuadra.", f"{a * b} ÷ {a} = {b}, which is the height. It checks out."
        else:
            q_es, q_en = "¿Cuál es el perímetro del rectángulo?", "What is the perimeter of the rectangle?"
            se = ["El perímetro es la suma de los cuatro lados; los lados opuestos son iguales.", f"{a} + {b} = {a + b}.", f"Perímetro = 2 × {a + b} = {2 * (a + b)} {unit}."]
            sn = ["The perimeter is the sum of the four sides; opposite sides are equal.", f"{a} + {b} = {a + b}.", f"Perimeter = 2 × {a + b} = {2 * (a + b)} {unit}."]
            ans = 2 * (a + b)
            ck_es = f"Lado por lado: {a} + {b} + {a} + {b} = {2 * (a + b)}. Cuadra."
            ck_en = f"Side by side: {a} + {b} + {a} + {b} = {2 * (a + b)}. It checks out."
        band, key = "primaria", f"rect|{a}|{b}|{q_en}"
        look_es, look_en = f"Un rectángulo de base {a} {unit} y altura {b} {unit}.", f"A rectangle with base {a} {unit} and height {b} {unit}."
    else:
        # figura en L: rectángulo grande menos una esquina
        A, B = r.randint(6, 14), r.randint(5, 10)
        c, e = r.randint(2, A - 2), r.randint(2, B - 2)
        sc = min(360 / A, 260 / B)
        x0, y0 = (520 - A * sc) / 2, (380 - B * sc) / 2
        pts = [(x0, y0), (x0 + (A - c) * sc, y0), (x0 + (A - c) * sc, y0 + e * sc), (x0 + A * sc, y0 + e * sc),
               (x0 + A * sc, y0 + B * sc), (x0, y0 + B * sc)]
        d.polygon(pts, fill="#fef3c7", outline="black")
        d.line(pts + [pts[0]], fill="black", width=4)
        ctext(d, (x0 + A * sc / 2, y0 + B * sc + 20), f"{A} {unit}", f)
        ctext(d, (x0 - 38, y0 + B * sc / 2), f"{B} {unit}", f)
        ctext(d, (x0 + (A - c / 2) * sc, y0 + e * sc - 18), f"{c} {unit}", font("sans", 18))
        ctext(d, (x0 + (A - c) * sc - 30, y0 + e * sc / 2), f"{e} {unit}", font("sans", 18))
        q_es, q_en = "Calcula el área de la figura.", "Find the area of the figure."
        se = [f"Completo la figura como un rectángulo de {A} × {B} = {A * B} {unit}².",
              f"Le falta un rectángulo de {c} × {e} = {c * e} {unit}² en la esquina.",
              f"Área = {A * B} - {c * e} = {A * B - c * e} {unit}²."]
        sn = [f"Complete the figure as a {A} × {B} = {A * B} {unit}² rectangle.",
              f"A {c} × {e} = {c * e} {unit}² rectangle is missing from the corner.",
              f"Area = {A * B} - {c * e} = {A * B - c * e} {unit}²."]
        ans, band, key = A * B - c * e, "secundaria", f"L|{A}|{B}|{c}|{e}"
        look_es = f"Una figura en forma de L: un rectángulo de {A} × {B} {unit} al que le falta una esquina de {c} × {e} {unit}."
        look_en = f"An L-shaped figure: a {A} × {B} {unit} rectangle with a {c} × {e} {unit} corner missing."
        p1, p2 = A * (B - e), (A - c) * e
        ck_es = f"Otra forma: la parte de abajo mide {A} × {B - e} = {p1} y la de arriba {A - c} × {e} = {p2}; {p1} + {p2} = {p1 + p2}. Cuadra."
        ck_en = f"Another way: the bottom part is {A} × {B - e} = {p1} and the top part is {A - c} × {e} = {p2}; {p1} + {p2} = {p1 + p2}. It checks out."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=str(ans), band=band, key=key,
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en)


def fam_numberline(r):
    secundaria = r.random() < 0.4
    step = r.choice([Fraction(1, 2), Fraction(1, 4), Fraction(2), Fraction(5)]) if secundaria else r.choice([Fraction(1), Fraction(2), Fraction(5), Fraction(10)])
    start = Fraction(r.randint(-6, 0)) * step if secundaria else Fraction(r.randint(0, 5)) * step
    n = r.randint(5, 10)
    k = r.choice([i for i in range(1, n) if i not in (0,)])
    end = start + n * step
    img, d = canvas(600, 220)
    x0, x1, y = 40, 560, 120
    d.line([(x0 - 15, y), (x1 + 15, y)], fill="black", width=3)
    f = font("sans", 20)
    labeled = {0, n} if r.random() < 0.6 else {0, 1, n}
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        d.line([(x, y - 12), (x, y + 12)], fill="black", width=3)
        if i in labeled:
            ctext(d, (x, y + 32), fmt_num(start + i * step), f)
    xk = x0 + (x1 - x0) * k / n
    d.ellipse([xk - 9, y - 9, xk + 9, y + 9], fill="#d62828")
    d.polygon([(xk, y - 18), (xk - 10, y - 40), (xk + 10, y - 40)], fill="#d62828")
    ctext(d, (xk, y - 58), "?", font("bold", 26))
    val = start + k * step
    q_es, q_en = "¿Qué número marca el punto rojo en la recta numérica?", "What number does the red point mark on the number line?"
    if 1 in labeled:
        se = [f"Entre dos marcas seguidas hay {fmt_num(step)} (de {fmt_num(start)} a {fmt_num(start + step)})."]
        sn = [f"Each space between marks is {fmt_num(step)} (from {fmt_num(start)} to {fmt_num(start + step)})."]
    else:
        se = [f"De {fmt_num(start)} a {fmt_num(end)} hay {n} espacios iguales.", f"Cada espacio vale ({fmt_num(end)} - ({fmt_num(start)})) ÷ {n} = {fmt_num(step)}."]
        sn = [f"From {fmt_num(start)} to {fmt_num(end)} there are {n} equal spaces.", f"Each space is ({fmt_num(end)} - ({fmt_num(start)})) ÷ {n} = {fmt_num(step)}."]
    se.append(f"El punto está {k} {'espacio' if k == 1 else 'espacios'} después de {fmt_num(start)}: {fmt_num(start)} + {k} × {fmt_num(step)} = {fmt_num(val)}.")
    sn.append(f"The point is {k} {'space' if k == 1 else 'spaces'} after {fmt_num(start)}: {fmt_num(start)} + {k} × {fmt_num(step)} = {fmt_num(val)}.")
    look_es = f"Una recta numérica con marcas a la misma distancia; solo algunas tienen número. Un punto rojo con un signo de interrogación está {k} {'marca' if k == 1 else 'marcas'} después del inicio."
    look_en = f"A number line with evenly spaced marks; only some are labeled. A red point with a question mark sits {k} {'mark' if k == 1 else 'marks'} after the start."
    ck_es = f"Desde el otro extremo: {fmt_num(end)} - {n - k} × {fmt_num(step)} = {fmt_num(val)}. Cuadra."
    ck_en = f"From the other end: {fmt_num(end)} - {n - k} × {fmt_num(step)} = {fmt_num(val)}. It checks out."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=fmt_num(val),
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en,
                band="secundaria" if secundaria else "primaria", key=f"nl|{start}|{step}|{n}|{k}|{sorted(labeled)}")


ITEMS = [("lápiz", "lápices", "pencil", "pencils"), ("cuaderno", "cuadernos", "notebook", "notebooks"),
         ("borrador", "borradores", "eraser", "erasers"), ("regla", "reglas", "ruler", "rulers"),
         ("jugo", "jugos", "juice", "juices"), ("galleta", "galletas", "cookie", "cookies"),
         ("manzana", "manzanas", "apple", "apples"), ("sándwich", "sándwiches", "sandwich", "sandwiches")]


def fam_prices(r, lang):
    items = r.sample(ITEMS, 4)
    prices = [r.choice([0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 3.5, 4, 5]) for _ in items]
    img, d = canvas(460, 300, "#fffef7")
    f, fb = font("sans", 22), font("bold", 22)
    d.rectangle([40, 30, 420, 270], outline="black", width=3)
    d.line([(40, 78), (420, 78)], fill="black", width=3)
    d.line([(270, 30), (270, 270)], fill="black", width=2)
    ctext(d, (155, 54), L(lang, "Producto", "Item"), fb)
    ctext(d, (345, 54), L(lang, "Precio", "Price"), fb)
    for i, (it, p) in enumerate(zip(items, prices)):
        yy = 105 + i * 46
        ctext(d, (155, yy), (it[0] if lang == "es" else it[2]).capitalize(), f)
        ctext(d, (345, yy), f"${fmt_money(p)}", f)
        if i < 3:
            d.line([(40, yy + 23), (420, yy + 23)], fill="#bbbbbb", width=1)
    (i1, i2) = r.sample(range(4), 2)
    q1, q2 = r.randint(2, 6), r.randint(1, 5)
    name = r.choice(["Ana", "Luis", "Sofía", "Mateo", "Valeria", "Diego", "Emma", "Liam"])
    def nm(i, q):
        it = items[i]
        return (it[0] if q == 1 else it[1]) if lang == "es" else (it[2] if q == 1 else it[3])
    total = q1 * prices[i1] + q2 * prices[i2]
    st = [L(lang, f"{q1} {nm(i1, q1)}: {q1} × ${fmt_money(prices[i1])} = ${fmt_money(q1 * prices[i1])}.",
            f"{q1} {nm(i1, q1)}: {q1} × ${fmt_money(prices[i1])} = ${fmt_money(q1 * prices[i1])}."),
          L(lang, f"{q2} {nm(i2, q2)}: {q2} × ${fmt_money(prices[i2])} = ${fmt_money(q2 * prices[i2])}.",
            f"{q2} {nm(i2, q2)}: {q2} × ${fmt_money(prices[i2])} = ${fmt_money(q2 * prices[i2])}."),
          L(lang, f"Total: ${fmt_money(q1 * prices[i1])} + ${fmt_money(q2 * prices[i2])} = ${fmt_money(total)}.",
            f"Total: ${fmt_money(q1 * prices[i1])} + ${fmt_money(q2 * prices[i2])} = ${fmt_money(total)}.")]
    pay = next((b for b in (5, 10, 20, 50) if b > total), None)
    if r.random() < 0.5 and pay:
        q = L(lang, f"{name} compra {q1} {nm(i1, q1)} y {q2} {nm(i2, q2)}, y paga con un billete de ${pay}. ¿Cuánto le devuelven?",
              f"{name} buys {q1} {nm(i1, q1)} and {q2} {nm(i2, q2)} and pays with a ${pay} bill. How much change does {name} get?")
        st.append(L(lang, f"Cambio: ${pay} - ${fmt_money(total)} = ${fmt_money(pay - total)}.", f"Change: ${pay} - ${fmt_money(total)} = ${fmt_money(pay - total)}."))
        ans = pay - total
        ck = L(lang, f"${fmt_money(ans)} + ${fmt_money(total)} = ${fmt_money(pay)}. Cuadra.", f"${fmt_money(ans)} + ${fmt_money(total)} = ${fmt_money(pay)}. It checks out.")
    else:
        q = L(lang, f"{name} compra {q1} {nm(i1, q1)} y {q2} {nm(i2, q2)}. ¿Cuánto paga en total?",
              f"{name} buys {q1} {nm(i1, q1)} and {q2} {nm(i2, q2)}. How much does {name} pay in total?")
        ans = total
        ck = L(lang, f"${fmt_money(total)} - ${fmt_money(q2 * prices[i2])} = ${fmt_money(q1 * prices[i1])}, que es lo de {nm(i1, q1)}. Cuadra.",
               f"${fmt_money(total)} - ${fmt_money(q2 * prices[i2])} = ${fmt_money(q1 * prices[i1])}, which is the cost of the {nm(i1, q1)}. It checks out.")
    look = L(lang, "Una tabla de precios: " + ", ".join(f"{it[0]} ${fmt_money(p)}" for it, p in zip(items, prices)) + ".",
             "A price list: " + ", ".join(f"{it[2]} ${fmt_money(p)}" for it, p in zip(items, prices)) + ".")
    return dict(img=img, q=q, steps=st, answer=fmt_money(ans), band="primaria", look=look, check=ck, key=f"price|{items}|{prices}|{i1}{q1}|{i2}{q2}|{q[:20]}")


def fam_column_op(r):
    op = r.choice(["+", "-", "x"])
    if op == "+":
        a, b = r.randint(100, 9999), r.randint(10, 999)
    elif op == "-":
        a = r.randint(200, 9999)
        b = r.randint(10, a - 1)
    else:
        a, b = r.randint(12, 999), r.choice([r.randint(2, 9), r.choice([x for x in range(12, 100) if x % 10])])
    res = a + b if op == "+" else a - b if op == "-" else a * b
    img, d = canvas(360, 300, "#fffef7")
    f = font(r.choice(["hand", "sans", "serif"]), 48)
    w = max(len(str(a)), len(str(b)) + 1, len(str(res)))
    right = 290
    for row, s in enumerate([str(a), ("×" if op == "x" else op) + " " + str(b)]):
        d.text((right, 40 + row * 70), s, font=f, fill="black", anchor="ra")
    d.line([(right - 30 * w - 30, 175), (right + 10, 175)], fill="black", width=4)
    q_es, q_en = "Resuelve la operación.", "Solve the operation."
    se, sn = [], []
    if op == "+":
        da, db = str(a)[::-1], str(b)[::-1]
        carry = 0
        names_es, names_en = ["unidades", "decenas", "centenas", "unidades de mil", "decenas de mil"], ["ones", "tens", "hundreds", "thousands", "ten thousands"]
        for i in range(max(len(da), len(db))):
            x, y = int(da[i]) if i < len(da) else 0, int(db[i]) if i < len(db) else 0
            s = x + y + carry
            extra_es = f" + {carry} que llevaba" if carry else ""
            extra_en = f" + {carry} carried" if carry else ""
            se.append(f"{names_es[i].capitalize()}: {x} + {y}{extra_es} = {s}" + (f"; escribo {s % 10} y llevo {s // 10}." if s >= 10 else "."))
            sn.append(f"{names_en[i].capitalize()}: {x} + {y}{extra_en} = {s}" + (f"; write {s % 10}, carry {s // 10}." if s >= 10 else "."))
            carry = s // 10
        if carry:
            se.append(f"Escribo el {carry} que llevo al principio.")
            sn.append(f"Write the carried {carry} at the front.")
    elif op == "-":
        da, db = str(a)[::-1], str(b)[::-1]
        names_es, names_en = ["unidades", "decenas", "centenas", "unidades de mil"], ["ones", "tens", "hundreds", "thousands"]
        borrow = 0
        for i in range(len(da)):
            x, y = int(da[i]) - borrow, int(db[i]) if i < len(db) else 0
            if i >= len(db) and borrow == 0:
                break
            pre_es = f"{int(da[i])} - 1 que presté = {x}; " if borrow else ""
            pre_en = f"{int(da[i])} - 1 borrowed = {x}; " if borrow else ""
            if x < y:
                se.append(f"{names_es[i].capitalize()}: {pre_es}{x} es menor que {y}, pido prestado 1 a la columna siguiente: {x + 10} - {y} = {x + 10 - y}.")
                sn.append(f"{names_en[i].capitalize()}: {pre_en}{x} is less than {y}, so borrow 1 from the next column: {x + 10} - {y} = {x + 10 - y}.")
                borrow = 1
            else:
                se.append(f"{names_es[i].capitalize()}: {pre_es}{x} - {y} = {x - y}.")
                sn.append(f"{names_en[i].capitalize()}: {pre_en}{x} - {y} = {x - y}.")
                borrow = 0
        se.append(f"Bajo las cifras que quedan y compruebo sumando: {res} + {b} = {a}.")
        sn.append(f"Bring down the remaining digits and check by adding: {res} + {b} = {a}.")
    else:
        db = str(b)
        if len(db) == 1:
            parts = [(int(dg) * 10 ** i) for i, dg in enumerate(str(a)[::-1])]
            se = [f"Descompongo {a} = " + " + ".join(str(p) for p in parts[::-1]) + "."] + \
                 [f"{p} × {b} = {p * b}." for p in parts[::-1]] + \
                 ["Sumo: " + " + ".join(str(p * b) for p in parts[::-1]) + f" = {res}."]
            sn = [f"Break {a} into " + " + ".join(str(p) for p in parts[::-1]) + "."] + \
                 [f"{p} × {b} = {p * b}." for p in parts[::-1]] + \
                 ["Add: " + " + ".join(str(p * b) for p in parts[::-1]) + f" = {res}."]
        else:
            u, t = int(db[1]), int(db[0])
            se = [f"Multiplico por las unidades: {a} × {u} = {a * u}.", f"Multiplico por las decenas: {a} × {t}0 = {a * t * 10}.",
                  f"Sumo los productos parciales: {a * u} + {a * t * 10} = {res}."]
            sn = [f"Multiply by the ones: {a} × {u} = {a * u}.", f"Multiply by the tens: {a} × {t}0 = {a * t * 10}.",
                  f"Add the partial products: {a * u} + {a * t * 10} = {res}."]
    se.append(f"Resultado: {res}.")
    sn.append(f"Result: {res}.")
    sym = "×" if op == "x" else op
    look_es, look_en = f"Una operación escrita en columna: {a} {sym} {b}.", f"An operation written in columns: {a} {sym} {b}."
    if op == "+":
        ck_es, ck_en = f"{res} - {b} = {a}. Cuadra.", f"{res} - {b} = {a}. It checks out."
    elif op == "-":
        se.pop(-2); sn.pop(-2)  # la comprobación va en su sección
        ck_es, ck_en = f"{res} + {b} = {a}. Cuadra.", f"{res} + {b} = {a}. It checks out."
    else:
        ck_es, ck_en = f"{res} ÷ {b} = {a}. Cuadra.", f"{res} ÷ {b} = {a}. It checks out."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=str(res), band="primaria", key=f"col|{a}{op}{b}",
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en)


def _triangle_pts(A, B, W=420, H=280):
    a, b = math.radians(A), math.radians(B)
    # base (0,0)-(1,0); vértice superior por intersección
    t = math.tan(a)
    u = math.tan(b)
    x = u / (t + u)
    y = t * x
    sc = min(W / 1.0, H / max(y, 1e-6))
    return [(0, 0), (1, 0), (x, y)], sc


def fam_triangle(r):
    A, B = r.randint(25, 95), r.randint(25, 95)
    C = 180 - A - B
    if C < 20:
        return None
    pts, sc = _triangle_pts(A, B)
    img, d = canvas(520, 400)
    ox, oy = 50, 360
    P = [(ox + p[0] * sc * 0.95, oy - p[1] * sc * 0.95) for p in pts]
    if max(p[0] for p in P) > 500 or min(p[1] for p in P) < 20:
        sc2 = sc * 0.8
        P = [(ox + p[0] * sc2, oy - p[1] * sc2) for p in pts]
    d.polygon(P, fill="#ecfccb", outline="black")
    d.line(P + [P[0]], fill="black", width=4)
    f = font("sans", 22)
    cen = (sum(p[0] for p in P) / 3, sum(p[1] for p in P) / 3)
    def lab(p, s):
        x, y = p[0] + (cen[0] - p[0]) * 0.28, p[1] + (cen[1] - p[1]) * 0.28
        ctext(d, (x, y), s, f, fill="#b91c1c" if s == "x" else "black")
    hide = r.randrange(3)
    vals = [A, B, C]
    for i in range(3):
        lab(P[i], "x" if i == hide else f"{vals[i]}°")
    known = [vals[i] for i in range(3) if i != hide]
    q_es, q_en = "Halla el valor del ángulo x.", "Find the value of angle x."
    sk = known[0] + known[1]
    se = ["Los tres ángulos de un triángulo suman 180°.", f"Sumo los ángulos que conozco: {known[0]}° + {known[1]}° = {sk}°.", f"x = 180° - {sk}° = {vals[hide]}°."]
    sn = ["The three angles of a triangle add up to 180°.", f"Add the known angles: {known[0]}° + {known[1]}° = {sk}°.", f"x = 180° - {sk}° = {vals[hide]}°."]
    look_es = f"Un triángulo con dos ángulos marcados, {known[0]}° y {known[1]}°; el tercero es x."
    look_en = f"A triangle with two marked angles, {known[0]}° and {known[1]}°; the third one is x."
    ck_es = f"{known[0]} + {known[1]} + {vals[hide]} = 180. Cuadra."
    ck_en = f"{known[0]} + {known[1]} + {vals[hide]} = 180. It checks out."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=str(vals[hide]), band="secundaria", key=f"tri|{A}|{B}|{hide}",
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en)


TRIPLES = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41), (12, 35, 37), (11, 60, 61), (28, 45, 53), (33, 56, 65)]


def fam_pythagoras(r):
    a, b, c = r.choice(TRIPLES)
    k = r.choice([1, 1, 2, 3, 4, 5]) if c <= 17 else r.choice([1, 1, 2])
    a, b, c = a * k, b * k, c * k
    unit = r.choice(["", " cm", " m"])
    if r.random() < 0.5:
        a, b = b, a
    img, d = canvas(520, 400)
    sc = min(380 / a, 280 / b)
    p0, p1, p2 = (60, 350), (60 + a * sc, 350), (60, 350 - b * sc)
    d.polygon([p0, p1, p2], fill="#e0e7ff", outline="black")
    d.line([p0, p1, p2, p0], fill="black", width=4)
    d.rectangle([60, 330, 80, 350], outline="black", width=2)
    f = font("sans", 22)
    unk = r.choice(["c", "a"])
    ctext(d, ((p0[0] + p1[0]) / 2, 375), "x" if unk == "a" else f"{a}{unit}", f, fill="#b91c1c" if unk == "a" else "black")
    ctext(d, (32 if not unit else 10, (p0[1] + p2[1]) / 2), f"{b}{unit}", f)
    ctext(d, ((p1[0] + p2[0]) / 2 + 22, (p1[1] + p2[1]) / 2 - 16), "x" if unk == "c" else f"{c}{unit}", f, fill="#b91c1c" if unk == "c" else "black")
    q_es, q_en = "El triángulo es rectángulo. Halla x.", "The triangle is a right triangle. Find x."
    if unk == "c":
        se = ["Por el teorema de Pitágoras: hipotenusa² = cateto² + cateto².", f"x² = {a}² + {b}² = {a * a} + {b * b} = {c * c}.", f"x = √{c * c} = {c}."]
        sn = ["By the Pythagorean theorem: hypotenuse² = leg² + leg².", f"x² = {a}² + {b}² = {a * a} + {b * b} = {c * c}.", f"x = √{c * c} = {c}."]
        ans = c
    else:
        se = ["Por el teorema de Pitágoras: cateto² = hipotenusa² - otro cateto².", f"x² = {c}² - {b}² = {c * c} - {b * b} = {a * a}.", f"x = √{a * a} = {a}."]
        sn = ["By the Pythagorean theorem: leg² = hypotenuse² - other leg².", f"x² = {c}² - {b}² = {c * c} - {b * b} = {a * a}.", f"x = √{a * a} = {a}."]
        ans = a
    if unk == "c":
        look_es = f"Un triángulo rectángulo (el cuadradito marca el ángulo recto). Los catetos miden {a} y {b}; x es la hipotenusa, el lado más largo."
        look_en = f"A right triangle (the small square marks the right angle). The legs are {a} and {b}; x is the hypotenuse, the longest side."
    else:
        look_es = f"Un triángulo rectángulo (el cuadradito marca el ángulo recto). La hipotenusa mide {c}, un cateto mide {b} y x es el otro cateto."
        look_en = f"A right triangle (the small square marks the right angle). The hypotenuse is {c}, one leg is {b}, and x is the other leg."
    ck_es = f"{a}² + {b}² = {a * a} + {b * b} = {c * c} = {c}². Cuadra."
    ck_en = f"{a}² + {b}² = {a * a} + {b * b} = {c * c} = {c}². It checks out."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=str(ans), band="secundaria", key=f"pyt|{a}|{b}|{unk}|{unit}",
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en)


def fam_circle(r):
    rad = r.randint(1, 25)
    unit = r.choice(["cm", "m", "mm"])
    img, d = canvas(420, 400)
    cx, cy, R = 210, 200, 160
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline="black", width=4, fill="#fce7f3")
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill="black")
    f = font("sans", 22)
    use_d = r.random() < 0.4
    if use_d:
        d.line([(cx - R, cy), (cx + R, cy)], fill="#1d4ed8", width=3)
        ctext(d, (cx, cy - 20), f"d = {2 * rad} {unit}", f)
    else:
        d.line([(cx, cy), (cx + R, cy)], fill="#1d4ed8", width=3)
        ctext(d, (cx + R / 2, cy - 20), f"r = {rad} {unit}", f)
    se0 = [f"El diámetro es {2 * rad} {unit}, así que el radio es {2 * rad} ÷ 2 = {rad} {unit}."] if use_d else []
    sn0 = [f"The diameter is {2 * rad} {unit}, so the radius is {2 * rad} ÷ 2 = {rad} {unit}."] if use_d else []
    if r.random() < 0.5:
        q_es, q_en = "Halla el área del círculo. Deja la respuesta en términos de π.", "Find the area of the circle. Leave the answer in terms of π."
        se = se0 + ["Área = π · r².", f"Área = π · {rad}² = {rad * rad}π {unit}²."]
        sn = sn0 + ["Area = π · r².", f"Area = π · {rad}² = {rad * rad}π {unit}²."]
        ans = f"{rad * rad}\\pi"
        ck_es, ck_en = f"{rad} × {rad} = {rad * rad}, así que el área es {rad * rad}π. Cuadra.", f"{rad} × {rad} = {rad * rad}, so the area is {rad * rad}π. It checks out."
    else:
        q_es, q_en = "Halla la longitud de la circunferencia. Deja la respuesta en términos de π.", "Find the circumference. Leave the answer in terms of π."
        se = se0 + ["Circunferencia = 2 · π · r.", f"C = 2 · π · {rad} = {2 * rad}π {unit}."]
        sn = sn0 + ["Circumference = 2 · π · r.", f"C = 2 · π · {rad} = {2 * rad}π {unit}."]
        ans = f"{2 * rad}\\pi"
        ck_es, ck_en = f"También C = π × diámetro = π × {2 * rad} = {2 * rad}π. Cuadra.", f"Also C = π × diameter = π × {2 * rad} = {2 * rad}π. It checks out."
    look_es = f"Un círculo con el {'diámetro' if use_d else 'radio'} marcado: {'d = ' + str(2 * rad) if use_d else 'r = ' + str(rad)} {unit}."
    look_en = f"A circle with its {'diameter' if use_d else 'radius'} marked: {'d = ' + str(2 * rad) if use_d else 'r = ' + str(rad)} {unit}."
    return dict(look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en, img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=ans, band="secundaria", key=f"circ|{rad}|{use_d}|{unit}|{q_en[:12]}")


def fam_equation(r):
    x = r.randint(-9, 12)
    kind = r.choice(["ax+b", "a(x-b)", "ax+b=cx+d"])
    if kind == "ax+b":
        a, b = r.choice([2, 3, 4, 5, 6, 7]), r.randint(-15, 20)
        c = a * x + b
        eq = f"{a}x {'+' if b >= 0 else '-'} {abs(b)} = {c}"
        se = [f"Paso el {b} al otro lado restándolo: {a}x = {c} - ({b}) = {c - b}.", f"Divido entre {a}: x = {c - b} ÷ {a} = {x}."]
        sn = [f"Move {b} to the other side by subtracting it: {a}x = {c} - ({b}) = {c - b}.", f"Divide by {a}: x = {c - b} ÷ {a} = {x}."]
    elif kind == "a(x-b)":
        a, b = r.choice([2, 3, 4, 5]), r.randint(1, 9)
        c = a * (x - b)
        eq = f"{a}(x - {b}) = {c}"
        se = [f"Divido ambos lados entre {a}: x - {b} = {c} ÷ {a} = {c // a}.", f"Sumo {b}: x = {c // a} + {b} = {x}."]
        sn = [f"Divide both sides by {a}: x - {b} = {c} ÷ {a} = {c // a}.", f"Add {b}: x = {c // a} + {b} = {x}."]
    else:
        a, c = r.randint(3, 9), r.randint(1, 8)
        if a == c:
            return None
        b = r.randint(-10, 10)
        dd = a * x + b - c * x
        eq = f"{a}x {'+' if b >= 0 else '-'} {abs(b)} = {c}x {'+' if dd >= 0 else '-'} {abs(dd)}"
        se = [f"Paso las x a la izquierda: {a}x - {c}x = {a - c}x.", f"Paso los números a la derecha: {dd} - ({b}) = {dd - b}.",
              f"{a - c}x = {dd - b}, así que x = {dd - b} ÷ {a - c} = {x}."]
        sn = [f"Move the x terms to the left: {a}x - {c}x = {a - c}x.", f"Move the numbers to the right: {dd} - ({b}) = {dd - b}.",
              f"{a - c}x = {dd - b}, so x = {dd - b} ÷ {a - c} = {x}."]
    img, d = canvas(520, 200, "#fffef7")
    ctext(d, (260, 100), eq, font(r.choice(["hand", "serif", "sans"]), 46))
    q_es, q_en = "Resuelve la ecuación para x.", "Solve the equation for x."
    if kind == "ax+b":
        lhs = f"{a} × ({x}) + ({b}) = {a * x} + ({b}) = {a * x + b}"; rhs = f"{c}"
    elif kind == "a(x-b)":
        lhs = f"{a} × ({x} - {b}) = {a} × ({x - b}) = {a * (x - b)}"; rhs = f"{c}"
    else:
        lhs = f"{a} × ({x}) + ({b}) = {a * x + b}"; rhs = f"{c} × ({x}) + ({dd}) = {c * x + dd}"
    look_es, look_en = f"Una ecuación con una incógnita: {eq}.", f"An equation with one unknown: {eq}."
    ck_es = f"Sustituyo x = {x}: izquierda {lhs}; derecha {rhs}. Son iguales, cuadra."
    ck_en = f"Substitute x = {x}: left side {lhs}; right side {rhs}. They are equal, it checks out."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=str(x), band="secundaria", key=f"eq|{eq}",
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en)


def fam_slope(r):
    x1, y1 = r.randint(-5, 1), r.randint(-5, 5)
    dx, dy = r.randint(1, 5), r.randint(-6, 6)
    x2, y2 = x1 + dx, y1 + dy
    if not (-6 <= y2 <= 6 and x2 <= 6):
        return None
    img, d = canvas(440, 440)
    o, u = 220, 32  # origen y unidad
    for i in range(-6, 7):
        d.line([(o + i * u, 28), (o + i * u, 412)], fill="#e5e7eb")
        d.line([(28, o + i * u), (412, o + i * u)], fill="#e5e7eb")
    d.line([(20, o), (420, o)], fill="black", width=2)
    d.line([(o, 20), (o, 420)], fill="black", width=2)
    fs = font("sans", 13)
    for i in range(-6, 7, 2):
        if i:
            ctext(d, (o + i * u, o + 14), str(i), fs)
            ctext(d, (o - 14, o - i * u), str(i), fs)
    m = Fraction(dy, dx)
    def P(x, y):
        return (o + x * u, o - y * u)
    # recta prolongada
    xa, xb = -7, 7
    d.line([P(xa, y1 + m * (xa - x1)), P(xb, y1 + m * (xb - x1))], fill="#1d4ed8", width=3)
    f = font("bold", 16)
    for (x, y) in [(x1, y1), (x2, y2)]:
        px, py = P(x, y)
        d.ellipse([px - 6, py - 6, px + 6, py + 6], fill="#d62828")
        d.text((px + 8, py - 24), f"({x}, {y})", font=f, fill="black")
    q_es, q_en = "Halla la pendiente de la recta que pasa por los dos puntos marcados.", "Find the slope of the line through the two marked points."
    se = ["Pendiente m = (y₂ - y₁) ÷ (x₂ - x₁).", f"m = ({y2} - ({y1})) ÷ ({x2} - ({x1})) = {dy} ÷ {dx} = {frac_str(m)}."]
    sn = ["Slope m = (y₂ - y₁) ÷ (x₂ - x₁).", f"m = ({y2} - ({y1})) ÷ ({x2} - ({x1})) = {dy} ÷ {dx} = {frac_str(m)}."]
    look_es = f"Una recta dibujada en una cuadrícula que pasa por los puntos ({x1}, {y1}) y ({x2}, {y2})."
    look_en = f"A line drawn on a grid that passes through the points ({x1}, {y1}) and ({x2}, {y2})."
    mov_es = "subo" if dy > 0 else "bajo" if dy < 0 else "no subo ni bajo"
    mov_en = "go up" if dy > 0 else "go down" if dy < 0 else "stay level"
    ck_es = f"Desde ({x1}, {y1}) avanzo {dx} a la derecha y {mov_es}{' ' + str(abs(dy)) if dy else ''}: llego a ({x2}, {y2}). Cuadra."
    ck_en = f"From ({x1}, {y1}) I move {dx} to the right and {mov_en}{' ' + str(abs(dy)) if dy else ''}: I reach ({x2}, {y2}). It checks out."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=frac_str(m), band="secundaria", key=f"slope|{x1}|{y1}|{x2}|{y2}",
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en)


def fam_pie(r, lang):
    cats = r.choice(CATS)[:4]
    names = [c[0] if lang == "es" else c[1] for c in cats]
    while True:
        cuts = sorted(r.sample(range(1, 20), 3))
        pcts = [b - a for a, b in zip([0] + cuts, cuts + [20])]
        pcts = [p * 5 for p in pcts]
        if min(pcts) >= 10:
            break
    total = r.choice([20, 40, 60, 80, 100, 120, 200, 300, 400])
    img, d = canvas(560, 400)
    cx, cy, R = 200, 200, 160
    pal = ["#ef4444", "#3b82f6", "#22c55e", "#eab308"]
    a0 = -90
    f = font("bold", 18)
    for p, col in zip(pcts, pal):
        a1 = a0 + 360 * p / 100
        d.pieslice([cx - R, cy - R, cx + R, cy + R], a0, a1, fill=col, outline="white", width=3)
        mid = math.radians((a0 + a1) / 2)
        ctext(d, (cx + 0.62 * R * math.cos(mid), cy + 0.62 * R * math.sin(mid)), f"{p}%", f, fill="white")
        a0 = a1
    for i, (nm, col) in enumerate(zip(names, pal)):
        d.rectangle([390, 120 + i * 40, 410, 140 + i * 40], fill=col)
        d.text((420, 120 + i * 40), nm, font=font("sans", 18), fill="black")
    i = r.randrange(4)
    ans = total * pcts[i] // 100
    q = L(lang, f"Se preguntó a {total} estudiantes. ¿Cuántos eligieron {names[i]}?", f"{total} students were asked. How many chose {names[i]}?")
    st = [L(lang, f"{names[i]} tiene el {pcts[i]}% del gráfico.", f"{names[i]} is {pcts[i]}% of the chart."),
          L(lang, f"{pcts[i]}% de {total} = {pcts[i]} ÷ 100 × {total} = {ans}.", f"{pcts[i]}% of {total} = {pcts[i]} ÷ 100 × {total} = {ans}.")]
    look = L(lang, "Un gráfico de pastel con 4 partes: " + ", ".join(f"{n} {p}%" for n, p in zip(names, pcts)) + ".",
             "A pie chart with 4 parts: " + ", ".join(f"{n} {p}%" for n, p in zip(names, pcts)) + ".")
    ck = L(lang, f"{ans} ÷ {total} = {fmt_num(Fraction(ans, total))} = {pcts[i]}%. Además, " + " + ".join(map(str, pcts)) + " = 100. Cuadra.",
           f"{ans} ÷ {total} = {fmt_num(Fraction(ans, total))} = {pcts[i]}%. Also " + " + ".join(map(str, pcts)) + " = 100. It checks out.")
    return dict(img=img, q=q, steps=st, answer=str(ans), band="secundaria", look=look, check=ck, key=f"pie|{names}|{pcts}|{total}|{i}")


def fam_cuboid(r):
    l, w, h = r.randint(2, 12), r.randint(2, 9), r.randint(2, 10)
    unit = r.choice(["cm", "m"])
    img, d = canvas(520, 400)
    sc = min(260 / l, 160 / h, 200 / w)
    ox, oy = 80, 340
    dx, dy = w * sc * 0.6, -w * sc * 0.45
    F = [(ox, oy), (ox + l * sc, oy), (ox + l * sc, oy - h * sc), (ox, oy - h * sc)]
    B = [(x + dx, y + dy) for x, y in F]
    d.polygon([F[3], F[2], B[2], B[3]], fill="#bfdbfe", outline="black")
    d.polygon([F[1], B[1], B[2], F[2]], fill="#93c5fd", outline="black")
    d.polygon(F, fill="#dbeafe", outline="black")
    for seg in [(F[0], F[1]), (F[1], F[2]), (F[2], F[3]), (F[3], F[0]), (F[1], B[1]), (B[1], B[2]), (F[2], B[2]), (F[3], B[3]), (B[3], B[2])]:
        d.line(seg, fill="black", width=3)
    f = font("sans", 20)
    ctext(d, ((F[0][0] + F[1][0]) / 2, oy + 20), f"{l} {unit}", f)
    ctext(d, (ox - 36, oy - h * sc / 2), f"{h} {unit}", f)
    ctext(d, ((F[1][0] + B[1][0]) / 2 + 34, (F[1][1] + B[1][1]) / 2 + 8), f"{w} {unit}", f)
    if r.random() < 0.6:
        q_es, q_en = "Halla el volumen de la caja.", "Find the volume of the box."
        se = ["Volumen = largo × ancho × alto.", f"Primero {l} × {w} = {l * w}.", f"Después {l * w} × {h} = {l * w * h} {unit}³."]
        sn = ["Volume = length × width × height.", f"First {l} × {w} = {l * w}.", f"Then {l * w} × {h} = {l * w * h} {unit}³."]
        ans = l * w * h
        ck_es, ck_en = f"En otro orden: {w} × {h} = {w * h}, y {w * h} × {l} = {ans}. Cuadra.", f"In another order: {w} × {h} = {w * h}, and {w * h} × {l} = {ans}. It checks out."
    else:
        q_es, q_en = "Halla el área total de la superficie de la caja.", "Find the total surface area of the box."
        A = 2 * (l * w + l * h + w * h)
        S = l * w + l * h + w * h
        se = ["La caja tiene 3 pares de caras iguales.", f"Caras: {l}×{w} = {l * w}, {l}×{h} = {l * h}, {w}×{h} = {w * h}.",
              f"Sumo una cara de cada par: {l * w} + {l * h} = {l * w + l * h}; {l * w + l * h} + {w * h} = {S}.",
              f"Como hay dos de cada una: Área = 2 × {S} = {A} {unit}²."]
        sn = ["The box has 3 pairs of equal faces.", f"Faces: {l}×{w} = {l * w}, {l}×{h} = {l * h}, {w}×{h} = {w * h}.",
              f"Add one face of each pair: {l * w} + {l * h} = {l * w + l * h}; {l * w + l * h} + {w * h} = {S}.",
              f"There are two of each: Area = 2 × {S} = {A} {unit}²."]
        ans = A
        ck_es = f"Cara por cara: {2 * l * w} + {2 * l * h} + {2 * w * h} = {A}. Cuadra."
        ck_en = f"Face by face: {2 * l * w} + {2 * l * h} + {2 * w * h} = {A}. It checks out."
    look_es = f"Una caja (prisma rectangular) de largo {l} {unit}, ancho {w} {unit} y alto {h} {unit}."
    look_en = f"A box (rectangular prism) {l} {unit} long, {w} {unit} wide and {h} {unit} tall."
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=str(ans), band="secundaria", key=f"box|{l}|{w}|{h}|{q_en[9:14]}",
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en)


def fam_sequence(r):
    if r.random() < 0.6:
        a, dd = r.randint(-20, 50), r.choice([2, 3, 4, 5, 6, 7, 9, 10, 11, -2, -3, -4, -5])
        seq = [a + i * dd for i in range(6)]
        se = [f"Miro la diferencia entre términos seguidos: {seq[1]} - {seq[0]} = {dd}, {seq[2]} - {seq[1]} = {dd}.",
              f"Siempre {'suma' if dd > 0 else 'resta'} {abs(dd)}.", f"Siguiente: {seq[4]} {'+' if dd > 0 else '-'} {abs(dd)} = {seq[5]}."]
        sn = [f"Look at the difference between consecutive terms: {seq[1]} - {seq[0]} = {dd}, {seq[2]} - {seq[1]} = {dd}.",
              f"It always {'adds' if dd > 0 else 'subtracts'} {abs(dd)}.", f"Next: {seq[4]} {'+' if dd > 0 else '-'} {abs(dd)} = {seq[5]}."]
        band, key = "primaria", f"seqA|{a}|{dd}"
        ck_es = f"La regla vale en todos: {seq[3]} - {seq[2]} = {dd}, {seq[4]} - {seq[3]} = {dd}, {seq[5]} - {seq[4]} = {dd}. Cuadra."
        ck_en = f"The rule holds everywhere: {seq[3]} - {seq[2]} = {dd}, {seq[4]} - {seq[3]} = {dd}, {seq[5]} - {seq[4]} = {dd}. It checks out."
    else:
        a, q = r.randint(1, 9), r.choice([2, 3, 4, 5])
        seq = [a * q ** i for i in range(6)]
        se = [f"Cada término se obtiene multiplicando el anterior: {seq[1]} ÷ {seq[0]} = {q}, {seq[2]} ÷ {seq[1]} = {q}.",
              f"Siguiente: {seq[4]} × {q} = {seq[5]}."]
        sn = [f"Each term is the previous one multiplied by a constant: {seq[1]} ÷ {seq[0]} = {q}, {seq[2]} ÷ {seq[1]} = {q}.",
              f"Next: {seq[4]} × {q} = {seq[5]}."]
        band, key = "secundaria", f"seqG|{a}|{q}"
        ck_es = f"La regla vale en todos: {seq[3]} × {q} = {seq[4]} y {seq[5]} ÷ {q} = {seq[4]}. Cuadra."
        ck_en = f"The rule holds everywhere: {seq[3]} × {q} = {seq[4]} and {seq[5]} ÷ {q} = {seq[4]}. It checks out."
    img, d = canvas(600, 180, "#fffef7")
    ctext(d, (300, 90), ",  ".join(map(str, seq[:5])) + ",  ?", font(r.choice(["hand", "sans", "serif"]), 40))
    q_es, q_en = "¿Qué número sigue en la sucesión?", "What number comes next in the sequence?"
    look_es = "Una sucesión de números: " + ", ".join(map(str, seq[:5])) + ", ?"
    look_en = "A sequence of numbers: " + ", ".join(map(str, seq[:5])) + ", ?"
    return dict(img=img, q_es=q_es, q_en=q_en, steps_es=se, steps_en=sn, answer=str(seq[5]), band=band, key=key,
                look_es=look_es, look_en=look_en, check_es=ck_es, check_en=ck_en)


# --------------------------------------------------------------------------- problemas de enunciado (v2)
NAMES = ["Ana", "Luis", "Sofía", "Mateo", "Valeria", "Diego", "Camila", "Andrés", "Emma", "Liam", "Lucía", "Tomás"]


def _hm(total_min):
    return f"{(total_min // 60 - 1) % 12 + 1}:{total_min % 60:02d}"


def _word_problem(r, lang):
    """Problemas de varios pasos en los dos idiomas, con datos, pasos y comprobación."""
    nm = r.choice(NAMES)
    t = r.choice(["descuento", "ahorro", "reparto", "sobran", "viaje", "pelicula", "receta", "cajas", "edades", "clase"])
    E = lang == "es"
    if t == "descuento":
        P, d = r.choice(range(20, 201, 20)), r.choice([10, 20, 25, 50])
        D = P * d // 100
        q = f"Una mochila cuesta ${P}. Hoy tiene un descuento del {d}%. ¿Cuánto cuesta ahora?" if E else \
            f"A backpack costs ${P}. Today it is {d}% off. How much does it cost now?"
        know = f"Precio ${P}; descuento {d}%." if E else f"Price ${P}; discount {d}%."
        st = [f"El descuento es el {d}% de {P}: {P} × {d} ÷ 100 = {D}." if E else f"The discount is {d}% of {P}: {P} × {d} ÷ 100 = {D}.",
              f"Precio nuevo: {P} - {D} = {P - D}." if E else f"New price: {P} - {D} = {P - D}."]
        ck = f"{P - D} + {D} = {P}. Cuadra." if E else f"{P - D} + {D} = {P}. It checks out."
        ans, band = P - D, "secundaria"
    elif t == "ahorro":
        sv, w = r.randint(2, 20), r.randint(2, 12)
        g = r.randint(1, sv * w - 1)
        q = f"{nm} ahorra ${sv} cada semana durante {w} semanas. Después gasta ${g} en un regalo. ¿Cuánto dinero le queda?" if E else \
            f"{nm} saves ${sv} every week for {w} weeks. Then {nm} spends ${g} on a gift. How much money is left?"
        know = f"Ahorra ${sv} por semana, {w} semanas; gasta ${g}." if E else f"Saves ${sv} per week for {w} weeks; spends ${g}."
        st = [f"Lo que ahorró: {sv} × {w} = {sv * w}." if E else f"Total saved: {sv} × {w} = {sv * w}.",
              f"Le quedan: {sv * w} - {g} = {sv * w - g}." if E else f"Money left: {sv * w} - {g} = {sv * w - g}."]
        ck = f"{sv * w - g} + {g} = {sv * w}. Cuadra." if E else f"{sv * w - g} + {g} = {sv * w}. It checks out."
        ans, band = sv * w - g, "primaria"
    elif t in ("reparto", "sobran"):
        k = r.randint(2, 9)
        each = r.randint(2, 15)
        rest = r.randint(1, k - 1) if t == "sobran" else 0
        N = k * each + rest
        if t == "reparto":
            q = f"Hay {N} caramelos para repartir en partes iguales entre {k} niños. ¿Cuántos caramelos le tocan a cada niño?" if E else \
                f"There are {N} candies to share equally among {k} children. How many candies does each child get?"
        else:
            q = f"{nm} reparte {N} caramelos en partes iguales entre {k} amigos y se queda con los que sobran. ¿Cuántos caramelos le sobran?" if E else \
                f"{nm} shares {N} candies equally among {k} friends and keeps the leftovers. How many candies are left over?"
        know = f"{N} caramelos, {k} personas, partes iguales." if E else f"{N} candies, {k} people, equal shares."
        st = [f"Divido {N} ÷ {k}: {k} × {each} = {k * each}" + (f", y {N} - {k * each} = {rest}." if rest else ", justo.") if E else
              f"Divide {N} ÷ {k}: {k} × {each} = {k * each}" + (f", and {N} - {k * each} = {rest}." if rest else ", exactly."),
              (f"A cada uno le tocan {each}" + (f" y sobran {rest}." if rest else ".")) if E else (f"Each one gets {each}" + (f" and {rest} are left over." if rest else "."))]
        ck = f"{k} × {each} + {rest} = {N}. Cuadra." if E else f"{k} × {each} + {rest} = {N}. It checks out."
        ans, band = (each if t == "reparto" else rest), "primaria"
    elif t == "viaje":
        v1, t1, v2, t2 = r.choice(range(30, 101, 10)), r.randint(1, 4), r.choice(range(30, 101, 10)), r.randint(1, 3)
        hs = lambda n: (f"{n} hora" if n == 1 else f"{n} horas") if E else (f"{n} hour" if n == 1 else f"{n} hours")
        q = f"Un autobús viaja a {v1} km/h durante {hs(t1)} y después a {v2} km/h durante {hs(t2)}. ¿Cuántos kilómetros recorre en total?" if E else \
            f"A bus travels at {v1} km/h for {hs(t1)} and then at {v2} km/h for {hs(t2)}. How many kilometers does it travel in total?"
        know = f"Tramo 1: {v1} km/h, {t1} h. Tramo 2: {v2} km/h, {t2} h." if E else f"Part 1: {v1} km/h, {t1} h. Part 2: {v2} km/h, {t2} h."
        st = [f"Distancia = velocidad × tiempo." if E else "Distance = speed × time.",
              f"Tramo 1: {v1} × {t1} = {v1 * t1} km." if E else f"Part 1: {v1} × {t1} = {v1 * t1} km.",
              f"Tramo 2: {v2} × {t2} = {v2 * t2} km." if E else f"Part 2: {v2} × {t2} = {v2 * t2} km.",
              f"Total: {v1 * t1} + {v2 * t2} = {v1 * t1 + v2 * t2} km."]
        ck = f"{v1 * t1 + v2 * t2} - {v2 * t2} = {v1 * t1}, que es el primer tramo. Cuadra." if E else \
             f"{v1 * t1 + v2 * t2} - {v2 * t2} = {v1 * t1}, which is the first part. It checks out."
        ans, band = v1 * t1 + v2 * t2, "primaria"
    elif t == "pelicula":
        h, m = r.randint(1, 10), r.choice(range(0, 60, 5))
        M = r.choice(range(70, 181, 5))
        start = h * 60 + m
        q = f"Una película empieza a las {h}:{m:02d} y dura {M} minutos. ¿A qué hora termina?" if E else \
            f"A movie starts at {h}:{m:02d} and lasts {M} minutes. What time does it end?"
        know = f"Empieza a las {h}:{m:02d}; dura {M} minutos." if E else f"Starts at {h}:{m:02d}; lasts {M} minutes."
        hh, mm = divmod(M, 60)
        st = [f"{M} minutos = {hh} h y {mm} min." if E else f"{M} minutes = {hh} h and {mm} min.",
              f"{h}:{m:02d} + {hh} h = {_hm(start + hh * 60)}." ,
              f"{_hm(start + hh * 60)} + {mm} min = {_hm(start + M)}."]
        ck = f"Desde las {h}:{m:02d} hasta las {_hm(start + M)} pasan {M} minutos. Cuadra." if E else \
             f"From {h}:{m:02d} to {_hm(start + M)} is {M} minutes. It checks out."
        ans, band = _hm(start + M), "primaria"
    elif t == "receta":
        p1 = r.choice([2, 3, 4, 5, 6])
        per = r.randint(1, 4)
        q1 = per * p1
        p2 = p1 * r.randint(2, 5) if r.random() < 0.5 else r.choice([x for x in range(2, 13) if x != p1])
        q2 = Fraction(q1 * p2, p1)
        if q2.denominator != 1:
            return None
        q = f"Para {p1} personas se necesitan {q1} tazas de harina. ¿Cuántas tazas se necesitan para {p2} personas?" if E else \
            f"A recipe for {p1} people needs {q1} cups of flour. How many cups are needed for {p2} people?"
        know = f"{p1} personas → {q1} tazas; ahora son {p2} personas." if E else f"{p1} people → {q1} cups; now there are {p2} people."
        st = [f"Para 1 persona: {q1} ÷ {p1} = {per} tazas." if E else f"For 1 person: {q1} ÷ {p1} = {per} cups.",
              f"Para {p2} personas: {per} × {p2} = {int(q2)} tazas." if E else f"For {p2} people: {per} × {p2} = {int(q2)} cups."]
        ck = f"{int(q2)} ÷ {p2} = {per} taza(s) por persona, igual que antes. Cuadra." if E else \
             f"{int(q2)} ÷ {p2} = {per} cup(s) per person, same as before. It checks out."
        ans, band = int(q2), "secundaria"
    elif t == "cajas":
        c, u = r.randint(2, 9), r.choice([6, 8, 10, 12, 24])
        g = r.randint(1, c * u - 1)
        q = f"{nm} compra {c} cajas de lápices con {u} lápices cada una. Regala {g} lápices a sus amigos. ¿Cuántos lápices le quedan?" if E else \
            f"{nm} buys {c} boxes of pencils with {u} pencils in each box. {nm} gives away {g} pencils. How many pencils are left?"
        know = f"{c} cajas × {u} lápices; regala {g}." if E else f"{c} boxes × {u} pencils; gives away {g}."
        st = [f"Lápices en total: {c} × {u} = {c * u}." if E else f"Total pencils: {c} × {u} = {c * u}.",
              f"Le quedan: {c * u} - {g} = {c * u - g}." if E else f"Pencils left: {c * u} - {g} = {c * u - g}."]
        ck = f"{c * u - g} + {g} = {c * u}. Cuadra." if E else f"{c * u - g} + {g} = {c * u}. It checks out."
        ans, band = c * u - g, "primaria"
    elif t == "edades":
        a, k = r.randint(4, 12), r.randint(3, 5)
        a2 = a + r.randint(2, 15)
        mom = a * k
        q = f"{nm} tiene {a} años y su mamá tiene {k} veces su edad. ¿Cuántos años tendrá la mamá cuando {nm} tenga {a2} años?" if E else \
            f"{nm} is {a} years old and {nm}'s mom is {k} times that age. How old will the mom be when {nm} is {a2}?"
        know = f"{nm}: {a} años; mamá: {k} veces más; futuro: {nm} con {a2} años." if E else f"{nm}: {a} years old; mom: {k} times as old; later: {nm} is {a2}."
        st = [f"Edad de la mamá ahora: {a} × {k} = {mom}." if E else f"Mom's age now: {a} × {k} = {mom}.",
              f"Años que pasan: {a2} - {a} = {a2 - a}." if E else f"Years that pass: {a2} - {a} = {a2 - a}.",
              f"La mamá tendrá {mom} + {a2 - a} = {mom + a2 - a} años." if E else f"Mom will be {mom} + {a2 - a} = {mom + a2 - a}."]
        ck = f"La diferencia de edad no cambia: {mom} - {a} = {mom - a} y {mom + a2 - a} - {a2} = {mom - a}. Cuadra." if E else \
             f"The age gap never changes: {mom} - {a} = {mom - a} and {mom + a2 - a} - {a2} = {mom - a}. It checks out."
        ans, band = mom + a2 - a, "primaria"
    else:  # clase
        N = r.choice([20, 24, 25, 30, 32, 36, 40])
        p = r.choice([x for x in (10, 20, 25, 40, 50, 60, 75, 80) if N * x % 100 == 0])
        girls = N * p // 100
        q = f"En una clase de {N} estudiantes, el {p}% son niñas. ¿Cuántos niños hay?" if E else \
            f"In a class of {N} students, {p}% are girls. How many boys are there?"
        know = f"{N} estudiantes; {p}% niñas." if E else f"{N} students; {p}% girls."
        st = [f"Niñas: {p}% de {N} = {N} × {p} ÷ 100 = {girls}." if E else f"Girls: {p}% of {N} = {N} × {p} ÷ 100 = {girls}.",
              f"Niños: {N} - {girls} = {N - girls}." if E else f"Boys: {N} - {girls} = {N - girls}."]
        ck = f"El {100 - p}% de {N} = {N * (100 - p) // 100}. Cuadra." if E else f"{100 - p}% of {N} = {N * (100 - p) // 100}. It checks out."
        ans, band = N - girls, "secundaria"
    img = render_text_card(q, r)
    return dict(img=img, q=q, steps=st, answer=str(ans), band=band, look=know, check=ck, text_in_image=True,
                key=f"word|{t}|{q}")


def render_text_card(text, r):
    """Enunciado escrito como en una hoja de tareas."""
    W = 640
    f = font(text_font(r), r.choice([22, 24, 26]))
    tmp = ImageDraw.Draw(Image.new("RGB", (W, 10)))
    lines = wrap(tmp, text, f, W - 80)
    lh = int(f.size * 1.45)
    img = Image.new("RGB", (W, 40 + lh * len(lines) + 30), "white")
    d = ImageDraw.Draw(img)
    if r.random() < 0.5:
        for y in range(40 + lh - 6, img.height, lh):
            d.line([(20, y), (W - 20, y)], fill="#c7d7f0", width=1)
    ink = r.choice(["black", "#1f2a44", "#202020"])
    for i, ln in enumerate(lines):
        d.text((50, 30 + i * lh), ln, font=f, fill=ink)
    return img


# familia -> (función, recibe idioma?, peso)
FAMILIES = {
    "counting": (fam_counting, False, 1.0), "clock": (fam_clock, False, 1.0), "fraction": (fam_fraction, False, 1.0),
    "barchart": (fam_barchart, True, 1.2), "rectangle": (fam_rectangle, False, 1.2), "numberline": (fam_numberline, False, 1.0),
    "prices": (fam_prices, True, 1.0), "column_op": (fam_column_op, False, 1.0), "triangle": (fam_triangle, False, 1.0),
    "pythagoras": (fam_pythagoras, False, 0.8), "circle": (fam_circle, False, 0.8), "equation": (fam_equation, False, 1.2),
    "slope": (fam_slope, False, 0.8), "pie": (fam_pie, True, 0.8), "cuboid": (fam_cuboid, False, 0.8), "sequence": (fam_sequence, False, 1.0),
}
# Familias nuevas de la v2. Van aparte para que el examen (generado con la lista de arriba) no cambie.
FAMILIES_V2 = {**FAMILIES, "word": (_word_problem, True, 3.0)}

# --------------------------------------------------------------------------- presentación
SYSTEM_PROMPT = (
    "You are Vertex-Math-Vision, a math tutor for elementary, middle and high school students, made by Vertex Coders LLC. "
    "Look carefully at the image, explain the solution in short, clear steps, and end with the final answer inside \\boxed{}. "
    "Language rule: reply in the language of the student's message. If the student writes in English, reply in English. "
    "Si el estudiante escribe en español, responde en español."
)

GENERIC = {
    "es": ["Resuelve este problema.", "¿Me ayudas con este ejercicio?", "Explícame cómo se resuelve esto.", "No entiendo este ejercicio, ¿cómo se hace?"],
    "en": ["Solve this problem.", "Can you help me with this exercise?", "Explain how to solve this.", "I don't get this one. How do I do it?"],
}


def render_question_on_top(img, question, r):
    """Pone el enunciado arriba de la imagen, como en una hoja de tareas."""
    f = font(text_font(r), 22)
    tmp = ImageDraw.Draw(img)
    lines = wrap(tmp, question, f, img.width - 40)
    top = 20 + 30 * len(lines)
    out = Image.new("RGB", (img.width, img.height + top), "white")
    out.paste(img, (0, top))
    d = ImageDraw.Draw(out)
    for i, ln in enumerate(lines):
        d.text((20, 14 + i * 30), ln, font=f, fill="black")
    return out


def photo_effect(img, r):
    """Simula una foto de celular: papel, rotación leve, ruido y desenfoque."""
    paper = r.choice([(255, 253, 245), (245, 245, 240), (250, 248, 235), (240, 244, 250)])
    bg = Image.new("RGB", img.size, paper)
    img = Image.blend(img, bg, 0.12)
    img = img.rotate(r.uniform(-4, 4), resample=Image.BICUBIC, expand=True, fillcolor=paper)
    if r.random() < 0.6:
        img = img.filter(ImageFilter.GaussianBlur(r.uniform(0.3, 1.0)))
    noise = Image.effect_noise(img.size, r.uniform(20, 45)).convert("RGB")
    img = Image.blend(img, noise, r.uniform(0.04, 0.10))
    return img


def build_response(lang, steps, answer, question=None, look=None, check=None, word=False):
    """v1: solo pasos. v2 (si llegan question/look/check): qué piden, qué veo, pasos y comprobación."""
    es = lang == "es"
    label = "Paso" if es else "Step"
    parts = []
    if question:
        parts.append(f"**{'Lo que me piden' if es else 'What I need to find'}:** {question}")
    if look:
        tag = ("Lo que sé" if es else "What I know") if word else ("Lo que veo" if es else "What I see")
        parts.append(f"**{tag}:** {look}")
    parts += [f"**{label} {i + 1}:** {s}" for i, s in enumerate(steps)]
    if check:
        parts.append(f"**{'Comprobación' if es else 'Check'}:** {check}")
    final = "Respuesta" if es else "Answer"
    return "\n".join(parts) + f"\n\n**{final}:** $\\boxed{{{answer}}}$"


def make_sample(r, family, lang, v2=False):
    fams = FAMILIES_V2 if v2 else FAMILIES
    fn, takes_lang, _ = fams[family]
    out = fn(r, lang) if takes_lang else fn(r)
    if out is None:
        return None
    if takes_lang:
        q, steps, look, check = out["q"], out["steps"], out.get("look"), out.get("check")
    else:
        q = out["q_es"] if lang == "es" else out["q_en"]
        steps = out["steps_es"] if lang == "es" else out["steps_en"]
        look, check = out.get(f"look_{lang}"), out.get(f"check_{lang}")
    img = out["img"]
    if out.get("text_in_image"):
        prompt = r.choice(GENERIC[lang])
    elif r.random() < 0.35:  # enunciado dentro de la imagen; el estudiante solo pide ayuda
        img = render_question_on_top(img, q, r)
        prompt = r.choice(GENERIC[lang])
    else:
        prompt = q
    if r.random() < 0.4:
        img = photo_effect(img, r)
    if v2:
        response = build_response(lang, steps, out["answer"], question=q, look=look, check=check, word=family == "word")
    else:
        response = build_response(lang, steps, out["answer"])
    return dict(img=img, prompt=prompt, question=q, response=response,
                answer=out["answer"], band=out["band"], key=f"{family}|{out['key']}")


def generate(n, seed, out_dir: Path, split, forbidden_keys=frozenset(), unique=True, v2=False):
    r = random.Random(seed)
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    fams = FAMILIES_V2 if v2 else FAMILIES
    names = list(fams)
    weights = [fams[k][2] for k in names]
    rows, keys = [], set()
    tries = 0
    while len(rows) < n:
        tries += 1
        if tries > n * 20:
            raise RuntimeError("Demasiados intentos fallidos generando muestras")
        family = r.choices(names, weights)[0]
        lang = "es" if r.random() < 0.5 else "en"
        s = make_sample(r, family, lang, v2=v2)
        if s is None:
            continue
        k = hashlib.sha1(s["key"].encode()).hexdigest()[:16]
        if k in forbidden_keys or (unique and k in keys):
            continue
        keys.add(k)
        sid = f"{split}-{len(rows):06d}"
        rel = f"images/{sid}.jpg"
        s["img"].convert("RGB").save(out_dir / rel, quality=90)
        rows.append(dict(id=sid, source="synth", family=family, lang=lang, band=s["band"], image=rel,
                         prompt=s["prompt"], question=s["question"], response=s["response"], answer=s["answer"], key=k))
    with open(out_dir / f"{split}.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return keys, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=int, default=12000)
    ap.add_argument("--eval", type=int, default=600)
    ap.add_argument("--out", default="data/synth")
    ap.add_argument("--v2", action="store_true", help="formato v2 (qué piden, qué veo, pasos, comprobación) + problemas de enunciado")
    ap.add_argument("--forbid", default=None, help="eval.jsonl ya existente: solo se genera train y nunca repite sus problemas")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.forbid:
        ev_rows = [json.loads(l) for l in open(args.forbid, encoding="utf-8")]
        forbidden = frozenset(row["key"] for row in ev_rows)
        _, tr = generate(args.train, 3407 + (1 if args.v2 else 0), out, "train", forbidden_keys=forbidden, unique=False, v2=args.v2)
        from collections import Counter
        print(f"[+] train: {len(tr)} muestras | idiomas {dict(Counter(r['lang'] for r in tr))} | {dict(Counter(r['band'] for r in tr))}")
        print("    familias:", dict(sorted(Counter(r["family"] for r in tr).items())))
        print(f"[+] Listo en {out.resolve()} (examen intacto: {args.forbid})")
        return
    # el examen se genera primero; el entrenamiento nunca repite un problema del examen
    eval_keys, ev = generate(args.eval, 20261021, out, "eval")
    # en train se permite repetir un mismo problema con otra presentación; lo que nunca se repite es el examen
    _, tr = generate(args.train, 3407, out, "train", forbidden_keys=frozenset(eval_keys), unique=False)
    from collections import Counter
    for name, rows in (("eval", ev), ("train", tr)):
        c = Counter(r["family"] for r in rows)
        lang = Counter(r["lang"] for r in rows)
        band = Counter(r["band"] for r in rows)
        print(f"[+] {name}: {len(rows)} muestras | idiomas {dict(lang)} | {dict(band)}")
        print("    familias:", dict(sorted(c.items())))
    print(f"[+] Listo en {out.resolve()}")


if __name__ == "__main__":
    main()
