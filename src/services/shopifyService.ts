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

/**
 * Marca un ordine Shopify come evaso (fulfilled)
 * @param orderId ID interno Shopify dell'ordine (es: "gid://shopify/Order/7249466851669")
 * @param trackingNumber Numero di tracking GLS (es: "61586276031597")
 * @param zipCode Codice postale destinatario (es: "46410")
 * @param trackingCompany Nome corriere (default: "GLS Spain, S.A.")
 * @param trackingUrl URL tracking personalizzato (opzionale)
 * @param notifyCustomer Se inviare notifica email al cliente (default: true)
 */
export async function fulfillShopifyOrder(
  orderId: string,
  trackingNumber: string,
  zipCode: string,
  trackingCompany: string = 'GLS Spain, S.A.',
  trackingUrl?: string,
  notifyCustomer: boolean = true
): Promise<{ success: boolean; error?: string }> {
  try {
    // Costruisci URL tracking se non fornito (include zip code)
    const finalTrackingUrl = trackingUrl || `https://mygls.gls-spain.es/e/${trackingNumber}/${zipCode}`;

    // GraphQL mutation per creare fulfillment
    const mutation = `
      mutation fulfillmentCreateV2($fulfillment: FulfillmentV2Input!) {
        fulfillmentCreateV2(fulfillment: $fulfillment) {
          fulfillment {
            id
            status
            trackingInfo {
              number
              company
              url
            }
          }
          userErrors {
            field
            message
          }
        }
      }
    `;

    const variables = {
      fulfillment: {
        lineItemsByFulfillmentOrder: [
          {
            fulfillmentOrderId: orderId
          }
        ],
        trackingInfo: {
          number: trackingNumber,
          company: trackingCompany,
          url: finalTrackingUrl
        },
        notifyCustomer: notifyCustomer
      }
    };

    // ==================== PRODUZIONE SHOPIFY ATTIVA ====================
    console.log('\n🚀 PRODUZIONE - Chiamata reale a Shopify');
    console.log('📦 Fulfillment per Order ID:', orderId);
    console.log('🚚 Tracking Number:', trackingNumber);
    console.log('🏢 Corriere:', trackingCompany);
    console.log('🔗 URL Tracking:', finalTrackingUrl);
    console.log('📍 ZIP Code:', zipCode);
    console.log('📧 Notifica Cliente:', notifyCustomer ? '✅ Sì' : '❌ No');
    console.log('==================================================================\n');

    const SHOPIFY_GRAPHQL_URL = 'https://db806d-07.myshopify.com/admin/api/2024-04/graphql.json';
    const SHOPIFY_ACCESS_TOKEN = import.meta.env.VITE_SHOPIFY_ACCESS_TOKEN;

    if (!SHOPIFY_ACCESS_TOKEN) {
      throw new Error('VITE_SHOPIFY_ACCESS_TOKEN non configurato');
    }

    const response = await fetch(SHOPIFY_GRAPHQL_URL, {
      method: 'POST',
      headers: {
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query: mutation, variables })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    console.log('📨 Shopify Fulfillment Response:', data);

    if (data.errors) {
      return {
        success: false,
        error: data.errors[0]?.message || 'GraphQL error'
      };
    }

    const userErrors = data.data?.fulfillmentCreateV2?.userErrors;
    if (userErrors && userErrors.length > 0) {
      return {
        success: false,
        error: userErrors[0]?.message || 'User error'
      };
    }

    return { success: true };
  } catch (error) {
    console.error('❌ Errore fulfillment Shopify:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}
