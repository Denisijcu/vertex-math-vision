import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideHouse, LucideMenu, LucideX } from '@lucide/angular';
import { Api } from '../core/api';
import { I18n, Lang } from '../core/i18n';
import { Logo } from '../shared/logo';

const LINKS = [
  { href: 'como-funciona', key: 'nav.how' },
  { href: 'sin-internet', key: 'nav.offline' },
  { href: 'preguntas', key: 'nav.faq' },
  { href: 'reportar', key: 'nav.report' },
] as const;

@Component({
  selector: 'app-navbar',
  imports: [RouterLink, Logo, LucideHouse, LucideMenu, LucideX],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-black/70 backdrop-blur-md">
      <nav class="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6" [attr.aria-label]="i18n.t('nav.home')">
        <a routerLink="/" fragment="inicio" class="flex items-center gap-2.5 rounded-lg font-extrabold tracking-tight text-zinc-100">
          <app-logo class="h-8 w-8" />
          <span>Vertex <span class="grad-text">Math Vision</span></span>
        </a>

        <div class="hidden items-center gap-6 text-sm text-zinc-400 lg:flex">
          <a routerLink="/" fragment="inicio" class="nav-link flex items-center gap-1.5">
            <svg lucideHouse class="h-4 w-4" aria-hidden="true"></svg>{{ i18n.t('nav.home') }}
          </a>
          @for (l of links; track l.href) {
            <a routerLink="/" [fragment]="l.href" class="nav-link">{{ i18n.t(l.key) }}</a>
          }
        </div>

        <div class="flex items-center gap-3">
          <span class="hidden items-center gap-2 text-xs text-zinc-400 sm:flex" role="status">
            <span class="h-2 w-2 rounded-full" [class]="dotClass()"></span>
            {{ statusLabel() }}
          </span>
          <div class="flex overflow-hidden rounded-lg border border-white/10 text-xs font-bold" role="group" aria-label="Idioma / Language">
            @for (l of langs; track l) {
              <button type="button" class="px-2.5 py-1.5 transition hover:text-cyan-300"
                [class.lang-on]="i18n.lang() === l" [attr.aria-pressed]="i18n.lang() === l" (click)="i18n.set(l)">{{ l.toUpperCase() }}</button>
            }
          </div>
          <button type="button" class="rounded-lg p-1.5 text-zinc-300 lg:hidden" (click)="open.set(!open())"
            [attr.aria-expanded]="open()" aria-controls="mobile-menu" [attr.aria-label]="i18n.t('nav.menu')">
            @if (open()) { <svg lucideX class="h-6 w-6" aria-hidden="true"></svg> } @else { <svg lucideMenu class="h-6 w-6" aria-hidden="true"></svg> }
          </button>
        </div>
      </nav>

      @if (open()) {
        <div id="mobile-menu" class="border-t border-white/10 bg-black/90 px-6 py-4 lg:hidden">
          <div class="flex flex-col gap-4 text-sm">
            <a routerLink="/" fragment="inicio" class="nav-link" (click)="open.set(false)">{{ i18n.t('nav.home') }}</a>
            @for (l of links; track l.href) {
              <a routerLink="/" [fragment]="l.href" class="nav-link" (click)="open.set(false)">{{ i18n.t(l.key) }}</a>
            }
            <span class="flex items-center gap-2 text-xs text-zinc-400">
              <span class="h-2 w-2 rounded-full" [class]="dotClass()"></span>{{ statusLabel() }}
            </span>
          </div>
        </div>
      }
    </header>
  `,
})
export class Navbar {
  protected readonly i18n = inject(I18n);
  private readonly api = inject(Api);
  protected readonly links = LINKS;
  protected readonly langs: Lang[] = ['es', 'en'];
  protected readonly open = signal(false);
  protected readonly status = signal<'checking' | 'up' | 'down'>('checking');

  constructor() {
    void this.check();
    const id = setInterval(() => void this.check(), 60_000);
    inject(DestroyRef).onDestroy(() => clearInterval(id));
  }

  private async check(): Promise<void> {
    this.status.set(await this.api.health());
  }

  protected dotClass(): string {
    const s = this.status();
    return s === 'up' ? 'bg-emerald-400 pulse-dot' : s === 'down' ? 'bg-rose-500' : 'bg-zinc-500';
  }

  protected statusLabel(): string {
    const s = this.status();
    return this.i18n.t(s === 'up' ? 'status.up' : s === 'down' ? 'status.down' : 'status.checking');
  }
}
