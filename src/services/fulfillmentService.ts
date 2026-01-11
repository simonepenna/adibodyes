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
}

export interface FulfillmentOrder {
  id: string;
  name: string;
  created_at: string;
  financial_status: string;
  customer_name: string;
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
