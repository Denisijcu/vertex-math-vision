import { ChangeDetectionStrategy, Component, ElementRef, effect, inject, input } from '@angular/core';

type Katex = typeof import('katex');
let katexPromise: Promise<Katex> | null = null;
/** KaTeX pesa ~270 kB: se carga solo cuando hay una respuesta que mostrar. */
function loadKatex(): Promise<Katex> {
  katexPromise ??= import('katex').then((m) => (m as unknown as { default: Katex }).default ?? m);
  return katexPromise;
}

const MATH = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|\$[^$\n]+?\$)/g;

/**
 * Muestra texto del modelo con fórmulas. SEGURIDAD: nunca usa innerHTML con la respuesta del modelo.
 * El texto va con textContent y las fórmulas las dibuja KaTeX (trust: false) directamente en el DOM.
 */
@Component({
  selector: 'app-math-text',
  template: '',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'math-text' },
})
export class MathText {
  readonly text = input.required<string>();
  readonly block = input(false);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  constructor() {
    effect(() => {
      const text = this.text();
      void this.render(text);
    });
  }

  private async render(text: string): Promise<void> {
    const el = this.host.nativeElement;
    const needsMath = MATH.test(text);
    MATH.lastIndex = 0;
    const katex = needsMath ? await loadKatex() : null;
    if (this.text() !== text) return; // llegó otro texto mientras cargaba KaTeX
    el.replaceChildren();
    for (const part of text.split(MATH)) {
      if (!part) continue;
      const math = this.asMath(part);
      if (math && katex) {
        const span = document.createElement('span');
        span.className = math.display ? 'block my-2 overflow-x-auto' : 'inline-block align-middle';
        katex.render(math.expr, span, { displayMode: math.display, throwOnError: false, trust: false, strict: 'ignore', output: 'html' });
        el.appendChild(span);
      } else {
        this.appendText(el, part);
      }
    }
  }

  private asMath(part: string): { expr: string; display: boolean } | null {
    if (part.startsWith('$$') && part.endsWith('$$')) return { expr: part.slice(2, -2), display: true };
    if (part.startsWith('\\[') && part.endsWith('\\]')) return { expr: part.slice(2, -2), display: true };
    if (part.startsWith('\\(') && part.endsWith('\\)')) return { expr: part.slice(2, -2), display: false };
    if (part.startsWith('$') && part.endsWith('$') && part.length > 2) return { expr: part.slice(1, -1), display: false };
    return null;
  }

  /** Texto plano con **negritas** y saltos de línea, sin interpretar HTML. */
  private appendText(el: HTMLElement, text: string): void {
    const lines = text.split('\n');
    lines.forEach((line, i) => {
      line.split(/(\*\*[^*]+\*\*)/g).forEach((chunk) => {
        if (!chunk) return;
        if (chunk.startsWith('**') && chunk.endsWith('**')) {
          const b = document.createElement('strong');
          b.className = 'font-semibold text-zinc-100';
          b.textContent = chunk.slice(2, -2);
          el.appendChild(b);
        } else {
          el.appendChild(document.createTextNode(chunk));
        }
      });
      if (i < lines.length - 1) el.appendChild(document.createElement('br'));
    });
  }
}
