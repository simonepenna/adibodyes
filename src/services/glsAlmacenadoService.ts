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
  already_contacted: string | null; // Data contatto (es. "2026-02-19 14:30") o null
}

interface GLSAlmacenadoMetadata {
  extraction_date: string;
  period: string;
  total_shipments: number;
  total_including_contacted: number;
  already_contacted_skipped: number;
  show_all: boolean;
  status_filter: string;
}

export interface GLSAlmacenadoResponse {
  metadata: GLSAlmacenadoMetadata;
  shipments: GLSAlmacenadoItem[];
}

const LAMBDA_URL = 'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod/almacenado';
const MARK_CONTACTED_URL = 'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod/mark-contacted';

export const fetchGLSAlmacenadoData = async (daysBack: number = 15, showAll: boolean = false) => {
  try {
    const response = await fetch(LAMBDA_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ days_back: daysBack, show_all: showAll })
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data: GLSAlmacenadoResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching GLS Almacenado data:', error);
    throw error;
  }
};

export const markContacted = async (expedicion: string, referencia?: string): Promise<boolean> => {
  try {
    const response = await fetch(MARK_CONTACTED_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expedicion, referencia })
    });
    const data = await response.json();
    return data.success === true;
  } catch (error) {
    console.error('Error marking contacted:', error);
    return false;
  }
};