import { Injectable } from '@angular/core';
import { environment } from '../../environments/environment';
import { Lang } from './i18n';

/** Contratos idénticos a backend/models.py y a space/app.py. */
export type Verification = 'verified' | 'mismatch' | 'ill_posed' | 'steps_ok' | 'steps_wrong' | 'unverified' | 'not_math';

export interface ReadResponse {
  reading: string;
  is_math: boolean;
  problems: string[];
  lang: Lang;
  source: 'llm' | 'fallback';
}

export interface SolveResponse {
  reading: string;
  steps: string;
  answer: string | null;
  verification: Verification;
  sympy_answer: string | null;
  note: string | null;
  lang: Lang;
  source: 'llm' | 'fallback';
}

export interface ReportRequest {
  message: string;
  reading?: string | null;
  answer?: string | null;
  email?: string | null;
  website?: string; // honeypot
}

/** Error de la API ya listo para enseñar: `message` viene en el idioma del estudiante cuando lo manda el backend. */
export class ApiError extends Error {
  constructor(
    readonly code: 'TIMEOUT' | 'NETWORK' | string,
    message: string,
    readonly status = 0,
  ) {
    super(message);
  }
}

/**
 * Tiempos máximos. En el Space, si se acaba la cuota de GPU del visitante, el modelo responde en CPU
 * y puede tardar varios minutos: por eso los tiempos de producción son más largos.
 */
const TIMEOUT = environment.backend.kind === 'gradio'
  ? { health: 15_000, read: 240_000, solve: 420_000, report: 20_000 }
  : { health: 4_000, read: 90_000, solve: 150_000, report: 15_000 };

interface GradioClient {
  predict(endpoint: string, data: Record<string, unknown>): Promise<{ data: unknown[] }>;
}

@Injectable({ providedIn: 'root' })
export class Api {
  private readonly backend = environment.backend;
  private readonly base = environment.backend.url.replace(/\/$/, '');
  private client: Promise<GradioClient> | null = null;

  async health(): Promise<'up' | 'down'> {
    try {
      const r = await this.call<{ status: string; llm: 'up' | 'down' }>('health', {}, TIMEOUT.health);
      return r.llm;
    } catch {
      return 'down';
    }
  }

  async read(image: Blob, lang: Lang): Promise<ReadResponse> {
    return this.call<ReadResponse>('read', { image, lang }, TIMEOUT.read);
  }

  async solve(opts: { image: Blob | null; text: string; reading: string; lang: Lang }): Promise<SolveResponse> {
    return this.call<SolveResponse>('solve', { ...opts }, TIMEOUT.solve);
  }

  report(body: ReportRequest): Promise<{ ok: boolean }> {
    return this.call<{ ok: boolean }>('report', { ...body }, TIMEOUT.report);
  }

  // ───────── transporte ─────────
  private call<T>(endpoint: string, data: Record<string, unknown>, timeoutMs: number): Promise<T> {
    return this.backend.kind === 'gradio'
      ? this.viaGradio<T>(endpoint, data, timeoutMs)
      : this.viaFastapi<T>(endpoint, data, timeoutMs);
  }

  /** Desarrollo: FastAPI en tu máquina. */
  private async viaFastapi<T>(endpoint: string, data: Record<string, unknown>, timeoutMs: number): Promise<T> {
    let init: RequestInit;
    if (endpoint === 'health') {
      init = { method: 'GET' };
    } else if (endpoint === 'report') {
      init = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) };
    } else {
      const form = new FormData();
      for (const [k, v] of Object.entries(data)) {
        if (v instanceof Blob) form.append(k, v, 'exercise.jpg');
        else if (v !== null && v !== undefined) form.append(k, String(v));
      }
      init = { method: 'POST', body: form };
    }
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    let res: Response;
    try {
      res = await fetch(`${this.base}/${endpoint}`, { ...init, signal: ctrl.signal });
    } catch (err) {
      throw (err as Error)?.name === 'AbortError' ? new ApiError('TIMEOUT', '') : new ApiError('NETWORK', '');
    } finally {
      clearTimeout(timer);
    }
    let body: unknown = null;
    try { body = await res.json(); } catch { /* respuesta vacía o no JSON */ }
    if (!res.ok) {
      const e = (body as { error?: { code?: string; message?: string } } | null)?.error;
      throw new ApiError(e?.code ?? 'HTTP_' + res.status, e?.message ?? '', res.status);
    }
    return body as T;
  }

  /** Producción: el Space de Hugging Face, igual que el Space del ajedrez. */
  private async viaGradio<T>(endpoint: string, data: Record<string, unknown>, timeoutMs: number): Promise<T> {
    const payload: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(data)) {
      if (k === 'image') payload['image_b64'] = v instanceof Blob ? await blobToBase64(v) : '';
      else payload[k] = v ?? '';
    }
    const call = this.gradio().then((c) => c.predict(`/${endpoint}`, payload));
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new ApiError('TIMEOUT', '')), timeoutMs);
    });
    try {
      const res = await Promise.race([call, timeout]);
      return res.data[0] as T;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      // Los errores del Space llegan como "CODIGO: mensaje en el idioma del estudiante".
      const msg = String((err as { message?: string })?.message ?? err ?? '');
      const m = msg.match(/^([A-Z_]{3,}):\s*([\s\S]*)$/);
      if (m) throw new ApiError(m[1], m[2]);
      throw new ApiError('NETWORK', '');
    } finally {
      clearTimeout(timer);
    }
  }

  private gradio(): Promise<GradioClient> {
    // @gradio/client se carga solo en producción, la primera vez que hace falta.
    this.client ??= import('@gradio/client')
      .then(({ Client }) => Client.connect(this.backend.url) as unknown as Promise<GradioClient>)
      .catch((e) => {
        this.client = null; // el Space puede estar dormido: el siguiente intento vuelve a conectar
        throw e;
      });
    return this.client;
  }
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',', 2)[1] ?? '');
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}
