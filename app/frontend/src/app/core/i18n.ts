import { DOCUMENT } from '@angular/common';
import { Injectable, effect, inject, signal } from '@angular/core';

export type Lang = 'es' | 'en';

const ES = {
  'skip': 'Saltar al contenido',
  'nav.home': 'Inicio',
  'nav.how': 'Cómo funciona',
  'nav.offline': 'Úsalo sin internet',
  'nav.faq': 'Preguntas',
  'nav.report': 'Reportar un error',
  'nav.menu': 'Abrir menú',
  'status.up': 'Tutor en línea',
  'status.down': 'Tutor dormido',
  'status.checking': 'Comprobando…',
  'hero.badge': 'Modelo propio de Vertex Coders · gratis',
  'hero.title1': 'Sácale una foto.',
  'hero.title2': 'Entiéndelo paso a paso.',
  'hero.sub': 'Tu tutor de matemáticas para primaria y secundaria, en español o inglés. Lee tu ejercicio, aunque esté escrito a mano, y te explica cómo se resuelve.',
  'hero.cta1': 'Tomar foto',
  'hero.cta2': 'Escribir el ejercicio',
  'hero.trust1': 'Las fotos no se guardan',
  'hero.trust2': 'Respuestas verificadas con calculadora',
  'hero.trust3': 'Funciona también sin internet',
  'tutor.title': 'Tu ejercicio',
  'tutor.drop': 'Arrastra una foto aquí o',
  'tutor.choose': 'elige un archivo',
  'tutor.camera': 'Usar la cámara',
  'tutor.or': 'o escríbelo',
  'tutor.textPh': 'Ejemplo: 2x + 3 = 7',
  'tutor.askPh': 'Opcional: ¿qué quieres saber?',
  'tutor.send': 'Resolver',
  'tutor.reading': 'Leyendo tu ejercicio…',
  'tutor.solving': 'Resolviendo paso a paso…',
  'tutor.slow': 'El tutor puede tardar hasta un minuto. Gracias por la paciencia.',
  'tutor.confirmTitle': 'Esto es lo que leí',
  'tutor.confirmHelp': 'Si algo está mal, corrígelo antes de seguir. Así el tutor no resuelve otro ejercicio.',
  'tutor.chooseOne': 'Hay varios ejercicios en la foto. ¿Cuál resuelvo?',
  'tutor.confirm': 'Sí, resuélvelo',
  'tutor.retake': 'Cambiar foto',
  'tutor.new': 'Nuevo ejercicio',
  'tutor.notMath': 'No veo un ejercicio de matemáticas en esta foto. Prueba con una foto más clara y bien iluminada.',
  'tutor.fallback': 'El tutor está despertando o muy ocupado. Prueba otra vez en un minuto.',
  'tutor.retry': 'Reintentar',
  'tutor.imageError': 'No pude abrir esa imagen. Usa una foto JPG, PNG o WEBP.',
  'tutor.photoAlt': 'Foto del ejercicio',
  'result.answer': 'Respuesta',
  'result.steps': 'Cómo se resuelve',
  'result.calc': 'La calculadora dice',
  'result.reading': 'Ejercicio',
  'result.report': '¿Ves un error? Repórtalo',
  'result.disclaimer': 'Vertex Math Vision es un modelo pequeño y puede equivocarse. Úsalo para aprender, no para copiar: revisa siempre los pasos.',
  'verify.verified': 'Verificado',
  'verify.mismatch': 'No coincide con la calculadora',
  'verify.ill_posed': 'Ejercicio mal planteado',
  'verify.steps_ok': 'Cuentas correctas · planteamiento sin verificar',
  'verify.steps_wrong': 'Hay una cuenta mal',
  'verify.unverified': 'Sin verificar',
  'verify.not_math': 'No es un ejercicio',
  'how.title': 'Cómo funciona',
  'how.sub': 'Cuatro pasos, y en ninguno te dejamos con una respuesta que no se ha comprobado.',
  'how.1t': 'Foto', 'how.1d': 'Saca una foto clara del ejercicio, aunque esté escrito a mano.',
  'how.2t': 'Revisa', 'how.2d': 'Te enseñamos lo que leímos para que lo corrijas si hace falta.',
  'how.3t': 'Aprende', 'how.3d': 'La solución paso a paso, no solo el resultado.',
  'how.4t': 'Verificado', 'how.4d': 'Una calculadora comprueba la respuesta cuando es posible. Si no puede, te lo decimos.',
  'offline.title': 'Úsalo sin internet',
  'offline.sub': 'El mismo modelo corre en tu computadora con LM Studio, gratis y sin enviar nada a internet.',
  'offline.1': 'Instala LM Studio desde lmstudio.ai.',
  'offline.2': 'Busca «Denisijcu/vertex-math-vision-GGUF» y descarga la versión Q4_K_M (1,1 GB). LM Studio baja también la parte que ve las imágenes.',
  'offline.3': 'Pon la temperatura en 0.2 y abre un chat nuevo para cada ejercicio.',
  'offline.4': 'Arrastra la foto al chat y escribe «Resuelve este problema».',
  'offline.cta': 'Ver el modelo en Hugging Face',
  'offline.note': 'Sin conexión no hay calculadora que verifique: revisa los pasos con calma.',
  'faq.title': 'Preguntas frecuentes',
  'faq.1q': '¿Es gratis?', 'faq.1a': 'Sí, completamente gratis.',
  'faq.2q': '¿Guardan mis fotos?', 'faq.2a': 'No. La foto se usa solo para resolver el ejercicio y se descarta. Antes de enviarla le quitamos los datos ocultos, como la ubicación.',
  'faq.3q': '¿Qué significa «Sin verificar»?', 'faq.3a': 'Que la calculadora no puede comprobar ese tipo de problema (problemas de texto, relojes, gráficas, figuras). Revisa el resultado con más cuidado.',
  'faq.4q': '¿Para qué cursos sirve?', 'faq.4a': 'Primaria y secundaria. No está pensado para la universidad.',
  'faq.5q': '¿Puedo usarlo sin internet?', 'faq.5a': 'Sí: descarga el modelo en LM Studio. Te lo explicamos en «Úsalo sin internet».',
  'faq.6q': '¿Por qué a veces se equivoca?', 'faq.6a': 'Es un modelo pequeño, pensado para correr incluso en una computadora sencilla. Lee muy bien, pero en ejercicios largos puede fallar. Por eso verificamos y te avisamos.',
  'report.title': 'Reportar un error del tutor',
  'report.sub': 'Cuéntanos qué salió mal. Solo guardamos el texto que escribas aquí; nunca la foto.',
  'report.msg': '¿Qué salió mal?',
  'report.msgPh': 'Ejemplo: el reloj marcaba 4:10 y dijo 2:45.',
  'report.email': 'Email (opcional, por si quieres respuesta)',
  'report.send': 'Enviar reporte',
  'report.sending': 'Enviando…',
  'report.ok': '¡Gracias! Lo usaremos para mejorar el tutor.',
  'report.error': 'No se pudo enviar. Inténtalo de nuevo.',
  'footer.made': 'Hecho por',
  'footer.privacy': 'Privacidad',
  'footer.rights': 'Todos los derechos reservados.',
  'privacy.title': 'Política de privacidad',
  'privacy.back': 'Volver al tutor',
  'error.generic': 'Algo falló. Inténtalo de nuevo.',
  'error.timeout': 'El tutor tardó demasiado en responder. Inténtalo de nuevo.',
  'error.network': 'No hay conexión con el tutor. Revisa tu internet e inténtalo de nuevo.',
};

