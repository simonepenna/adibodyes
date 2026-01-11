interface StockItem {
  sku: string;
  modelo: string;
  talla: string;
  magazzino_attuale: number;
  in_arrivo: number;
  totale_disponibile: number;
  ordini_arretrati: number;
  magazzino_netto: number;
  media_vendite_giornaliere: number;
  giorni_autonomia: number;
  urgenza: 'CRITICO' | 'ORDINARE' | 'OK';
}

interface OrdineFornitoreItem {
  sku: string;
  modelo: string;
  talla: string;
  quantita: number;
  urgenza: 'CRITICO' | 'ORDINARE';
  giorni_autonomia: number;
}

interface StockSummary {
  totale_sku: number;
  totale_pezzi_stock: number;
  totale_magazzino_attuale: number;
  totale_in_arrivo: number;
  sku_critici: number;
  sku_da_ordinare: number;
  totale_pezzi_ordine: number;
}

export interface StockResponse {
  stock: StockItem[];
  ordine_fornitore: OrdineFornitoreItem[];
  summary: StockSummary;
  timestamp: string;
}

const LAMBDA_URL = 'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod/stock';

export const fetchStockData = async (): Promise<StockResponse> => {
  try {
    const response = await fetch(LAMBDA_URL);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching stock data:', error);
    throw error;
  }
};
