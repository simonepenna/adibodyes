export interface RefundOrder {
  id: string;
  name: string;
  created_at: string;
  tags: string[];
  note: string | null;
  customer: {
    displayName: string;
    phone: string | null;
  } | null;
  shipping_address: {
    name: string;
    address1: string;
    city: string;
    province: string;
    country: string;
    phone: string | null;
  } | null;
  total_price: string;
  currency: string;
  fulfillment_status: string;
  financial_status: string;
  fully_paid: boolean;
  refunds: Array<{
    id: string;
    createdAt: string;
    note: string | null;
  }>;
}

interface RefundOrdersMetadata {
  extraction_date: string;
  period_days: number;
  total_orders: number;
  required_tags: string[];
}

export interface RefundOrdersResponse {
  metadata: RefundOrdersMetadata;
  orders: RefundOrder[];
}

const LAMBDA_URL = 'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod/refunds';

export const fetchRefundOrders = async () => {
  try {
    const response = await fetch(LAMBDA_URL, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Errore nel recupero ordini da rimborsare: ${response.statusText}`);
    }

    const data = await response.json();

    // Se la risposta è in formato Lambda (con body), parsala
    if (data.body) {
      return JSON.parse(data.body);
    }

    return data;
  } catch (error) {
    console.error('Errore fetchRefundOrders:', error);
    throw error;
  }
};