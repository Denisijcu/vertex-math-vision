---
title: Vertex Math Vision
emoji: 📐
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 6.27.0
app_file: app.py
python_version: "3.10"
pinned: false
license: apache-2.0
short_description: Tutor de matemáticas con foto, paso a paso y verificado
models:
- Denisijcu/vertex-math-vision
- Qwen/Qwen3-VL-2B-Instruct
---

# Vertex Math Vision — Demo

Tutor de matemáticas para primaria y secundaria de **Vertex Coders LLC**, en español e inglés.
Saca una foto del ejercicio (aunque esté escrito a mano) o escríbelo, y recibe la solución paso a paso.

**Cómo funciona**

1. El modelo copia el ejercicio de la foto **sin resolverlo**.
2. Tú revisas lo que leyó y lo corriges si hace falta.
3. Lo resuelve paso a paso.
4. Una calculadora simbólica (**SymPy**) comprueba la respuesta. Si el problema no se puede comprobar entero,
   revisa al menos las cuentas de cada paso. Cada respuesta lleva una etiqueta honesta:
   Verificado · No coincide · Mal planteado · Cuentas correctas · Hay una cuenta mal · Sin verificar.

**Modelo:** [Denisijcu/vertex-math-vision](https://huggingface.co/Denisijcu/vertex-math-vision), Qwen3-VL-2B-Instruct
afinado con QLoRA. Corre en ZeroGPU; si se agota tu cuota de GPU, responde en CPU con el mismo modelo (más lento).

**Otras formas de usarlo**

- App web: [vertex-math-vision.netlify.app](https://vertex-math-vision.netlify.app)
- Sin internet, en tu PC con LM Studio: [Denisijcu/vertex-math-vision-GGUF](https://huggingface.co/Denisijcu/vertex-math-vision-GGUF)

**Privacidad:** las fotos no se guardan. Se les quitan los metadatos (EXIF/GPS), se usan para responder y se descartan.

**Límites:** es un modelo pequeño (2B). Lee muy bien ejercicios escritos e impresos, pero falla con dibujos
(relojes, gráficas, dados) y con razonamientos largos. Úsalo para aprender, no para copiar.

**Licencia:** Qwen3-VL-2B-Instruct y el adaptador, Apache 2.0.
