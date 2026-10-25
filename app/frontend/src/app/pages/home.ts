import { ChangeDetectionStrategy, Component } from '@angular/core';
import { Faq } from '../sections/faq';
import { Hero } from '../sections/hero';
import { How } from '../sections/how';
import { Offline } from '../sections/offline';
import { Report } from '../sections/report';
import { Tutor } from '../sections/tutor';

@Component({
  selector: 'app-home',
  imports: [Hero, Tutor, How, Offline, Faq, Report],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-hero />
    <app-tutor />
    <app-how />
    <app-offline />
    <app-faq />
    <app-report />
  `,
})
export default class Home {}
