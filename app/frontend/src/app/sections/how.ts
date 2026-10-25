import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { LucideCamera, LucideListOrdered, LucideScanText, LucideShieldCheck } from '@lucide/angular';
import { I18n } from '../core/i18n';

@Component({
  selector: 'app-how',
  imports: [LucideCamera, LucideScanText, LucideListOrdered, LucideShieldCheck],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section id="como-funciona" class="mx-auto max-w-6xl scroll-mt-24 px-4 py-24 sm:px-6" aria-labelledby="how-title">
      <h2 id="how-title" class="section-title">{{ i18n.t('how.title') }}</h2>
      <p class="section-sub">{{ i18n.t('how.sub') }}</p>
      <ol class="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        @for (s of steps; track s.n) {
          <li class="glass-card group relative rounded-2xl p-6 transition duration-300 hover:-translate-y-1 motion-reduce:hover:translate-y-0">
            <span class="absolute right-5 top-4 font-mono text-5xl font-black text-white/5" aria-hidden="true">{{ s.n }}</span>
            <div class="flex h-11 w-11 items-center justify-center rounded-xl ring-1 ring-white/10 {{ s.bg }}">
              @switch (s.n) {
                @case (1) { <svg lucideCamera class="h-5 w-5 {{ s.fg }}" aria-hidden="true"></svg> }
                @case (2) { <svg lucideScanText class="h-5 w-5 {{ s.fg }}" aria-hidden="true"></svg> }
                @case (3) { <svg lucideListOrdered class="h-5 w-5 {{ s.fg }}" aria-hidden="true"></svg> }
                @default { <svg lucideShieldCheck class="h-5 w-5 {{ s.fg }}" aria-hidden="true"></svg> }
              }
            </div>
            <h3 class="mt-5 font-bold text-zinc-100">{{ i18n.t(s.t) }}</h3>
            <p class="mt-2 text-sm leading-relaxed text-zinc-400">{{ i18n.t(s.d) }}</p>
          </li>
        }
      </ol>
    </section>
  `,
})
export class How {
  protected readonly i18n = inject(I18n);
  protected readonly steps = [
    { n: 1, t: 'how.1t', d: 'how.1d', bg: 'bg-cyan-400/10', fg: 'text-cyan-300' },
    { n: 2, t: 'how.2t', d: 'how.2d', bg: 'bg-sky-400/10', fg: 'text-sky-300' },
    { n: 3, t: 'how.3t', d: 'how.3d', bg: 'bg-violet-400/10', fg: 'text-violet-300' },
    { n: 4, t: 'how.4t', d: 'how.4d', bg: 'bg-emerald-400/10', fg: 'text-emerald-300' },
  ] as const;
}
