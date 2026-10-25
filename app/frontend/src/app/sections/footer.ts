import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { environment } from '../../environments/environment';
import { I18n } from '../core/i18n';
import { Logo } from '../shared/logo';

@Component({
  selector: 'app-footer',
  imports: [RouterLink, Logo],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <footer class="border-t border-white/10 py-10 text-sm text-zinc-500">
      <div class="mx-auto flex max-w-6xl flex-col items-center gap-6 px-4 sm:px-6 md:flex-row md:justify-between">
        <a routerLink="/" fragment="inicio" class="flex items-center gap-2 font-bold text-zinc-200">
          <app-logo class="h-7 w-7" /> Vertex <span class="grad-text">Math Vision</span>
        </a>
        <nav class="flex flex-wrap justify-center gap-5 text-zinc-400" aria-label="Footer">
          <a routerLink="/" fragment="como-funciona" class="nav-link">{{ i18n.t('nav.how') }}</a>
          <a routerLink="/" fragment="sin-internet" class="nav-link">{{ i18n.t('nav.offline') }}</a>
          <a routerLink="/" fragment="preguntas" class="nav-link">{{ i18n.t('nav.faq') }}</a>
          <a routerLink="/privacidad" class="nav-link">{{ i18n.t('footer.privacy') }}</a>
          <a [href]="model" target="_blank" rel="noopener noreferrer" class="nav-link">Hugging Face</a>
        </nav>
        <p class="text-center">
          © {{ year }} <a [href]="site" target="_blank" rel="noopener noreferrer" class="text-zinc-300 hover:text-cyan-300">Vertex Coders LLC</a> · Miami, FL ·
          {{ i18n.t('footer.rights') }}
        </p>
      </div>
    </footer>
  `,
})
export class Footer {
  protected readonly i18n = inject(I18n);
  protected readonly year = new Date().getFullYear();
  protected readonly site = environment.site;
  protected readonly model = environment.modelRepo;
}
