# Vertex Math Vision — App para estudiantes

Tutor de matemáticas para primaria y secundaria: el estudiante saca una foto a un ejercicio (o lo escribe)
y recibe la solución paso a paso, en español o inglés, con el modelo propio **Vertex-Math-Vision 2B v2**.

**Principio central:** nunca enseñar una respuesta falsa con cara de segura. Cada respuesta lleva una
etiqueta honesta, comprobada con una calculadora simbólica (SymPy) cuando se puede:
✅ Verificado · ⚠️ No coincide · ⚠️ Mal planteado · ℹ️ Cuentas correctas (planteamiento sin verificar) · ⚠️ Hay una cuenta mal · ℹ️ Sin verificar · 🚫 No es un ejercicio.

Cuando el problema no se puede comprobar entero (problemas de texto, relojes, gráficas), SymPy revisa al menos
las cuentas de cada paso ("120 − 40 = 80") y dice en qué paso hay un error.

Diseño y decisiones: `PARTE_B_plan_maestro.md` (se usa con la Parte A del Plan Maestro v2).

## Stack

| Parte | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SymPy, Pillow, httpx |
| Frontend | Angular 21 (standalone, signals, zoneless), Tailwind CSS 4, KaTeX, Lucide |
| Modelo en local | LM Studio con `vertex-math-vision-v2` (GGUF + mmproj) |
| Producción | Backend en un Space de Hugging Face (Gradio + ZeroGPU, con respaldo en CPU) · Frontend en Netlify |

## Carpetas

```
app/
├── PARTE_B_plan_maestro.md
├── README.md
├── backend/
│   ├── main.py              rutas: /health, /read, /solve, /report
│   ├── config.py            configuración desde .env
│   ├── models.py            contratos (los mismos que usa el frontend)
│   ├── services/
│   │   ├── llm.py           cliente del modelo (formato OpenAI; una conversación nueva por foto)
│   │   ├── prompts.py       prompts y lectura de la respuesta (los comparte el Space)
│   │   ├── verify.py        verificación con SymPy (lista blanca: nunca ejecuta texto peligroso)
│   │   ├── guard.py         límites, rate limit, inyección, limpieza de la foto (sin EXIF/GPS)
│   │   └── answers.py       extractor de respuestas (el mismo del examen)
│   ├── tests/test_api.py    48 pruebas
│   ├── data/                reportes de error (solo texto)
│   ├── requirements.txt
│   └── .env.example
├── space/                   el backend de producción (Space de Hugging Face, como el del ajedrez)
│   ├── app.py               Gradio + ZeroGPU: /health, /read, /solve, /report (mismos contratos)
│   ├── services/            COPIA de backend/services (mismos prompts, guardrails y SymPy)
│   ├── config.py            copia de backend/config.py
│   ├── requirements.txt
│   └── README.md            ficha del Space
└── frontend/
    ├── src/app/
    │   ├── core/            api.ts, i18n.ts (ES/EN), image.ts (reduce la foto y quita EXIF), ui-bus.ts
    │   ├── sections/        navbar, hero, tutor, how, offline, faq, report, footer
    │   ├── pages/           home, privacy
    │   └── shared/          math-text (KaTeX sin innerHTML), steps, logo
    ├── src/environments/    URL del backend en desarrollo y en producción
    ├── public/favicon.svg
    └── netlify.toml         build, SPA, cabeceras de seguridad (CSP)
```

## Requisitos

- Python 3.12 (`D:\python312\python.exe`)
- Node 22 o 24 y npm
- LM Studio con el servidor encendido (pestaña Developer → Start Server, puerto 1234) y el modelo `vertex-math-vision` cargado

## Antes de arrancar: comprobar los puertos

En PowerShell, desde cualquier carpeta:

```
netstat -ano | findstr :8000
netstat -ano | findstr :4200
netstat -ano | findstr :1234
```

8000 (backend) y 4200 (frontend) tienen que salir vacíos; 1234 tiene que estar ocupado por LM Studio.
Si 8000 está ocupado, arranca uvicorn con otro puerto (`--port 8010`) y cámbialo también en
`frontend/src/environments/environment.ts` (`apiBase`). Si cambias el 4200, cámbialo en `ALLOWED_ORIGINS` del `.env`.

## Backend

Desde `E:\vertex-math-vision\app\backend`:

