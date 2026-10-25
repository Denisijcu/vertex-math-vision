/**
 * Dónde está el backend:
 * - 'fastapi': app/backend en tu máquina (desarrollo), con fetch.
 * - 'gradio': el Space de Hugging Face (producción), con @gradio/client, como el Space del ajedrez.
 * Los dos devuelven exactamente los mismos contratos (ver api.ts).
 */
export interface Backend {
  kind: 'fastapi' | 'gradio';
  url: string;
}
