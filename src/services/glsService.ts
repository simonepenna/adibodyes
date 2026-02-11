/**
 * Service for GLS shipping API integration
 */

export interface GLSOrderData {
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
    title: string;
  }>;
  totalPrice: string;
  financialStatus: string;
  email?: string;
  // Aggiunto per struttura completa GLS
  orderDate?: string;
  customObservations?: string; // Observations personalizzate dall'utente
}

export interface GLSShipmentResponse {
  success: boolean;
  trackingNumber?: string;
  labelUrl?: string;
  error?: string;
}

const GLS_UID = 'cbfbcd8f-ef6c-4986-9643-0b964e1efa20'; // Production UID

export const createGLSShipment = async (orderData: GLSOrderData): Promise<GLSShipmentResponse> => {
  try {
    // Determina il reembolso basato sullo stato del pagamento
    const isPaid = orderData.financialStatus?.toLowerCase() === 'paid';
    const reembolso = isPaid ? '0' : orderData.totalPrice;

    console.log('💰 Financial Status ricevuto:', orderData.financialStatus, '- Tipo:', typeof orderData.financialStatus);
    console.log('💰 È pagato?', isPaid, '- Reembolso calcolato:', reembolso);

    // Usa le observations custom se fornite, altrimenti genera dalla lista SKU
    const observaciones = orderData.customObservations || 
      orderData.items
        .filter(item => item.sku) // Solo item con SKU valido
        .map(item => `${item.sku}x${item.quantity}`)
        .join(', ');

    console.log('📝 Observations finali:', observaciones);

    // Estrai il numero dell'ordine senza "#ES" per l'albaran
    const albaran = orderData.orderName.replace('#ES', '');

    console.log('📄 Order Name:', orderData.orderName, '- Albaran:', albaran);

    // Build SOAP XML request for GrabaServicios - VERSIONE COMPLETA STRUTTURATA
    const soapXml = `<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <GrabaServicios xmlns="http://www.asmred.com/">
      <docIn>
        <Servicios uidcliente="${GLS_UID}" xmlns="http://www.asmred.com/">
          <Envio>
            <Fecha>${new Date().toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })}</Fecha>
            <Servicio>96</Servicio>
            <Horario>18</Horario>
            <Bultos>1</Bultos>
            <Peso>1</Peso>
            <Portes>P</Portes>
            <Remite>
              <Nombre>AdiBody ES</Nombre>
              <Direccion>Calle Principal 123</Direccion>
              <Poblacion>Madrid</Poblacion>
              <Pais>34</Pais>
              <CP>28001</CP>
            </Remite>
            <Destinatario>
              <Nombre>${orderData.customerName}</Nombre>
              <Direccion>${orderData.shippingAddress.address1 || ''} ${orderData.shippingAddress.address2 || ''}</Direccion>
              <Poblacion>${orderData.shippingAddress.city || ''}</Poblacion>
              <Pais>34</Pais>
              <CP>${orderData.shippingAddress.zip || ''}</CP>
              <Telefono>${orderData.shippingAddress.phone || ''}</Telefono>
              <Email>${orderData.email || ''}</Email>
            </Destinatario>
            <Referencias>
              <Referencia tipo="C">${orderData.orderName}</Referencia>
            </Referencias>
            <Albaran>${albaran}</Albaran>
            <Observaciones>${observaciones}</Observaciones>
            <Importe>${orderData.totalPrice}</Importe>
            <Reembolso>${reembolso}</Reembolso>
            <Retorno>0</Retorno>
          </Envio>
        </Servicios>
      </docIn>
    </GrabaServicios>
  </soap12:Body>
</soap12:Envelope>`;

    console.log('🚚 GLS SOAP Request XML:', soapXml);
    console.log('📦 Order Data:', orderData);
    console.log('📧 Email estratta:', orderData.email);

    // ==================== MOCK MODE - TEST LOCALE ====================
    console.log('\n🧪 MOCK MODE ATTIVO - Nessuna chiamata reale a GLS');
    console.log('📦 Simulazione creazione spedizione per:', orderData.orderName);
    console.log('👤 Cliente:', orderData.customerName);
    console.log('📍 Indirizzo:', `${orderData.shippingAddress.address1}, ${orderData.shippingAddress.city}, ${orderData.shippingAddress.zip}`);
    console.log('💰 Importo:', orderData.totalPrice, '- Stato:', orderData.financialStatus);
    console.log('💵 Reembolso calcolato:', reembolso);
    
    const mockTrackingNumber = '615862760' + Math.floor(Math.random() * 100000).toString().padStart(5, '0');
    console.log('✅ Tracking Number SIMULATO:', mockTrackingNumber);
    console.log('==================================================================\n');
    
    return {
      success: true,
      trackingNumber: mockTrackingNumber,
      labelUrl: 'https://example.com/label.pdf'
    };

    /* COMMENTATO TEMPORANEAMENTE
    const response = await fetch(GLS_SOAP_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'text/xml; charset=UTF-8',
        'SOAPAction': 'http://www.asmred.com/GrabaServicios'
      },
      body: soapXml
    });

    console.log('📡 Fetch request details:', {
      url: GLS_SOAP_ENDPOINT,
      method: 'POST',
      headers: {
        'Content-Type': 'text/xml; charset=UTF-8',
        'SOAPAction': 'http://www.asmred.com/GrabaServicios'
      },
      body: soapXml
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const responseText = await response.text();
    console.log('📨 GLS API Raw Response:', responseText);

    // Parse XML response
    // For now, return a mock success response
    // TODO: Parse actual XML response
    return {
      success: true,
      trackingNumber: 'GLS' + Date.now(),
      labelUrl: 'https://example.com/label.pdf'
    };
    */

  } catch (error) {
    console.error('Error creating GLS shipment:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
};