/**
 * Service for fetching fulfillment data from Lambda API
 */

export interface FulfillmentItem {
  sku: string;
  title: string;
  quantity: number;
  modelo: string;
  talla: string;
  available: number | string;
  sufficient: boolean;
  status: 'OK' | 'MISSING' | 'UNKNOWN';
}

export interface ShippingAddress {
  address1?: string;
  address2?: string;
  city?: string;
  province?: string;
  zip?: string;
  country?: string;
  phone?: string;
}

export interface FulfillmentOrder {
  id: string;
  name: string;
  created_at: string;
  financial_status: string;
  customer_name: string;
  email?: string; // Aggiunto campo email opzionale
  total_price: string;
  note: string;
  tags: string[];
  items: FulfillmentItem[];
  category: 'GREEN' | 'YELLOW' | 'RED';
  category_label: string;
  warnings: string[];
  can_fulfill: boolean;
  shipping_address?: ShippingAddress;
}

export interface FulfillmentSummary {
  total: number;
  green: number;
  yellow: number;
  red: number;
}

export interface FulfillmentData {
  summary: FulfillmentSummary;
  orders: {
    green: FulfillmentOrder[];
    yellow: FulfillmentOrder[];
    red: FulfillmentOrder[];
  };
}

const LAMBDA_URL = 'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod/orders/check-fulfillment';

export const fetchFulfillmentData = async (days: number = 4): Promise<FulfillmentData> => {
  try {
    const url = `${LAMBDA_URL}?days=${days}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching fulfillment data:', error);
    throw error;
  }
};

// Lambda fulfillment interfaces and functions
const LAMBDA_BASE_URL = 'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod';

export interface FulfillOrderRequest {
  orderId: string;
  orderName: string;
  customerName: string;
  shippingAddress: {
    address1?: string;
    address2?: string;
    city?: string;
    zip?: string;
    country?: string;
    phone?: string;
  };
  items: Array<{
    sku: string;
    quantity: number;
    title?: string;
  }>;
  totalPrice: string;
  financialStatus: string;
  email: string;
  customObservations?: string;
  notifyCustomer?: boolean;
}

export interface FulfillOrderResponse {
  success: boolean;
  trackingNumber?: string;
  message?: string;
  error?: string;
}

/**
 * Chiama la Lambda per evadere un ordine (GLS + Shopify)
 * Endpoint: /orders/fulfill
 */
export async function fulfillOrderLambda(data: FulfillOrderRequest): Promise<FulfillOrderResponse> {
  try {
    console.log('🚀 Chiamata Lambda /orders/fulfill');
    console.log('📦 Dati:', data);

    const response = await fetch(`${LAMBDA_BASE_URL}/orders/fulfill`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    console.log('✅ Risposta Lambda:', result);

    return {
      success: result.success || false,
      trackingNumber: result.trackingNumber,
      message: result.message,
      error: result.error
    };

  } catch (error) {
    console.error('❌ Errore chiamata Lambda:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Errore sconosciuto'
    };
  }
}
