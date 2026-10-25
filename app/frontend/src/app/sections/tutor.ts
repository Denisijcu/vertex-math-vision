import {
  ChangeDetectionStrategy, Component, DestroyRef, ElementRef, computed, inject, signal, viewChild,
} from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  LucideCamera, LucideCircleAlert, LucideCircleCheck, LucideCircleHelp, LucideFlag, LucideImageUp,
  LucideInfo, LucideKeyboard, LucideLoaderCircle, LucideRotateCcw, LucideScanText,
  LucideSparkles, LucideTriangleAlert, LucideX,
} from '@lucide/angular';
import { Api, ApiError, SolveResponse, Verification } from '../core/api';
import { I18n, I18nKey } from '../core/i18n';
import { ImageError, prepareImage } from '../core/image';
import { UiBus } from '../core/ui-bus';
import { MathText } from '../shared/math-text';
import { Block, parseSteps } from '../shared/steps';

type Phase = 'idle' | 'reading' | 'confirm' | 'solving' | 'result' | 'error';

interface Badge { key: I18nKey; cls: string; icon: 'ok' | 'warn' | 'info' | 'stop'; }

const BADGES: Record<Verification, Badge> = {
  verified:   { key: 'verify.verified',   cls: 'border-emerald-400/40 bg-emerald-400/10 text-emerald-300', icon: 'ok' },
  mismatch:   { key: 'verify.mismatch',   cls: 'border-amber-400/40 bg-amber-400/10 text-amber-300',       icon: 'warn' },
  ill_posed:  { key: 'verify.ill_posed',  cls: 'border-orange-400/40 bg-orange-400/10 text-orange-300',    icon: 'warn' },
  // Azul, no verde: las cuentas cuadran pero el planteamiento no está comprobado. El verde es solo para "Verificado".
  steps_ok:   { key: 'verify.steps_ok',   cls: 'border-sky-400/40 bg-sky-400/10 text-sky-300',             icon: 'info' },
  steps_wrong:{ key: 'verify.steps_wrong',cls: 'border-amber-400/40 bg-amber-400/10 text-amber-300',       icon: 'warn' },
  unverified: { key: 'verify.unverified', cls: 'border-sky-400/40 bg-sky-400/10 text-sky-300',             icon: 'info' },
  not_math:   { key: 'verify.not_math',   cls: 'border-rose-400/40 bg-rose-400/10 text-rose-300',          icon: 'stop' },
};

