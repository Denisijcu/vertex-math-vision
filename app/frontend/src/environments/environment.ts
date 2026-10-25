import type { Backend } from '../app/core/backend';

// Desarrollo: el backend corre en tu máquina (uvicorn en el puerto 8000).
export const environment = {
  production: false,
  // Backend local (FastAPI + LM Studio).
  backend: { kind: 'fastapi', url: 'http://127.0.0.1:8000' } as Backend,
  ggufRepo: 'https://huggingface.co/Denisijcu/vertex-math-vision-GGUF',
  modelRepo: 'https://huggingface.co/Denisijcu/vertex-math-vision',
  site: 'https://vertex-services.org',
  email: 'contact@vertexcoders.com',
};
