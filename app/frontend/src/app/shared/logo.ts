import { ChangeDetectionStrategy, Component } from '@angular/core';

/** Marca de Vertex Math Vision: una lente (la foto) con el signo de raíz dentro (las matemáticas). */
@Component({
  selector: 'app-logo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'inline-block' },
  template: `
    <svg viewBox="0 0 64 64" class="h-full w-full" role="img" aria-label="Vertex Math Vision">
      <defs>
        <linearGradient id="vmv-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#22d3ee" />
          <stop offset="1" stop-color="#8b5cf6" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#vmv-g)" />
      <circle cx="32" cy="32" r="19" fill="#09090b" />
      <circle cx="32" cy="32" r="19" fill="none" stroke="#ffffff" stroke-opacity=".25" stroke-width="2" />
      <path d="M19 33 l5 0 l5 9 l8 -20 l9 0" fill="none" stroke="url(#vmv-g)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
      <circle cx="46" cy="18" r="3" fill="#ffffff" fill-opacity=".9" />
    </svg>
  `,
})
export class Logo {}