type Key = keyof typeof ES;

const EN: Record<Key, string> = {
  'skip': 'Skip to content',
  'nav.home': 'Home',
  'nav.how': 'How it works',
  'nav.offline': 'Use it offline',
  'nav.faq': 'FAQ',
  'nav.report': 'Report an error',
  'nav.menu': 'Open menu',
  'status.up': 'Tutor online',
  'status.down': 'Tutor asleep',
  'status.checking': 'Checking…',
  'hero.badge': 'Vertex Coders’ own model · free',
  'hero.title1': 'Snap a photo.',
  'hero.title2': 'Understand it step by step.',
  'hero.sub': 'Your math tutor for elementary, middle and high school, in English or Spanish. It reads your exercise, even handwritten, and explains how to solve it.',
  'hero.cta1': 'Take a photo',
  'hero.cta2': 'Type the exercise',
  'hero.trust1': 'Photos are never stored',
  'hero.trust2': 'Answers checked with a calculator',
  'hero.trust3': 'Also works offline',
  'tutor.title': 'Your exercise',
  'tutor.drop': 'Drag a photo here or',
  'tutor.choose': 'choose a file',
  'tutor.camera': 'Use the camera',
  'tutor.or': 'or type it',
  'tutor.textPh': 'Example: 2x + 3 = 7',
  'tutor.askPh': 'Optional: what do you want to know?',
  'tutor.send': 'Solve',
  'tutor.reading': 'Reading your exercise…',
  'tutor.solving': 'Solving step by step…',
  'tutor.slow': 'The tutor can take up to a minute. Thanks for your patience.',
  'tutor.confirmTitle': 'This is what I read',
  'tutor.confirmHelp': 'If something is wrong, fix it before going on, so the tutor doesn’t solve a different exercise.',
  'tutor.chooseOne': 'There are several exercises in the photo. Which one should I solve?',
  'tutor.confirm': 'Yes, solve it',
  'tutor.retake': 'Change photo',
  'tutor.new': 'New exercise',
  'tutor.notMath': 'I can’t see a math exercise in this photo. Try a clearer, well-lit photo.',
  'tutor.fallback': 'The tutor is waking up or very busy. Please try again in a minute.',
  'tutor.retry': 'Try again',
  'tutor.imageError': 'I couldn’t open that image. Please use a JPG, PNG or WEBP photo.',
  'tutor.photoAlt': 'Photo of the exercise',
  'result.answer': 'Answer',
  'result.steps': 'How to solve it',
  'result.calc': 'The calculator says',
  'result.reading': 'Exercise',
  'result.report': 'See a mistake? Report it',
  'result.disclaimer': 'Vertex Math Vision is a small model and can make mistakes. Use it to learn, not to copy: always check the steps.',
  'verify.verified': 'Verified',
  'verify.mismatch': 'Doesn’t match the calculator',
  'verify.ill_posed': 'Ill-posed exercise',
  'verify.steps_ok': 'Arithmetic correct · setup not verified',
  'verify.steps_wrong': 'Arithmetic mistake',
  'verify.unverified': 'Not verified',
  'verify.not_math': 'Not an exercise',
  'how.title': 'How it works',
  'how.sub': 'Four steps, and none of them leaves you with an answer nobody checked.',
  'how.1t': 'Photo', 'how.1d': 'Take a clear photo of the exercise, even if it’s handwritten.',
  'how.2t': 'Review', 'how.2d': 'We show you what we read so you can fix it if needed.',
  'how.3t': 'Learn', 'how.3d': 'The solution step by step, not just the result.',
  'how.4t': 'Verified', 'how.4d': 'A calculator checks the answer when possible. When it can’t, we tell you.',
  'offline.title': 'Use it offline',
  'offline.sub': 'The same model runs on your computer with LM Studio, free and without sending anything to the internet.',
  'offline.1': 'Install LM Studio from lmstudio.ai.',
  'offline.2': 'Search for “Denisijcu/vertex-math-vision-GGUF” and download the Q4_K_M version (1.1 GB). LM Studio also downloads the part that sees images.',
  'offline.3': 'Set the temperature to 0.2 and open a new chat for every exercise.',
  'offline.4': 'Drag the photo into the chat and type “Solve this problem”.',
  'offline.cta': 'See the model on Hugging Face',
  'offline.note': 'Offline there is no calculator to check the answer: review the steps carefully.',
  'faq.title': 'Frequently asked questions',
  'faq.1q': 'Is it free?', 'faq.1a': 'Yes, completely free.',
  'faq.2q': 'Do you store my photos?', 'faq.2a': 'No. The photo is only used to solve the exercise and then discarded. Before sending it we strip hidden data such as the location.',
  'faq.3q': 'What does “Not verified” mean?', 'faq.3a': 'That the calculator can’t check that kind of problem (word problems, clocks, graphs, figures). Review the result more carefully.',
  'faq.4q': 'Which grades is it for?', 'faq.4a': 'Elementary, middle and high school. It isn’t meant for university.',
  'faq.5q': 'Can I use it offline?', 'faq.5a': 'Yes: download the model in LM Studio. We explain how in “Use it offline”.',
  'faq.6q': 'Why does it sometimes make mistakes?', 'faq.6a': 'It’s a small model, built to run even on a modest computer. It reads very well, but on long exercises it can fail. That’s why we verify and warn you.',
  'report.title': 'Report a tutor error',
  'report.sub': 'Tell us what went wrong. We only store the text you write here; never the photo.',
  'report.msg': 'What went wrong?',
  'report.msgPh': 'Example: the clock showed 4:10 and it said 2:45.',
  'report.email': 'Email (optional, if you’d like a reply)',
  'report.send': 'Send report',
  'report.sending': 'Sending…',
  'report.ok': 'Thank you! We’ll use it to improve the tutor.',
  'report.error': 'It couldn’t be sent. Please try again.',
  'footer.made': 'Made by',
  'footer.privacy': 'Privacy',
  'footer.rights': 'All rights reserved.',
  'privacy.title': 'Privacy policy',
  'privacy.back': 'Back to the tutor',
  'error.generic': 'Something went wrong. Please try again.',
  'error.timeout': 'The tutor took too long to answer. Please try again.',
  'error.network': 'Can’t reach the tutor. Check your connection and try again.',
};

const DICT: Record<Lang, Record<Key, string>> = { es: ES, en: EN };
const STORAGE_KEY = 'vmv.lang';

@Injectable({ providedIn: 'root' })
export class I18n {
  private readonly doc = inject(DOCUMENT);
  readonly lang = signal<Lang>(this.initial());

  constructor() {
    effect(() => {
      const l = this.lang();
      this.doc.documentElement.lang = l;
      try { localStorage.setItem(STORAGE_KEY, l); } catch { /* modo privado: no pasa nada */ }
    });
  }

  t(key: Key): string {
    return DICT[this.lang()][key];
  }

  set(lang: Lang): void {
    this.lang.set(lang);
  }

  private initial(): Lang {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'es' || saved === 'en') return saved;
    } catch { /* sin localStorage */ }
    const nav = (globalThis.navigator?.language || 'es').toLowerCase();
    return nav.startsWith('es') ? 'es' : 'en';
  }
}

export type I18nKey = Key;
