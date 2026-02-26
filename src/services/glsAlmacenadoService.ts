export interface GLSAlmacenadoItem {
  expedicion: string;
  referencia: string;
  destinatario: string;
  direccion: string;
  localidad: string;
  estado: string;
  fecha: string;
  bultos: string;
  kgs: string;
  servicio: string;
  horario: string;
  reembolso: string;
  pod: string;
  phone: string | null;
  dac: string;
  retorno: string;
  nombre_org: string;
  localidad_org: string;
  fecha_actualizacion: string;
  cp_dst: string;
  indirizzo_agenzia: string | null;
  telefono_agenzia: string | null;
  orari_agenzia: string | null;
}

interface GLSAlmacenadoMetadata {
  extraction_date: string;
  period: string;
  total_shipments: number;
  status_filter: string;
}

export interface GLSAlmacenadoResponse {
  metadata: GLSAlmacenadoMetadata;
  shipments: GLSAlmacenadoItem[];
}

const LAMBDA_URL = 'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod/almacenado';

export interface AgenziaDetails {
  indirizzo_agenzia: string | null;
  telefono_agenzia: string | null;
  orari_agenzia: string | null;
}

export const fetchGLSAlmacenadoData = async (daysBack: number = 14) => {
  try {
    const response = await fetch(LAMBDA_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ days_back: daysBack })
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data: GLSAlmacenadoResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching GLS Almacenado data:', error);
    throw error;
  }
};

export const fetchAgenziaDetails = async (expedicion: string): Promise<AgenziaDetails> => {
  const response = await fetch(LAMBDA_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'get_agenzia', expedicion }),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return response.json();
};

// ─── Email parsing ────────────────────────────────────────────────────────────

export type MotivoCategoria =
  | 'AUSENTE'
  | 'RECHAZA'
  | 'DEVOLUCION'
  | 'DIRECCION'
  | 'PAGO'
  | 'RECOGIDA'
  | 'CONCERTADA'
  | 'OTRO';

export interface ParsedEmailEntry {
  expedicion: string;
  nombre: string;
  motivoRaw: string;
  categoria: MotivoCategoria;
}

export interface CategoriaConfig {
  label: string;
  badgeClass: string;
}

export const CATEGORIA_CONFIG: Record<MotivoCategoria, CategoriaConfig> = {
  AUSENTE:    { label: 'Ausente',          badgeClass: 'badge-warning' },
  RECHAZA:    { label: 'Rechaza envío',    badgeClass: 'badge-error' },
  DEVOLUCION: { label: 'Devolución',       badgeClass: 'badge-error' },
  DIRECCION:  { label: 'Dirección incorrecta', badgeClass: 'badge-info' },
  PAGO:       { label: 'Problema pago',    badgeClass: 'badge-warning' },
  RECOGIDA:   { label: 'Recoger agencia',  badgeClass: 'badge-success' },
  CONCERTADA: { label: 'Concertada',       badgeClass: 'badge-success' },
  OTRO:       { label: 'Otro',             badgeClass: 'badge-ghost' },
};

export function categorizeMotivo(motivo: string): MotivoCategoria {
  const m = motivo.toLowerCase();
  if (m.includes('concertad')) return 'CONCERTADA';
  if (
    m.includes('rechaz') ||
    m.includes('no acepta') ||
    m.includes('indica que no') ||
    m.includes('no lo quiere')
  ) return 'RECHAZA';
  if (m.includes('devolvemos') || m.includes('devuelvan') || m.includes('devoluci')) return 'DEVOLUCION';
  if (m.includes('direcci') || m.includes('incorrecta') || m.includes('tlf es incorrecto')) return 'DIRECCION';
  if (m.includes('cambio') || m.includes('tarjeta') || m.includes('solo pagar')) return 'PAGO';
  if (
    m.includes('parcell') ||
    m.includes('parcelshop') ||
    m.includes('delegaci') ||
    m.includes('agencia') ||
    m.includes('recoger')
  ) return 'RECOGIDA';
  return 'AUSENTE';
}

