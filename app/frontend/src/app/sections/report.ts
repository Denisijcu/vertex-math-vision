import { ChangeDetectionStrategy, Component, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { LucideCircleCheck, LucideFlag, LucideSend, LucideTriangleAlert } from '@lucide/angular';
import { Api } from '../core/api';
import { I18n } from '../core/i18n';
import { UiBus } from '../core/ui-bus';

@Component({
  selector: 'app-report',
  imports: [FormsModule, RouterLink, LucideFlag, LucideSend, LucideCircleCheck, LucideTriangleAlert],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section id="reportar" class="mx-auto max-w-3xl scroll-mt-24 px-4 pb-28 sm:px-6" aria-labelledby="report-title">
      <div class="glass-card rounded-3xl p-6 sm:p-8">
        <h2 id="report-title" class="flex items-center gap-2 text-2xl font-extrabold text-white">
          <svg lucideFlag class="h-6 w-6 text-amber-300" aria-hidden="true"></svg>{{ i18n.t('report.title') }}
        </h2>
        <p class="mt-2 text-sm text-zinc-400">{{ i18n.t('report.sub') }}
          <a routerLink="/privacidad" class="text-cyan-300 underline-offset-4 hover:underline">{{ i18n.t('footer.privacy') }}</a>
        </p>

        @if (draftInfo(); as d) {
          <p class="mt-4 rounded-xl border border-white/10 bg-black/30 p-3 font-mono text-xs text-zinc-400">{{ d }}</p>
        }

        <form class="mt-6 space-y-4" (ngSubmit)="send()" #f="ngForm">
          <label class="block">
            <span class="mb-1.5 block text-sm font-medium text-zinc-300">{{ i18n.t('report.msg') }}</span>
            <textarea name="message" rows="4" required minlength="3" maxlength="2000" class="field"
              [placeholder]="i18n.t('report.msgPh')" [ngModel]="message()" (ngModelChange)="message.set($event)"></textarea>
          </label>
          <label class="block">
            <span class="mb-1.5 block text-sm font-medium text-zinc-300">{{ i18n.t('report.email') }}</span>
            <input name="email" type="email" maxlength="200" class="field" autocomplete="email" [ngModel]="email()" (ngModelChange)="email.set($event)" />
          </label>
          <!-- honeypot: invisible para personas; los bots lo rellenan -->
          <div class="hidden" aria-hidden="true">
            <label>Website <input name="website" type="text" tabindex="-1" autocomplete="off" [ngModel]="website()" (ngModelChange)="website.set($event)" /></label>
          </div>
          <div class="flex flex-wrap items-center gap-4">
            <button type="submit" class="btn-primary" [disabled]="state() === 'sending' || !f.valid">
              <svg lucideSend class="h-4 w-4" aria-hidden="true"></svg>
              {{ state() === 'sending' ? i18n.t('report.sending') : i18n.t('report.send') }}
            </button>
            <p aria-live="polite" class="text-sm">
              @if (state() === 'ok') {
                <span class="flex items-center gap-1.5 text-emerald-300"><svg lucideCircleCheck class="h-4 w-4" aria-hidden="true"></svg>{{ i18n.t('report.ok') }}</span>
              } @else if (state() === 'error') {
                <span class="flex items-center gap-1.5 text-rose-300"><svg lucideTriangleAlert class="h-4 w-4" aria-hidden="true"></svg>{{ i18n.t('report.error') }}</span>
              }
            </p>
          </div>
        </form>
      </div>
    </section>
  `,
})
export class Report {
  protected readonly i18n = inject(I18n);
  private readonly api = inject(Api);
  private readonly bus = inject(UiBus);
  protected readonly message = signal('');
  protected readonly email = signal('');
  protected readonly website = signal('');
  protected readonly state = signal<'idle' | 'sending' | 'ok' | 'error'>('idle');
  protected readonly draftInfo = signal<string | null>(null);

  constructor() {
    effect(() => {
      const d = this.bus.reportDraft();
      if (!d) return;
      const parts = [d.reading ? `${this.i18n.t('result.reading')}: ${d.reading}` : '', d.answer ? `${this.i18n.t('result.answer')}: ${d.answer}` : ''];
      this.draftInfo.set(parts.filter(Boolean).join('  ·  ') || null);
      this.state.set('idle');
    });
  }

  protected async send(): Promise<void> {
    if (this.message().trim().length < 3) return;
    this.state.set('sending');
    const d = this.bus.reportDraft();
    try {
      await this.api.report({
        message: this.message().trim(),
        reading: d?.reading ?? null,
        answer: d?.answer ?? null,
        email: this.email().trim() || null,
        website: this.website(),
      });
      this.state.set('ok');
      this.message.set('');
      this.email.set('');
      this.draftInfo.set(null);
      this.bus.reportDraft.set(null);
    } catch {
      this.state.set('error');
    }
  }
}
