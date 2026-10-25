"""Prompts y lectura de respuestas del modelo. Los comparten el backend local (LM Studio) y el Space de Hugging Face,
así los dos se comportan igual."""
import re

# El mismo system prompt del entrenamiento (scripts/gen_synth.py). No cambiarlo sin reentrenar.
SYSTEM_PROMPT = (
    "You are Vertex-Math-Vision, a math tutor for elementary, middle and high school students, made by Vertex Coders LLC. "
    "Look carefully at the image, explain the solution in short, clear steps, and end with the final answer inside \\boxed{}. "
    "Language rule: reply in the language of the student's message. If the student writes in English, reply in English. "
    "Si el estudiante escribe en español, responde en español."
)

READ_PROMPT = {
    "es": (
        "No resuelvas nada y no hagas ninguna cuenta: no escribas resultados. Copia exactamente el ejercicio de matemáticas que aparece en la imagen, en una sola línea, "
        "usando ^ para las potencias y sqrt() para las raíces. Si hay varios ejercicios, escribe uno por línea empezando "
        "por 1), 2), 3). Si en la imagen no hay ningún ejercicio de matemáticas, escribe solo: NO_MATH"
    ),
    "en": (
        "Do not solve anything and do not calculate: write no results. Copy exactly the math exercise shown in the image, on a single line, using ^ for powers "
        "and sqrt() for roots. If there are several exercises, write one per line starting with 1), 2), 3). "
        "If there is no math exercise in the image, write only: NO_MATH"
    ),
}

DEFAULT_ASK = {"es": "Resuelve este problema.", "en": "Solve this problem."}


def build_ask(student_text: str, confirmed_reading: str, lang: str) -> str:
    """Texto del estudiante para la llamada de resolver. Si confirmó o corrigió la lectura, se le pasa al modelo
    para que no relea mal la foto."""
    ask = student_text or DEFAULT_ASK[lang]
    if confirmed_reading:
        ask = f"{ask}\nEl ejercicio es: {confirmed_reading}" if lang == "es" else f"{ask}\nThe exercise is: {confirmed_reading}"
    return ask


_COMPUTED = re.compile(r"^[\d\s+\-*/×÷·().,^]+=\s*-?\d+(?:[.,]\d+)?\s*$")


def parse_reading(raw: str) -> tuple[str, bool, list[str]]:
    """Interpreta la transcripción. El modelo está afinado para resolver, así que si se pone a resolver
    de todas formas, nos quedamos solo con lo anterior a los pasos."""
    text = raw.strip()
    if re.fullmatch(r"\W*NO_MATH\W*", text, flags=re.I) or text.upper().startswith("NO_MATH"):
        return "", False, []
    # cortar si empezó a resolver
    text = re.split(r"\*\*(?:Step|Paso)\s*1|\\boxed|\*\*(?:Answer|Respuesta)", text, maxsplit=1, flags=re.I)[0]
    text = re.sub(r"\*\*(?:What I need to find|What I see|Pregunta|Qu[eé] (?:me )?piden|Qu[eé] veo)[^*]*\*\*:?", "", text, flags=re.I)
    lines = [l.strip(" *-\t") for l in text.splitlines() if l.strip(" *-\t")]
    # A veces añade "NO_MATH" al final aunque sí copió un ejercicio: esa línea sobra.
    lines = [l for l in lines if not re.fullmatch(r"\W*NO_MATH\W*", l, flags=re.I)]
    # Si el modelo coló una cuenta ya hecha ("(120-40)+25=95"), es un resultado, no parte del ejercicio: fuera.
    # Solo cuando hay más líneas; un ejercicio de una sola línea se deja tal cual.
    if len(lines) > 1:
        kept = [l for l in lines if not _COMPUTED.match(re.sub(r"^\d+\)\s*", "", l))]
        lines = kept or lines
    problems = [re.sub(r"^\d+\)\s*", "", l) for l in lines if re.match(r"^\d+\)\s*", l)]
    reading = "\n".join(lines)[:1000]
    if not reading:
        return "", False, []
    return reading, True, problems if len(problems) > 1 else []