```
D:\python312\python.exe -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

En `.env`, pon el nombre exacto del modelo tal como lo lista LM Studio (por ejemplo `LLM_MODEL=vertex-math-vision@q8_0`).

```
pytest -q
uvicorn main:app --port 8000
```

Documentación interactiva para probar la API: http://127.0.0.1:8000/docs

## Frontend

Desde `E:\vertex-math-vision\app\frontend` (otra terminal):

```
npm install
npm start
```

Abre http://localhost:4200. Para probarlo en el móvil dentro de tu red: `npx ng serve --host 0.0.0.0` y añade
`http://<IP-de-tu-PC>:4200` a `ALLOWED_ORIGINS`.

Build de producción (lo mismo que hace Netlify), desde `E:\vertex-math-vision\app\frontend`:

```
npm run build
```

## Cómo funciona una pregunta

1. **Foto** → el navegador la gira, la reduce a 1280 px y la vuelve a codificar (sin EXIF).
2. **`POST /read`** → el modelo copia el ejercicio sin resolverlo. Si hay varios, el estudiante elige uno.
3. **Confirmación** → el estudiante ve "Esto es lo que leí" y lo corrige si hace falta.
4. **`POST /solve`** → el modelo resuelve paso a paso (conversación nueva, mismo *system prompt* del entrenamiento).
5. **SymPy** → calcula por su cuenta y compara con el `\boxed{}` del modelo; si no puede, revisa las cuentas de cada paso.

## Seguridad

- **SymPy** ejecuta lo que se le pasa: por eso `verify.py` solo deja pasar números, operadores y variables de
  una letra (más `sqrt` y `pi`), con límite de longitud, sin potencias gigantes y con tiempo máximo de 3 s.
  Las pruebas `test_verify_never_evaluates_unsafe_input` lo comprueban.
- La respuesta del modelo **nunca** se inserta con `innerHTML`: el texto va con `textContent` y las fórmulas las dibuja KaTeX con `trust: false`.
- **Fotos:** no se guardan. Se les quitan los metadatos en el navegador y otra vez en el servidor.
- Rate limit por IP, límite de tamaño de imagen y de texto, detección básica de inyección y Portero opcional (`PORTERO_URL`).
- CORS restringido a `ALLOWED_ORIGINS`. En Netlify, CSP estricta en `netlify.toml`.

## Portero (V-SRT)

Pon la URL en `PORTERO_URL` del `.env`. El backend envía `POST {PORTERO_URL}/check` con `{"text": ...}` y respeta
`{"allowed": bool}`. Si el Portero no responde, sigue con la validación local y lo apunta en el log.

## Paso a producción

### 1. Backend: Space de Hugging Face

El Space usa los mismos módulos que el backend local (`space/services` es una copia de `backend/services`).
Si cambias algo en `backend/services`, cópialo también a `space/services` antes de subir.

1. En huggingface.co → **New Space**: nombre `vertex-math-vision`, SDK **Gradio**, hardware **ZeroGPU**, público.
2. Sube la carpeta, desde `E:\vertex-math-vision\app` (con `HF_TOKEN` puesto en esa consola, como para el modelo):
   ```
   ..\venv\Scripts\hf.exe upload Denisijcu/vertex-math-vision space . --repo-type space --commit-message "Vertex Math Vision API"
   ```
3. Espera al build y abre la pestaña **Logs**: tiene que salir `Running on local URL`.
4. Cuando tengas la URL de Netlify, ponla en el Space como variable `APP_URL` (Settings → Variables).

La URL del Space queda como `https://denisijcu-vertex-math-vision.hf.space/`. Es la que ya usan
`frontend/src/environments/environment.prod.ts`, `frontend/netlify.toml` y `frontend/public/_headers`.
Si el Space tiene otro nombre, cámbiala en esos tres sitios.

### 2. Frontend: Netlify

Opción A, **Netlify Drop** (sin repositorio), desde `E:\vertex-math-vision\app\frontend`:
```
npm run build
```
y arrastra la carpeta `dist\frontend\browser` a app.netlify.com/drop. `_redirects` y `_headers` van dentro:
la redirección de Angular y las cabeceras de seguridad funcionan igual.

Opción B, **desde GitHub**: "Base directory" = la carpeta `frontend`. `netlify.toml` trae el build, la redirección y las cabeceras.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| El punto del navbar sale rojo ("Tutor dormido") | LM Studio no tiene el servidor encendido, o el backend no está corriendo |
| `CORS` en la consola del navegador | El origen del frontend no está en `ALLOWED_ORIGINS`; reinicia uvicorn después de cambiar `.env` |
| La respuesta sale en `{}` | En LM Studio está activado "Structured Output": desactívalo |
| Tarda mucho | Normal con el modelo en CPU; el frontend espera hasta 150 s |
| `npm install` falla con "edgesOut" o por dependencias "peer" | Error interno de npm 10: usa `npm install --legacy-peer-deps` |
| Puerto ocupado | Ver "Antes de arrancar" |