export function parseGLSEmail(text: string): ParsedEmailEntry[] {
  // Decode quoted-printable encoding (e.g. =E1 → á, =F3 → ó, soft line breaks)
  let decoded = text
    .replace(/=\r?\n/g, '')  // soft line breaks
    .replace(/=([0-9A-Fa-f]{2})/g, (_, hex) => {
      try { return decodeURIComponent('%' + hex); } catch { return ''; }
    });

  // Se è un'email MIME (.eml), estrai solo la sezione text/plain
  // La sezione text/plain si trova dopo "Content-Type: text/plain..." + riga vuota
  // e termina al prossimo boundary
  if (/Content-Type:\s*text\/plain/i.test(decoded)) {
    const plainMatch = decoded.match(
      /Content-Type:\s*text\/plain[^\n]*\n(?:[^\n]+\n)*\n([\s\S]+?)(?=\n--|\n------=_NextPart|$)/i
    );
    if (plainMatch) decoded = plainMatch[1];
  }

  // Tronca al tag HTML o a marcatori tipici di firma nel plain text
  const cutIdx = decoded.search(/<html[\s>]|<http|Este mensaje|This message|Mensaje confidencial|mensaje.*confidencial/i);
  if (cutIdx !== -1) decoded = decoded.slice(0, cutIdx);

  const results: ParsedEmailEntry[] = [];
  const seen = new Set<string>();
  const isShipmentLine = (l: string) => /^\d{9,10}[\s\-+]/.test(l);

  // Pattern tipici di firme email da ignorare come continuazione
  const isSignatureLine = (l: string) =>
    /^(tel[.:éf]|fax|www\.|http|mailto:|c\/\s|calle\s|avda?\.|pol[íi]gono|departamento|administrac)/i.test(l) ||
    /\d{9}@|@[a-z]+\.[a-z]{2,}/.test(l) ||
    // Riga con sole parole in TitleCase senza verbi/preposizioni comuni del motivo → nome mittente/azienda
    (
      /^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,5}$/.test(l) &&
      !/\b(no|en|de|la|el|que|para|por|pero|con|sin|al|una|un|llamamos|ausente|rechaz|acepta|indica|responde|recoger|mando|conciert|concert|pendiente|devol|direcc|tlf)\b/i.test(l)
    );

  for (const rawLine of decoded.split('\n')) {
    const line = rawLine.trim();
    if (!line) continue;

    // Format A: "1253052382- Tatiana Santana:Motivo..." or "1256387608+- Verónica: ..."
    const matchColon = line.match(/^(\d{9,10})\s*[+\-]*[-]?\s*(.+?)\s*:\s*(.+)$/);
    if (matchColon) {
      const expedicion = matchColon[1];
      const nombre = matchColon[2].trim().replace(/^[-\s]+/, '');
      const motivo = matchColon[3].trim();
      if (!seen.has(expedicion) && motivo) {
        seen.add(expedicion);
        results.push({ expedicion, nombre, motivoRaw: motivo, categoria: categorizeMotivo(motivo) });
      }
      continue;
    }

    // Format B: "1258444157 Marian Montesinos Garcia, Ausente..." or "1249452939- Antonia Campos,Pendiente..."
    const matchComma = line.match(/^(\d{9,10})\s*[-+]*\s+([^,:]+),\s*(.+)$/);
    if (matchComma) {
      const expedicion = matchComma[1];
      const nombre = matchComma[2].trim();
      const motivo = matchComma[3].trim();
      if (!seen.has(expedicion) && motivo) {
        seen.add(expedicion);
        results.push({ expedicion, nombre, motivoRaw: motivo, categoria: categorizeMotivo(motivo) });
      }
      continue;
    }

    // Linea di continuazione: appende al motivoRaw dell'ultimo elemento
    // Ignora linee che sembrano firma o intestazione
    if (results.length > 0 && !isShipmentLine(line) && !isSignatureLine(line)) {
      const last = results[results.length - 1];
      last.motivoRaw = last.motivoRaw + ' ' + line;
      last.categoria = categorizeMotivo(last.motivoRaw);
    }
  }

  return results;
}

