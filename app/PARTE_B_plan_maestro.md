# Vertex-Math-Vision App — Parte B del Plan Maestro v2

> Se usa con la **Parte A (Constitución)** de `F:\Plan_Maestro\Plan Maestro v2 - Generador Web Fullstack Vertex.md`.
> La Parte A se pensó para una tienda (catálogo, carrito). Esta app no vende nada, así que abajo, en
> **"Ajustes a la Parte A"**, se dice qué se cambia y por qué. Todo lo demás de la Parte A se cumple tal cual:
> calidad, seguridad, accesibilidad, SEO, README con directorio por comando, tests y checklist A8.

---

## 1. Qué es

Un tutor de matemáticas para **primaria y secundaria**: el estudiante saca una foto a un ejercicio
(o lo escribe) y recibe la solución paso a paso, en **español o inglés**. Usa el modelo propio
**Vertex-Math-Vision 2B v2**.

**Principio central: nunca presentar una respuesta falsa con cara de segura.** En las pruebas
el modelo lee muy bien, pero en problemas largos, sin solución limpia, o al leer relojes y gráficas
a mano, se equivoca y además "comprueba" que cuadra. Por eso cada respuesta lleva una etiqueta
honesta, verificada por una calculadora simbólica cuando se puede.

## 2. Flujo de una pregunta

1. **Entrada:** una foto (cámara del móvil o archivo) y, opcional, un texto ("Resuelve", "¿cuánto vale x?").
   Cada foto es una **conversación nueva**: no se arrastra nada de la anterior.
2. **Guard** (`guard.py`): tipo y tamaño de archivo, longitud del texto, rate limit, inyección; Portero opcional.
3. **Lectura** (llamada 1 al modelo): *"Transcribe exactamente el problema de la imagen, sin resolverlo."*
   Devuelve también si ve un problema de matemáticas o no, y cuántos ejercicios hay.
4. **Confirmación:** la app enseña **"Leí esto: …"**. El estudiante puede corregirlo antes de seguir.
5. **Solución** (llamada 2): el modelo resuelve paso a paso con el formato del entrenamiento.
6. **Verificación** (`verify.py`, SymPy): si la transcripción es una ecuación, una expresión o una cuenta,
   SymPy la resuelve por su cuenta y la compara con el `\boxed{}` del modelo.
7. **Resultado** con una de estas etiquetas:
   - ✅ **Verificado:** SymPy coincide.
   - ⚠️ **No coincide:** se muestra la respuesta de SymPy al lado y se avisa al estudiante.
   - ℹ️ **Sin verificar:** problemas de texto, relojes, gráficas, geometría con figura. "Revisa el resultado".
   - 🚫 **No es un ejercicio:** "No veo un problema de matemáticas en esta foto".

## 3. Casos de entrada que se manejan (no solo la entrada "buena")

| Entrada | Comportamiento |
|---|---|
| Problema bien planteado | Resuelve + verifica con SymPy cuando se puede |
| Mal planteado (sin "=", incompleto) | SymPy lo detecta; la app pregunta: "No hay signo igual, ¿lo igualo a 0?" |
| Sin solución real | SymPy lo dice: "No tiene solución en los números reales" |
| Foto borrosa, oscura o torcida | Se enseña lo leído para que el estudiante lo corrija |
| Foto que no es de matemáticas | Mensaje amable, sin respuesta inventada |
| Varios ejercicios en la misma foto | Se listan y el estudiante elige uno (o "todos") |
| Solo texto, sin foto | Se acepta; mismo flujo desde el paso 5 |
| Archivo enorme, formato raro, HEIC | Límite de tamaño, conversión a JPEG/PNG o error claro |
| "Ignora tus instrucciones…" | Guard / Portero → HTTP 400 `MESSAGE_REJECTED` con mensaje amable |
| El modelo no responde (Space dormido, timeout) | `source: "fallback"`: "El tutor está despertando, prueba en un minuto"; nunca un 500 |

## 4. Ajustes a la Parte A (y por qué)

| Parte A dice | En esta app | Motivo |
|---|---|---|
| `GET /products`, CSV, carrito, `Product` JSON-LD | **No existen** | No es una tienda |
| `POST /chat` (texto) | **`POST /solve`** (multipart: `image` opcional + `text` + `lang`) | La entrada principal es una foto |
| — | **`POST /read`** (solo transcribe, para el paso de confirmación) | Separar leer de resolver |
| LLM: `POST {LLM_BASE_URL}/chat/completions` | Se mantiene, con la imagen en base64 (formato OpenAI de visión) | Funciona igual con **LM Studio** en local y con el servidor del Space |
| `POST /contact` | Se mantiene, como **"Reportar un error del tutor"** (con honeypot). **Solo texto: nunca se guarda la foto** | Recoger los fallos reales sirve para la v3, sin guardar fotos de menores |
| A1/A3: `frontend/index.html` single-file con Tailwind Play CDN | **`frontend/` es una app Angular 21 standalone** (CLI 21.2 instalado), Tailwind compilado en el build, signals, rutas con lazy loading, i18n ES/EN propio | Decisión de Denis: Angular, bonita y profesional. Todo lo demás de A3, A4 y A5 se cumple igual dentro de Angular |
| `services/catalog.py` | Se sustituye por **`services/verify.py`** (SymPy) | La pieza clave de esta app |
| `privacidad.html` | Se mantiene y **se refuerza**: usuarios menores de edad, las fotos no se guardan | Público escolar |
| Testimonios | **Ninguno** | No hay testimonios reales todavía |

