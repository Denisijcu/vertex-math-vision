import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideArrowLeft } from '@lucide/angular';
import { environment } from '../../environments/environment';
import { I18n } from '../core/i18n';

@Component({
  selector: 'app-privacy',
  imports: [RouterLink, LucideArrowLeft],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <article class="mx-auto max-w-3xl px-4 pb-24 pt-28 sm:px-6">
      <a routerLink="/" fragment="tutor" class="btn-ghost"><svg lucideArrowLeft class="h-4 w-4" aria-hidden="true"></svg>{{ i18n.t('privacy.back') }}</a>
      <h1 class="mt-8 text-4xl font-black tracking-tight text-white">{{ i18n.t('privacy.title') }}</h1>
      <p class="mt-2 text-sm text-zinc-500">{{ i18n.lang() === 'es' ? 'Última actualización: 24 de octubre de 2026' : 'Last updated: October 24, 2026' }}</p>

      @if (i18n.lang() === 'es') {
        <div class="prose-vmv">
          <p>Vertex Math Vision es un tutor de matemáticas de <strong>Vertex Coders LLC</strong> (Miami, FL) pensado para estudiantes de primaria y secundaria. Por eso recogemos lo mínimo posible.</p>
          <h2>Fotos de los ejercicios</h2>
          <p><strong>No guardamos las fotos.</strong> Se usan solo para resolver el ejercicio y se descartan al terminar. Antes de enviarlas, tu navegador y nuestro servidor les quitan los datos ocultos (EXIF), como la ubicación GPS o el modelo del teléfono.</p>
          <h2>Lo que escribes</h2>
          <p>El texto del ejercicio y la pregunta se usan solo para generar la respuesta. No guardamos conversaciones.</p>
          <h2>Reportes de error</h2>
          <p>Si envías un reporte, guardamos el texto que escribes, lo que leyó el tutor, su respuesta y, solo si lo pones, tu email. <strong>Nunca la foto.</strong> Lo usamos para mejorar el modelo. Los reportes se borran como máximo a los 12 meses.</p>
          <h2>Menores de edad</h2>
          <p>No pedimos nombre, edad ni cuenta para usar el tutor. Si eres menor de edad, no escribas tu email ni datos personales en los reportes. Si un padre, madre o tutor quiere que borremos algo, puede escribirnos.</p>
          <h2>Cookies y seguimiento</h2>
          <p>No usamos cookies de publicidad ni herramientas de seguimiento. Solo guardamos en tu navegador el idioma que elegiste.</p>
          <h2>Uso sin internet</h2>
          <p>Si usas el modelo en LM Studio, todo ocurre en tu computadora y no nos llega nada.</p>
          <h2>Borrar tus datos</h2>
          <p>Para pedir que borremos un reporte, escribe a <a [href]="'mailto:' + email">{{ email }}</a>.</p>
        </div>
      } @else {
        <div class="prose-vmv">
          <p>Vertex Math Vision is a math tutor by <strong>Vertex Coders LLC</strong> (Miami, FL) built for elementary, middle and high school students. That's why we collect as little as possible.</p>
          <h2>Photos of exercises</h2>
          <p><strong>We don't store photos.</strong> They are only used to solve the exercise and are discarded afterwards. Before sending, your browser and our server strip hidden data (EXIF) such as GPS location or the phone model.</p>
          <h2>What you type</h2>
          <p>The exercise text and your question are only used to produce the answer. We don't store conversations.</p>
          <h2>Error reports</h2>
          <p>If you send a report, we store the text you write, what the tutor read, its answer and, only if you provide it, your email. <strong>Never the photo.</strong> We use it to improve the model. Reports are deleted after 12 months at most.</p>
          <h2>Minors</h2>
          <p>We don't ask for a name, age or account to use the tutor. If you are a minor, don't write your email or personal data in reports. A parent or guardian who wants something deleted can write to us.</p>
          <h2>Cookies and tracking</h2>
          <p>We don't use advertising cookies or tracking tools. We only store the language you chose in your browser.</p>
          <h2>Offline use</h2>
          <p>If you use the model in LM Studio, everything happens on your computer and nothing reaches us.</p>
          <h2>Deleting your data</h2>
          <p>To ask us to delete a report, write to <a [href]="'mailto:' + email">{{ email }}</a>.</p>
        </div>
      }
    </article>
  `,
})
export default class Privacy {
  protected readonly i18n = inject(I18n);
  protected readonly email = environment.email;
}
