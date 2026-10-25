---
title: Vertex Math Vision API
emoji: 📐
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 6.27.0
app_file: app.py
python_version: "3.10"
pinned: false
license: apache-2.0
short_description: Backend del tutor de matemáticas con foto de Vertex Coders
models:
- Denisijcu/vertex-math-vision
- Qwen/Qwen3-VL-2B-Instruct
---

# Vertex Math Vision — API (ZeroGPU)

Backend del tutor de matemáticas para primaria y secundaria de **Vertex Coders LLC**. Genera las respuestas con
[Denisijcu/vertex-math-vision](https://huggingface.co/Denisijcu/vertex-math-vision) (Qwen3-VL-2B-Instruct afinado
con QLoRA) y comprueba cada resultado con una calculadora simbólica (SymPy) cuando es posible.

- **Fotos:** no se guardan. Se validan, se les quitan los metadatos (EXIF/GPS) y se descartan.
- **Reportes de error:** solo texto.
- **Cuota:** la GPU de ZeroGPU la gasta quien usa el tutor. Cuando se acaba, la respuesta se genera en CPU con el
  mismo modelo (fusionado e int8): más lenta, pero sin límite.

**Licencia:** Qwen3-VL-2B-Instruct y el adaptador, Apache 2.0.