@Component({
  selector: 'app-tutor',
  imports: [
    FormsModule, NgTemplateOutlet, MathText, LucideCamera, LucideImageUp, LucideKeyboard, LucideScanText, LucideLoaderCircle,
    LucideCircleCheck, LucideTriangleAlert, LucideInfo, LucideCircleAlert, LucideRotateCcw,
    LucideFlag, LucideSparkles, LucideX, LucideCircleHelp,
  ],
  templateUrl: './tutor.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Tutor {
  protected readonly i18n = inject(I18n);
  private readonly api = inject(Api);
  private readonly bus = inject(UiBus);
  private readonly destroyRef = inject(DestroyRef);

  private readonly fileInput = viewChild.required<ElementRef<HTMLInputElement>>('fileInput');
  private readonly cameraInput = viewChild.required<ElementRef<HTMLInputElement>>('cameraInput');
  private readonly textArea = viewChild<ElementRef<HTMLTextAreaElement>>('textArea');
  private readonly panel = viewChild.required<ElementRef<HTMLElement>>('panel');

  protected readonly phase = signal<Phase>('idle');
  protected readonly mode = signal<'photo' | 'text'>('photo');
  protected readonly dragging = signal(false);
  protected readonly preview = signal<string | null>(null);
  protected readonly typed = signal('');
  protected readonly ask = signal('');
  protected readonly reading = signal('');
  protected readonly problems = signal<string[]>([]);
  protected readonly chosen = signal(0);
  protected readonly result = signal<SolveResponse | null>(null);
  protected readonly errorMsg = signal('');
  protected readonly notMath = signal(false);
  protected readonly elapsed = signal(0);
  protected readonly canRetry = signal(false);

  protected readonly blocks = computed<Block[]>(() => parseSteps(this.result()?.steps ?? ''));
  protected readonly badge = computed(() => {
    const r = this.result();
    return r ? BADGES[r.verification] : null;
  });
  protected readonly busy = computed(() => this.phase() === 'reading' || this.phase() === 'solving');

  private image: Blob | null = null;
  private retryFn: (() => void) | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.bus.registerTutor(() => this.openCamera(), () => this.startTyping());
    this.destroyRef.onDestroy(() => {
      this.stopTimer();
      this.revokePreview();
    });
  }

  // ───────── entrada ─────────
  protected openCamera(): void {
    this.mode.set('photo');
    this.scrollIntoView();
    this.cameraInput().nativeElement.click();
  }

  protected openFiles(): void {
    this.fileInput().nativeElement.click();
  }

  protected startTyping(): void {
    this.reset();
    this.mode.set('text');
    this.scrollIntoView();
    setTimeout(() => this.textArea()?.nativeElement.focus(), 350);
  }

  protected onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = ''; // permite volver a elegir la misma foto
    if (file) void this.takePhoto(file);
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) void this.takePhoto(file);
  }

  protected onPaste(event: ClipboardEvent): void {
    const file = Array.from(event.clipboardData?.files ?? []).find((f) => f.type.startsWith('image/'));
    if (file) {
      event.preventDefault();
      void this.takePhoto(file);
    }
  }

  private async takePhoto(file: File): Promise<void> {
    this.reset();
    this.mode.set('photo');
    try {
      this.image = await prepareImage(file);
    } catch (e) {
      this.fail(e instanceof ImageError ? this.i18n.t('tutor.imageError') : this.i18n.t('error.generic'), null);
      return;
    }
    this.preview.set(URL.createObjectURL(this.image));
    void this.readPhoto();
  }

  // ───────── lectura ─────────
  private async readPhoto(): Promise<void> {
    if (!this.image) return;
    this.start('reading');
    try {
      const r = await this.api.read(this.image, this.i18n.lang());
      this.stopTimer();
      if (r.source === 'fallback') return this.fail(this.i18n.t('tutor.fallback'), () => this.readPhoto());
      if (!r.is_math) {
        this.notMath.set(true);
        this.phase.set('confirm');
        return;
      }
      this.reading.set(r.reading);
      this.problems.set(r.problems);
      this.chosen.set(0);
      this.phase.set('confirm');
    } catch (e) {
      this.fail(this.message(e), () => this.readPhoto());
    }
  }

  protected pickProblem(i: number): void {
    this.chosen.set(i);
  }

  protected editProblem(i: number, value: string): void {
    this.problems.update((list) => list.map((p, j) => (j === i ? value : p)));
  }

  // ───────── solución ─────────
  protected confirm(): void {
    const list = this.problems();
    const reading = list.length > 1 ? list[this.chosen()] : this.reading();
    void this.solve(reading.trim());
  }

  protected solveTyped(): void {
    const text = this.typed().trim();
    if (!text || this.busy()) return;
    this.image = null;
    void this.solve('', text);
  }

  private async solve(reading: string, text = this.ask().trim()): Promise<void> {
    this.start('solving');
    try {
      const r = await this.api.solve({ image: this.image, text, reading, lang: this.i18n.lang() });
      this.stopTimer();
      if (r.source === 'fallback') return this.fail(this.i18n.t('tutor.fallback'), () => this.solve(reading, text));
      this.result.set(r);
      this.phase.set('result');
      this.scrollIntoView();
    } catch (e) {
      this.fail(this.message(e), () => this.solve(reading, text));
    }
  }

  // ───────── resultado ─────────
  protected reportError(): void {
    const r = this.result();
    this.bus.reportDraft.set({ reading: r?.reading ?? null, answer: r?.answer ?? null });
    document.getElementById('reportar')?.scrollIntoView({ behavior: this.motion(), block: 'start' });
  }

  protected retry(): void {
    this.retryFn?.();
  }

  protected reset(): void {
    this.stopTimer();
    this.revokePreview();
    this.image = null;
    this.phase.set('idle');
    this.reading.set('');
    this.problems.set([]);
    this.result.set(null);
    this.errorMsg.set('');
    this.notMath.set(false);
    this.retryFn = null;
    this.canRetry.set(false);
  }

  // ───────── utilidades ─────────
  private start(phase: Phase): void {
    this.phase.set(phase);
    this.elapsed.set(0);
    this.stopTimer();
    this.timer = setInterval(() => this.elapsed.update((s) => s + 1), 1000);
  }

  private stopTimer(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  private fail(message: string, retry: (() => void) | null): void {
    this.stopTimer();
    this.errorMsg.set(message);
    this.retryFn = retry;
    this.canRetry.set(retry !== null);
    this.phase.set('error');
  }

  private message(e: unknown): string {
    if (e instanceof ApiError) {
      if (e.code === 'TIMEOUT') return this.i18n.t('error.timeout');
      if (e.code === 'NETWORK') return this.i18n.t('error.network');
      if (e.message) return e.message; // los errores del backend ya vienen en el idioma del estudiante
    }
    return this.i18n.t('error.generic');
  }

  private revokePreview(): void {
    const url = this.preview();
    if (url) URL.revokeObjectURL(url);
    this.preview.set(null);
  }

  private motion(): ScrollBehavior {
    return matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
  }

  private scrollIntoView(): void {
    this.panel().nativeElement.scrollIntoView({ behavior: this.motion(), block: 'start' });
  }

  protected answerMath(answer: string): string {
    return `$${answer}$`;
  }

  protected stepLabel(b: Block): string {
    if (b.kind === 'step') return String(b.n ?? '');
    return b.label;
  }
}
