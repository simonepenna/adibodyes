/**
 * Service per chiamare le Lambda Shopify
 */

// TODO: Sostituisci con l'URL della tua Lambda dopo il deploy
const LAMBDA_ORDER_STATS_URL = import.meta.env.VITE_LAMBDA_ORDER_STATS_URL ||
  'https://i5g7wtxgec.execute-api.eu-central-1.amazonaws.com/prod/order-stats';
export interface OrderStats {
  total_orders: number;
  orders_by_tag: {
    RESO: number;
    CAMBIO: number;
    RIFIUTO: number;
    other: number;
  };
  fulfillment_status: {
    FULFILLED: number;
    UNFULFILLED: number;
    PARTIALLY_FULFILLED: number;
    SCHEDULED: number;
    ON_HOLD: number;
  };
  financial_status: {
    PAID: number;
    PARTIALLY_PAID: number;
    PENDING: number;
    REFUNDED: number;
    VOIDED: number;
    AUTHORIZED: number;
    PARTIALLY_REFUNDED: number;
  };
  payment_status: {
    fully_paid: number;
    unpaid: number;
    partially_paid: number;
  };
  cancelled_orders: number;
  orders_with_refunds: number;
  total_revenue: number;
  currency: string;
  consegnati_senza_problemi: number;
  orders_timeline: Array<{
    date: string;
    count: number;
  }>;
  percentages: {
    reso: number;
    cambio: number;
    rifiuto: number;
    fulfilled: number;
    fully_paid: number;
    cancelled: number;
    with_refunds: number;
  };
  metadata: {
    start_date: string;
    end_date: string;
    generated_at: string;
    total_orders_fetched: number;
  };
}

/**
 * Recupera statistiche ordini Shopify
 * @param startDate Data inizio YYYY-MM-DD (opzionale, default: 30 giorni fa)
 * @param endDate Data fine YYYY-MM-DD (opzionale, default: oggi)
 */
export async function getOrderStats(
  startDate?: string,
  endDate?: string
): Promise<OrderStats> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  const url = `${LAMBDA_ORDER_STATS_URL}${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Errore nel recupero statistiche: ${response.statusText}`);
  }

  return await response.json();
}
