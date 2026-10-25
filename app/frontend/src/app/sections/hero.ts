import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { LucideCamera, LucideCircleCheck, LucideKeyboard, LucideShieldCheck, LucideCalculator, LucideWifiOff } from '@lucide/angular';
import { I18n } from '../core/i18n';
import { UiBus } from '../core/ui-bus';

@Component({
  selector: 'app-hero',
  imports: [LucideCamera, LucideKeyboard, LucideCircleCheck, LucideShieldCheck, LucideCalculator, LucideWifiOff],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section id="inicio" class="hero relative overflow-hidden pt-28 pb-16 sm:pt-36 sm:pb-24" aria-labelledby="hero-title">
      <div class="hero-grid" aria-hidden="true"></div>
      <div class="relative mx-auto grid max-w-6xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-[1.15fr_1fr]">
        <div class="fade-up">
          <p class="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-semibold text-cyan-200">
            <span class="h-1.5 w-1.5 rounded-full bg-cyan-300"></span>{{ i18n.t('hero.badge') }}
          </p>
          <h1 id="hero-title" class="mt-6 text-4xl font-black leading-[1.05] tracking-tight text-white sm:text-6xl">
            {{ i18n.t('hero.title1') }}<br />
            <span class="grad-text">{{ i18n.t('hero.title2') }}</span>
          </h1>
          <p class="mt-6 max-w-xl text-lg leading-relaxed text-zinc-300">{{ i18n.t('hero.sub') }}</p>
          <div class="mt-9 flex flex-col gap-3 sm:flex-row">
            <button type="button" class="btn-primary btn-lg btn-glow" (click)="bus.openCamera()">
              <svg lucideCamera class="h-5 w-5" aria-hidden="true"></svg> {{ i18n.t('hero.cta1') }}
            </button>
            <button type="button" class="btn-outline btn-lg" (click)="bus.startTyping()">
              <svg lucideKeyboard class="h-5 w-5" aria-hidden="true"></svg> {{ i18n.t('hero.cta2') }}
            </button>
          </div>
          <ul class="mt-10 grid gap-3 text-sm text-zinc-400 sm:grid-cols-3">
            <li class="flex items-center gap-2"><svg lucideShieldCheck class="h-4 w-4 text-emerald-300" aria-hidden="true"></svg>{{ i18n.t('hero.trust1') }}</li>
            <li class="flex items-center gap-2"><svg lucideCalculator class="h-4 w-4 text-cyan-300" aria-hidden="true"></svg>{{ i18n.t('hero.trust2') }}</li>
            <li class="flex items-center gap-2"><svg lucideWifiOff class="h-4 w-4 text-violet-300" aria-hidden="true"></svg>{{ i18n.t('hero.trust3') }}</li>
          </ul>
        </div>

        <!-- Ilustración: un ejemplo de cómo se ve una respuesta (no es una captura real) -->
        <div class="relative mx-auto w-full max-w-sm fade-up [animation-delay:150ms]" aria-hidden="true">
          <div class="absolute -inset-6 rounded-[2.5rem] bg-gradient-to-br from-cyan-400/25 via-violet-500/20 to-fuchsia-500/20 blur-2xl"></div>
          <div class="glass-card relative rounded-[2rem] p-5 float-slow">
            <div class="rounded-2xl border border-white/10 bg-[#fafaf7] p-5 text-center handwritten text-2xl text-zinc-800 shadow-inner -rotate-1">
              2x + 3 = 7
            </div>
            <div class="mt-4 space-y-2.5 text-sm">
              <div class="step"><span class="step-num">1</span><span class="text-zinc-300">2x = 7 − 3 = 4</span></div>
              <div class="step"><span class="step-num">2</span><span class="text-zinc-300">x = 4 ÷ 2</span></div>
            </div>
            <div class="answer-box mt-4 flex items-center justify-between rounded-2xl px-4 py-3">
              <span class="text-xl font-bold text-white">x = 2</span>
              <span class="inline-flex items-center gap-1 rounded-full border border-emerald-400/40 bg-emerald-400/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                <svg lucideCircleCheck class="h-3.5 w-3.5"></svg>{{ i18n.t('verify.verified') }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  `,
})
export class Hero {
  protected readonly i18n = inject(I18n);
  protected readonly bus = inject(UiBus);
}
