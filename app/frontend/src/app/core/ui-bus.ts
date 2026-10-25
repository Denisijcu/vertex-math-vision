import { Injectable, signal } from '@angular/core';

export interface ReportDraft {
  reading: string | null;
  answer: string | null;
}

/**
 * Comunicación entre secciones de la página sin acoplarlas:
 * el hero abre la cámara del tutor y el resultado del tutor rellena el formulario de reporte.
 * La cámara se abre llamando directamente a la función registrada, dentro del mismo clic,
 * porque los navegadores solo dejan abrir el selector de archivos durante un gesto del usuario.
 */
@Injectable({ providedIn: 'root' })
export class UiBus {
  private cameraFn: (() => void) | null = null;
  private typeFn: (() => void) | null = null;
  readonly reportDraft = signal<ReportDraft | null>(null);

  registerTutor(camera: () => void, type: () => void): void {
    this.cameraFn = camera;
    this.typeFn = type;
  }

  openCamera(): void { this.cameraFn?.(); }
  startTyping(): void { this.typeFn?.(); }
}
