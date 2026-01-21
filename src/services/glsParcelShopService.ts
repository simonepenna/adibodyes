export interface GLSParcelShopItem {
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

interface GLSParcelShopMetadata {
  extraction_date: string;
  period: string;
  total_shipments: number;
  status_filter: string;
}

export interface GLSParcelShopResponse {
  metadata: GLSParcelShopMetadata;
  shipments: GLSParcelShopItem[];
}

const LAMBDA_URL = 'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod/parcel-shop';

export const fetchGLSParcelShopData = async (daysBack: number = 15) => {
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

    const data = await response.json();
    console.log('Raw API response:', data);

    // Se la risposta è in formato Lambda (con body), estrai il body
    if (data.body && typeof data.body === 'string') {
      const parsedBody = JSON.parse(data.body);
      console.log('Parsed body:', parsedBody);
      return parsedBody;
    }

    return data;
  } catch (error) {
    console.error('Errore nel fetch GLS Parcel Shop:', error);
    throw error;
  }
};