export function buildWhatsAppMessage(
  entrada: ParsedEmailEntry,
  referencia?: string,
  reembolso?: string,
  agenzia?: AgenziaDetails,
  expedicion?: string,
): string {
  const nombre = entrada.nombre.split(' ')[0];
  const ref = referencia ? `\n📦 Pedido: #ES${referencia}` : '';
  const envio = expedicion ? `\n🚚 Nº envío GLS: ${expedicion}` : '';

  switch (entrada.categoria) {
    case 'AUSENTE':
      return (
        `¡Hola ${nombre}!\nSomos el equipo de AdiBody\n\n` +
        `Hemos intentado entregarte tu pedido pero no había nadie en casa.${ref}${envio}\n\n` +
        `¿Cuándo te va bien que volvamos a intentarlo? 😊`
      );
    case 'RECHAZA':
      return (
        `¡Hola ${nombre}!\nSomos el equipo de AdiBody\n\n` +
        `Hemos recibido información de que ha habido un problema con la aceptación de tu pedido.${ref}${envio}\n\n` +
        `¿Podemos ayudarte a resolverlo? Estamos aquí para lo que necesites 🙏`
      );
    case 'DEVOLUCION':
      return (
        `¡Hola ${nombre}!\nSomos el equipo de AdiBody\n\n` +
        `Nos han indicado que no deseas recibir tu pedido.${ref}${envio}\n\n` +
        `Si fue un malentendido o quieres recuperarlo, ¡escríbenos! Buscamos una solución 📦`
      );
    case 'DIRECCION':
      return (
        `¡Hola ${nombre}!\nSomos el equipo de AdiBody\n\n` +
        `Nuestro mensajero no ha podido localizar tu dirección para entregarte tu pedido.${ref}${envio}\n\n` +
        `¿Puedes confirmarnos la dirección correcta? Así organizamos una nueva entrega 📍`
      );
    case 'PAGO':
      return (
        `¡Hola ${nombre}!\nSomos el equipo de AdiBody\n\n` +
        `Tu pedido se entrega con pago en efectivo` +
        (reembolso ? ` (importe: ${reembolso})` : '') +
        `.${ref}${envio}\n\n` +
        `¿Puedes tener el importe exacto preparado para la próxima entrega? 💶`
      );
    case 'RECOGIDA':
      return (
        `¡Hola ${nombre}!\nSomos el equipo de AdiBody\n\n` +
        `Tu paquete está pendiente de recoger en la agencia GLS de tu zona.${ref}${envio}\n\n` +
        (agenzia?.indirizzo_agenzia ? `📍 Dirección: ${agenzia.indirizzo_agenzia}\n` : '') +
        (agenzia?.telefono_agenzia ? `📞 Teléfono: ${agenzia.telefono_agenzia}\n` : '') +
        (agenzia?.orari_agenzia ? `🕐 Horarios: ${agenzia.orari_agenzia}\n` : '') +
        `\nPuedes ir a recogerlo antes de que sea devuelto al remitente 🏃`
      );
    case 'CONCERTADA':
      return (
        `¡Hola ${nombre}!\nSomos el equipo de AdiBody\n\n` +
        `Hemos concertado una nueva entrega para tu pedido.${ref}${envio}\n\n` +
        `¡Te esperamos en casa! 🏠 Cualquier cambio, escríbenos.`
      );
    default:
      return (
        `¡Hola ${nombre}!\nSomos el equipo de AdiBody\n\n` +
        `Estamos intentando entregarte tu pedido y ha habido un pequeño inconveniente.${ref}${envio}\n\n` +
        `¿Puedes contactarnos para resolverlo? 😊`
      );
  }
}