Contrato de `POST /solve` → `{"reading": str, "steps": str, "answer": str|null, "verification": "verified|mismatch|unverified|not_math", "sympy_answer": str|null, "lang": "es|en", "source": "llm|fallback"}`.

## 5. Despliegue (como el ajedrez)

- **Modelo:** `Denisijcu/vertex-math-vision` (adaptador) y `Denisijcu/vertex-math-vision-GGUF`.
- **Backend:** Space de Hugging Face. Opción preferida: ZeroGPU con transformers + el adaptador;
  respaldo en CPU si la GPU no está disponible (más lento: se avisa en la interfaz).
  En local, el mismo backend apunta a LM Studio (`LLM_BASE_URL=http://127.0.0.1:1234/v1`).
- **Frontend:** Angular 21 en Netlify (build `ng build`, carpeta `dist/.../browser`, redirección SPA en `netlify.toml`). Sin subdominio propio por ahora: se usa el que asigne Netlify.
- **Descarga para estudiantes:** sección "Úsalo sin internet" con los pasos de LM Studio y el enlace al GGUF.

## 6. Variables

```yaml
SLUG: vertex-math-vision-app
EMPRESA: Vertex Coders LLC
MARCA: Vertex Math Vision
AÑO: 2026
DOMINIO: ""                       # sin subdominio propio por ahora (decisión de Denis)
IDIOMA: es                        # con selector ES/EN, como vertex-services.org
LOCALE: es-US
TITLE_SEO: "Vertex Math Vision — Tu tutor de matemáticas con una foto"
DESCRIPCION_SEO: "Saca una foto a tu ejercicio y aprende a resolverlo paso a paso, en español o inglés. Tutor de matemáticas para primaria y secundaria, hecho por Vertex Coders."
NOMBRE_ASISTENTE: Vertex Math Vision

DESIGN_SYSTEM:                    # mismo lenguaje visual que vertex-services.org
  fondo: "#09090b"
  acento_primario: cyan-400
  acento_secundario: violet-500
  estilo: "dark, glassmorphism, tarjetas con borde sutil, gradiente cian→violeta"
  tipografia: Inter
  extra: "fórmulas renderizadas con KaTeX; botón de cámara grande, pensado para el móvil"

NAVBAR:
  enlaces: [Inicio, Cómo funciona, Úsalo sin internet, Preguntas, Reportar un error]
  extra: "estado del tutor (verde/amarillo/rojo según GET /health) + selector ES/EN"

HERO:
  titulo: "Sácale una foto. Entiéndelo paso a paso."
  subtitulo: "Tu tutor de matemáticas para primaria y secundaria, en español o inglés."
  cta_primario: "Tomar foto"          # abre la cámara en el móvil / selector de archivo en PC
  cta_secundario: "Escribir el ejercicio"

COMO_FUNCIONA:
  - {icono: camera,        titulo: "1. Foto",       texto: "Saca una foto clara del ejercicio, aunque esté escrito a mano."}
  - {icono: scan-text,     titulo: "2. Revisa",     texto: "Te enseñamos lo que leímos para que lo corrijas si hace falta."}
  - {icono: list-ordered,  titulo: "3. Aprende",    texto: "La solución paso a paso, no solo el resultado."}
  - {icono: shield-check,  titulo: "4. Verificado", texto: "Una calculadora comprueba la respuesta cuando es posible. Si no puede, te lo decimos."}

AVISO_HONESTO: "Vertex Math Vision es un modelo pequeño y puede equivocarse. Úsalo para aprender, no para copiar: revisa siempre los pasos."

FAQ:
  - {p: "¿Es gratis?", r: "Sí."}
  - {p: "¿Guardan mis fotos?", r: "No. La foto se usa solo para resolver el ejercicio y se descarta."}
  - {p: "¿Puedo usarlo sin internet?", r: "Sí: descarga el modelo en LM Studio. Te explicamos cómo en «Úsalo sin internet»."}
  - {p: "¿Qué significa «Sin verificar»?", r: "Que la calculadora no puede comprobar ese tipo de problema (texto, relojes, gráficas). Revisa el resultado con más cuidado."}
  - {p: "¿Para qué cursos sirve?", r: "Primaria y secundaria. No está pensado para universidad."}

CONTACTO:
  email: "contact@vertexcoders.com"   # el de vertex-services.org
  web: "https://vertex-services.org"

LLM:
  base_url: "http://127.0.0.1:1234/v1"   # LM Studio en local; en el Space, el servidor propio
  model: "vertex-math-vision-v2"
  portero_url: ""
```

## 7. Decisiones de Denis (24-oct-2026)

1. **Frontend en Angular**, "bien bonita y profesional", siguiendo las normas de la Parte A.
2. **No se guardan fotos.** Los reportes de error son solo texto.
3. **Sin subdominio propio** por ahora.
