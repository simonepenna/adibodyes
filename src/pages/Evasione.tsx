import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchFulfillmentData } from '../services/fulfillmentService';
import type { FulfillmentOrder } from '../services/fulfillmentService';

const Evasione = () => {
  const [days, setDays] = useState(4);

  // Aggiorna il titolo della pagina
  useEffect(() => {
    document.title = 'AdiBody ES - Evasione';
  }, []);

  const { data, isLoading, error } = useQuery({
    queryKey: ['fulfillment', days],
    queryFn: () => fetchFulfillmentData(days),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] p-8">
        <div className="loading loading-spinner loading-lg text-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-error">
        <span>Errore: {error.message}</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="alert alert-info">
        <span>Nessun dato disponibile</span>
      </div>
    );
  }

  // Combina tutti gli ordini in un array unico e ordina per data (dal più vecchio al più recente)
  const allOrders = [
    ...data.orders.green,
    ...data.orders.yellow,
    ...data.orders.red
  ].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

  const getStatusBadge = (order: FulfillmentOrder) => {
    // Prima controlla se ci sono problemi di indirizzo
    if (hasAddressIssue(order)) {
      return <span className="badge badge-sm badge-warning">WARNING</span>;
    }

    // Altrimenti usa la categoria del backend
    if (order.category === 'GREEN') {
      return <span className="badge badge-sm badge-success">OK</span>;
    } else if (order.category === 'YELLOW') {
      return <span className="badge badge-sm badge-warning">WARNING</span>;
    } else {
      return <span className="badge badge-sm badge-error whitespace-nowrap">NO STOCK</span>;
    }
  };

  const formatAddress = (order: FulfillmentOrder) => {
    const addr = order.shipping_address;
    if (!addr) return '-';
    const parts = [
      addr.address1,
      addr.city,
      addr.zip
    ].filter(Boolean);
    return parts.join(', ') || '-';
  };

  const formatItems = (order: FulfillmentOrder) => {
    return order.items
      .filter(item => item.sku) // Escludi item senza SKU (es. Pago Contra Reembolso)
      .map(item => `${item.quantity}x ${item.sku}`)
      .join(', ');
  };

  function hasAddressIssue(order: FulfillmentOrder) {
    const a = order.shipping_address;
    if (!a) return true;

    // Controlla sia address1 che address2 per il numero civico
    const address1 = a.address1 || '';
    const address2 = a.address2 || '';
    const fullAddress = (address1 + ' ' + address2).toLowerCase().trim();

    // Se non c'è nessun indirizzo, è un problema
    if (!fullAddress) return true;

    // Se contiene "s/n" (sin número), è considerato valido
    if (fullAddress.includes('s/n') || fullAddress.includes('sin número')) {
      return false;
    }

    // Controlla se c'è almeno un numero nell'indirizzo completo
    const hasStreetNumber = /\d/.test(fullAddress);

    return !hasStreetNumber;
  }

  // Ricalcola i totali considerando anche i problemi di indirizzo
  const adjustedSummary = {
    total: data.summary.total,
    green: data.orders.green.filter(order => !hasAddressIssue(order)).length,
    yellow: data.summary.yellow + data.orders.green.filter(order => hasAddressIssue(order)).length,
    red: data.summary.red
  };

  return (
    <div className="space-y-6">
      <div className="mb-6">
        
        <div className="flex items-center gap-3 mb-6">
          <label className="text-base font-medium">Mostra ordini degli ultimi:</label>
          <select 
            className="select select-bordered select-sm"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={1}>1 giorno</option>
            <option value={2}>2 giorni</option>
            <option value={3}>3 giorni</option>
            <option value={4}>4 giorni</option>
            <option value={7}>7 giorni</option>
            <option value={14}>14 giorni</option>
            <option value={30}>30 giorni</option>
          </select>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-base font-bold">Totale Ordini</p>
                <p className="text-3xl font-bold text-primary">{adjustedSummary.total}</p>
              </div>
              <div className="text-4xl">📋</div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-base font-bold">Evadibili OK</p>
                <p className="text-3xl font-bold text-success">{adjustedSummary.green}</p>
              </div>
              <div className="text-4xl">✅</div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-base font-bold">Con Warning</p>
                <p className="text-3xl font-bold text-warning">{adjustedSummary.yellow}</p>
              </div>
              <div className="text-4xl">⚠️</div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-base font-bold">No Stock</p>
                <p className="text-3xl font-bold text-error">{adjustedSummary.red}</p>
              </div>
              <div className="text-4xl">❌</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabella Unica con tutti gli ordini */}
      <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
        <div className="card-body">
          <h2 className="card-title font-bold">Ordini da Evadere</h2>
          <div className="overflow-x-auto">
            <table className="table table-zebra">
              <thead>
                <tr>
                  <th className="text-base">Ordine</th>
                  <th className="text-base">Data</th>
                  <th className="text-base">Cliente</th>
                  <th className="text-base">Indirizzo</th>
                  <th className="text-base">Totale</th>
                  <th className="text-base">Stato Pag.</th>
                  <th className="text-base">Taglie Ordine</th>
                  <th className="text-base">Evadibile</th>
                  <th className="text-base">Dettagli</th>
                  <th className="text-base">WhatsApp</th>
                </tr>
              </thead>
              <tbody>
                {allOrders.map((order) => (
                  <tr key={order.id} className="hover">
                    <td className="font-mono font-medium">{order.name}</td>
                    <td className="text-sm">{new Date(order.created_at).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' })}</td>
                    <td className="font-medium">{order.customer_name}</td>
                    <td className="text-sm max-w-xs truncate">{formatAddress(order)}</td>
                    <td className="text-sm">€{parseFloat(order.total_price).toFixed(2)}</td>
                    <td>
                      <span className="badge badge-sm badge-ghost">
                        {order.financial_status}
                      </span>
                    </td>
                    <td className="text-sm max-w-xs truncate">{formatItems(order)}</td>
                    <td>{getStatusBadge(order)}</td>
                    <td className="text-sm">
                      {(() => {
                        const warnings = [...order.warnings];
                        if (hasAddressIssue(order)) {
                          warnings.push('Indirizzo incompleto o problematico');
                        }
                        return warnings.length > 0 ? warnings.join('; ') : '-';
                      })()}
                    </td>
                    <td>
                      {order.shipping_address?.phone ? (() => {
                        const firstName = order.customer_name.split(' ')[0];
                        let phone = order.shipping_address.phone.replace(/[^\d+]/g, '');
                        if (!phone.startsWith('+')) {
                          phone = '+34' + phone;
                        }
                        const sizes = [...new Set(order.items.map(item => item.talla).filter(talla => talla && talla !== 'N/A'))];
                        const sizesText = sizes.length > 0 
                          ? sizes.map(size => `una ${size}`).join(', ').replace(/, ([^,]*)$/, ' y $1')
                          : 'ninguna talla disponible';
                        
                        // Determina il messaggio in base al tipo di warning
                        let message = '';
                        if (hasAddressIssue(order)) {
                          // Messaggio per indirizzo incompleto
                          message = `Buenos días, ${firstName}.\n` +
                                   `Somos el equipo de AdiBody.\n\n` +
                                   `Antes de enviar tu pedido, queremos confirmar la dirección completa, ya que nos aparece incompleta.\n` +
                                   `¿Podrías indicarnos calle, número, código postal y ciudad?\n\n` +
                                   `¡Gracias!\n` +
                                   `AdiBody`;
                        } else {
                          // Messaggio per taglie (warning originale)
                          message = `Buenos días, ${firstName}.\n` +
                                   `Somos el equipo de AdiBody.\n` +
                                   `¿Podrías confirmarnos, por favor, las tallas del pedido?\n` +
                                   `Vemos ${sizesText}.\n\n` +
                                   `¡Gracias!\n` +
                                   `AdiBody`;
                        }
                        
                        return (
                          <a
                            href={`https://web.whatsapp.com/send?phone=${encodeURIComponent(phone)}&text=${encodeURIComponent(message)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-success btn-sm btn-circle"
                            title="Invia messaggio WhatsApp"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                              <path d="M13.601 2.326A7.854 7.854 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.933 7.933 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.898 7.898 0 0 0 13.6 2.326zM7.994 14.521a6.573 6.573 0 0 1-3.356-.92l-.24-.144-2.494.654.666-2.433-.156-.251a6.56 6.56 0 0 1-1.007-3.505c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.557 6.557 0 0 1 1.928 4.66c-.004 3.639-2.961 6.592-6.592 6.592zm3.615-4.934c-.197-.099-1.17-.578-1.353-.646-.182-.065-.315-.099-.445.099-.133.197-.513.646-.627.775-.114.133-.232.148-.43.05-.197-.1-.836-.308-1.592-.985-.59-.525-.985-1.175-1.103-1.372-.114-.198-.011-.304.088-.403.087-.088.197-.232.296-.346.1-.114.133-.198.198-.33.065-.134.034-.248-.015-.347-.05-.099-.445-1.076-.612-1.47-.16-.389-.323-.335-.445-.34-.114-.007-.247-.007-.38-.007a.729.729 0 0 0-.529.247c-.182.198-.691.677-.691 1.654 0 .977.71 1.916.81 2.049.098.133 1.394 2.132 3.383 2.992.47.205.84.326 1.129.418.475.152.904.129 1.246.08.38-.058 1.171-.48 1.338-.943.164-.464.164-.86.114-.943-.049-.084-.182-.133-.38-.232z"/>
                            </svg>
                          </a>
                        );
                      })() : (
                        <span className="text-xs text-error" title="Telefono non disponibile">❌</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Evasione;