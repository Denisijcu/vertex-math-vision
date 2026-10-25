import type { Backend } from '../app/core/backend';

// Producción (Netlify): el backend es el Space de Hugging Face.
// Si el Space se crea con otro nombre, cambia la URL aquí y en connect-src de netlify.toml.
export const environment = {
  production: true,
  // Space de Hugging Face (Gradio + ZeroGPU): se llama con @gradio/client.
  backend: { kind: 'gradio', url: 'https://denisijcu-vertex-math-vision.hf.space/' } as Backend,
  ggufRepo: 'https://huggingface.co/Denisijcu/vertex-math-vision-GGUF',
  modelRepo: 'https://huggingface.co/Denisijcu/vertex-math-vision',
  site: 'https://vertex-services.org',
  email: 'contact@vertexcoders.com',
};
