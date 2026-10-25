import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', loadComponent: () => import('./pages/home'), title: 'Vertex Math Vision — Tu tutor de matemáticas con una foto' },
  { path: 'privacidad', loadComponent: () => import('./pages/privacy'), title: 'Privacidad — Vertex Math Vision' },
  { path: '**', redirectTo: '' },
];
