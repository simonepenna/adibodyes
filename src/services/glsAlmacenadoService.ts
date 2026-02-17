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

export const fetchGLSAlmacenadoData = async (daysBack: number = 15) => {
  try {
    const response = await fetch(LAMBDA_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        days_back: daysBack
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data: GLSAlmacenadoResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching GLS Almacenado data:', error);
    throw error;
  }
};