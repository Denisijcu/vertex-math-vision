import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { LucideDownload, LucideExternalLink, LucideLaptop, LucideTriangleAlert } from '@lucide/angular';
import { environment } from '../../environments/environment';
import { I18n } from '../core/i18n';

@Component({
  selector: 'app-offline',
  imports: [LucideLaptop, LucideDownload, LucideExternalLink, LucideTriangleAlert],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section id="sin-internet" class="mx-auto max-w-6xl scroll-mt-24 px-4 pb-24 sm:px-6" aria-labelledby="offline-title">
      <div class="glass-card relative overflow-hidden rounded-3xl p-6 sm:p-10">
        <div class="pointer-events-none absolute -right-20 top-0 h-72 w-72 rounded-full bg-violet-500/15 blur-3xl" aria-hidden="true"></div>
        <div class="relative grid gap-10 lg:grid-cols-[1fr_1.2fr] lg:items-center">
          <div>
            <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-400/10 ring-1 ring-white/10">
              <svg lucideLaptop class="h-6 w-6 text-violet-300" aria-hidden="true"></svg>
            </div>
            <h2 id="offline-title" class="mt-5 text-3xl font-extrabold tracking-tight text-white">{{ i18n.t('offline.title') }}</h2>
            <p class="mt-3 leading-relaxed text-zinc-300">{{ i18n.t('offline.sub') }}</p>
            <a [href]="gguf" target="_blank" rel="noopener noreferrer" class="btn-outline mt-7">
              <svg lucideDownload class="h-5 w-5" aria-hidden="true"></svg> {{ i18n.t('offline.cta') }}
              <svg lucideExternalLink class="h-4 w-4 opacity-60" aria-hidden="true"></svg>
            </a>
          </div>
          <div>
            <ol class="space-y-3">
              @for (k of keys; track k; let i = $index) {
                <li class="step"><span class="step-num">{{ i + 1 }}</span><span class="leading-relaxed text-zinc-300">{{ i18n.t(k) }}</span></li>
              }
            </ol>
            <p class="mt-4 flex gap-2 text-sm text-amber-200/90">
              <svg lucideTriangleAlert class="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true"></svg>{{ i18n.t('offline.note') }}
            </p>
          </div>
        </div>
      </div>
    </section>
  `,
})
export class Offline {
  protected readonly i18n = inject(I18n);
  protected readonly gguf = environment.ggufRepo;
  protected readonly keys = ['offline.1', 'offline.2', 'offline.3', 'offline.4'] as const;
}
