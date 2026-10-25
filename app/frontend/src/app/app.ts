import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { I18n } from './core/i18n';
import { Footer } from './sections/footer';
import { Navbar } from './sections/navbar';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Navbar, Footer],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <a href="#contenido" class="skip-link" (click)="skip($event)">{{ i18n.t('skip') }}</a>
    <app-navbar />
    <main id="contenido" tabindex="-1">
      <router-outlet />
    </main>
    <app-footer />
  `,
})
export class App {
  protected readonly i18n = inject(I18n);

  /** Con <base href="/"> un enlace "#contenido" saldría de /privacidad; movemos el foco a mano. */
  protected skip(event: Event): void {
    event.preventDefault();
    document.getElementById('contenido')?.focus();
  }
}
