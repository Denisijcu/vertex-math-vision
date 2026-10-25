import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { LucidePlus } from '@lucide/angular';
import { I18n } from '../core/i18n';

@Component({
  selector: 'app-faq',
  imports: [LucidePlus],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section id="preguntas" class="mx-auto max-w-3xl scroll-mt-24 px-4 pb-24 sm:px-6" aria-labelledby="faq-title">
      <h2 id="faq-title" class="section-title">{{ i18n.t('faq.title') }}</h2>
      <div class="mt-10 space-y-3">
        @for (f of items; track f.q; let i = $index) {
          <div class="glass-card overflow-hidden rounded-2xl">
            <h3>
              <button type="button" class="flex w-full items-center justify-between gap-4 px-5 py-4 text-left font-semibold text-zinc-100"
                [attr.aria-expanded]="open() === i" [attr.aria-controls]="'faq-' + i" [id]="'faq-btn-' + i" (click)="toggle(i)">
                {{ i18n.t(f.q) }}
                <svg lucidePlus class="h-5 w-5 shrink-0 text-cyan-300 transition-transform duration-300 motion-reduce:transition-none"
                  [class.rotate-45]="open() === i" aria-hidden="true"></svg>
              </button>
            </h3>
            <div [id]="'faq-' + i" role="region" [attr.aria-labelledby]="'faq-btn-' + i" class="faq-panel" [class.faq-open]="open() === i">
              <div class="overflow-hidden"><p class="px-5 pb-5 text-sm leading-relaxed text-zinc-400">{{ i18n.t(f.a) }}</p></div>
            </div>
          </div>
        }
      </div>
    </section>
  `,
})
export class Faq {
  protected readonly i18n = inject(I18n);
  protected readonly open = signal<number | null>(null);
  protected readonly items = [
    { q: 'faq.1q', a: 'faq.1a' }, { q: 'faq.2q', a: 'faq.2a' }, { q: 'faq.3q', a: 'faq.3a' },
    { q: 'faq.4q', a: 'faq.4a' }, { q: 'faq.5q', a: 'faq.5a' }, { q: 'faq.6q', a: 'faq.6a' },
  ] as const;

  protected toggle(i: number): void {
    this.open.set(this.open() === i ? null : i);
  }
}
