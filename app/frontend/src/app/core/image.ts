/**
 * Prepara la foto en el navegador antes de enviarla:
 * - la gira según la orientación de la cámara,
 * - limita el lado mayor a 1280 px (el backend no necesita más y en el móvil se envía mucho más rápido),
 * - la vuelve a codificar como JPEG, lo que además elimina los metadatos EXIF (ubicación GPS incluida).
 */
const MAX_SIDE = 1280;
const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif', ''];

export class ImageError extends Error {}

export async function prepareImage(file: File): Promise<Blob> {
  if (!ACCEPTED.includes(file.type) && !file.type.startsWith('image/')) {
    throw new ImageError('unsupported');
  }
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
  } catch {
    throw new ImageError('decode'); // p. ej. HEIC en un navegador que no lo entiende
  }
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const w = Math.round(bitmap.width * scale);
  const h = Math.round(bitmap.height * scale);
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new ImageError('canvas');
  ctx.fillStyle = '#ffffff'; // PNG con transparencia → fondo blanco, como el papel
  ctx.fillRect(0, 0, w, h);
  ctx.drawImage(bitmap, 0, 0, w, h);
  bitmap.close();
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  if (!blob) throw new ImageError('encode');
  return blob;
}
