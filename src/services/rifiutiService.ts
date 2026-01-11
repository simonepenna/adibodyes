export interface Rifiuto {
  fecha: string;
  expedicion: string;
  referencia: string;
  destinatario: string;
  localidad: string;
  estado: string;
  servizio?: string;
  stato_pagamento?: string;
  ha_tag_rifiuto: boolean;
  order_id?: string;
}

export interface RifiutiResponse {
  summary: {
    totale: number;
    in_transito: number;
    consegnati: number;
    da_taggare: number;
    gia_taggati: number;
  };
  rifiuti: Rifiuto[];
  ordini_da_taggare: Array<{
    order_id: string;
    referenza: string;
    destinatario: string;
    fecha: string;
    stato_pagamento: string;
  }>;
}

export interface TagResponse {
  success: boolean;
  message?: string;
  error?: string;
  order_id?: string;
}

export interface BulkTagResponse {
  success: boolean;
  total?: number;
  success_count?: number;
  error_count?: number;
  results?: Array<{
    order_id: string;
    success: boolean;
    message: string;
  }>;
  message?: string;
  preview?: boolean;
  orders_to_tag?: string[];
  count?: number;
}

const API_BASE_URL = 'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod';

const rifiutiService = {
  async getRifiuti(daysBack: number = 7): Promise<RifiutiResponse> {
    const response = await fetch(`${API_BASE_URL}/rifiuti?days_back=${daysBack}`);

    if (!response.ok) {
      throw new Error(`Errore nel recupero rifiuti: ${response.statusText}`);
    }

    const data: RifiutiResponse = await response.json();
    return data;
  },

  async addTagRifiuto(orderId: string, orderName: string): Promise<TagResponse> {
    const response = await fetch(`${API_BASE_URL}/rifiuti/tag`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        order_id: orderId,
        order_name: orderName
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `Errore aggiunta tag: ${response.statusText}`);
    }

    return await response.json();
  },

  async tagOrdini(orderIds: string[], preview: boolean = false): Promise<BulkTagResponse> {
    const response = await fetch(`${API_BASE_URL}/rifiuti/tag`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        order_ids: orderIds,
        preview: preview
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `Errore tagging ordini: ${response.statusText}`);
    }

    return await response.json();
  },
};

export default rifiutiService;
