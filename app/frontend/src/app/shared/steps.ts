/** Convierte la respuesta del modelo ("**Paso 1:** …", "**Comprobación:** …") en bloques para pintarlos como tarjetas. */
export type BlockKind = 'ask' | 'see' | 'step' | 'check' | 'text';

export interface Block {
  kind: BlockKind;
  label: string;
  body: string;
  n?: number;
}

const LABEL = /^\s*\*\*([^*]{1,40}?):?\*\*:?\s*(.*)$/;

function kindOf(label: string): { kind: BlockKind; n?: number } | null {
  const l = label.toLowerCase();
  const step = l.match(/^(?:paso|step)\s*(\d+)/);
  if (step) return { kind: 'step', n: Number(step[1]) };
  if (/^(respuesta|answer|respuesta final|final answer|boxed answer|respuesta en caja)/.test(l)) return null; // la respuesta se pinta aparte
  if (/(piden|pregunta|need to find|asked|question)/.test(l)) return { kind: 'ask' };
  if (/\b(veo|s[eé]|datos|see|know|given)\b/.test(l)) return { kind: 'see' };
  if (/(comprob|check|verific)/.test(l)) return { kind: 'check' };
  return { kind: 'text' };
}

/**
 * A veces el modelo lo escribe todo en un solo párrafo ("… **Step 1:** … **Step 2:** …").
 * Cada etiqueta en negrita que termina en ":" empieza una línea nueva, así cada paso sale en su tarjeta.
 * Solo las que terminan en ":" — una negrita normal dentro de una frase no se toca.
 */
const INLINE_LABEL = /[ \t]+(\*\*[^*\n]{1,40}?:\*\*|\*\*[^*\n]{1,40}?\*\*:)/g;

export function parseSteps(raw: string): Block[] {
  const blocks: Block[] = [];
  let skipping = false;
  for (const line of (raw || '').replace(INLINE_LABEL, '\n$1').split('\n')) {
    const m = line.match(LABEL);
    if (m) {
      const k = kindOf(m[1]);
      if (!k) { skipping = true; continue; }
      skipping = false;
      blocks.push({ kind: k.kind, label: m[1].trim(), body: m[2].trim(), n: k.n });
      continue;
    }
    if (skipping) continue;
    if (!line.trim()) continue;
    if (/\\boxed\s*\{/.test(line) && blocks.length) continue; // "$\boxed{5}$" suelto al final
    const last = blocks[blocks.length - 1];
    if (last) last.body += (last.body ? '\n' : '') + line.trim();
    else blocks.push({ kind: 'text', label: '', body: line.trim() });
  }
  return blocks;
}
