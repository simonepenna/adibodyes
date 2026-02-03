import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchRefundOrders } from '../services/refundOrdersService';
import type { RefundOrder } from '../services/refundOrdersService';

const Rimborsi = () => {
  // Aggiorna il titolo della pagina
  useEffect(() => {
    document.title = 'AdiBody ES - Ordini da Rimborsare';
  }, []);

  const { data, isLoading, error } = useQuery({
    queryKey: ['refund-orders'],
    queryFn: () => fetchRefundOrders(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] p-8">
        <div className="loading loading-spinner loading-lg text-primary"></div>
        <span className="ml-4"></span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-error">
        <span>Errore nel caricamento degli ordini da rimborsare: {error.message}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="card-body">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base-content/70 text-sm font-bold">Totale Ordini</p>
                  <p className="text-2xl font-bold text-primary">{data.metadata.total_orders}</p>
                </div>
                <div className="text-3xl">💰</div>
              </div>
            </div>
          </div>

          <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="card-body">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base-content/70 text-sm font-bold">Periodo</p>
                  <p className="text-lg font-bold text-secondary">Tutti gli ordini</p>
                </div>
                <div className="text-3xl">📅</div>
              </div>
            </div>
          </div>

          <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="card-body">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base-content/70 text-sm font-bold">Stato</p>
                  <p className="text-lg font-bold text-accent">DA RIMBORSARE</p>
                </div>
                <div className="text-3xl">🔄</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      {data && data.orders.length > 0 && (
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h2 className="card-title font-bold">Ordini da Rimborsare</h2>
            <div className="overflow-x-auto">
              <table className="table table-zebra">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Ordine</th>
                    <th>Destinatario</th>
                    <th>Stato</th>
                    <th>Totale</th>
                    <th>Stato Pagamento</th>
                    <th>Note</th>
                    <th className="text-center">WhatsApp</th>
                  </tr>
                </thead>
                <tbody>
                  {data.orders.map((order: RefundOrder, index: number) => (
                    <tr key={order.id || index}>
                      <td className="font-mono text-sm">
                        {new Date(order.created_at).toLocaleDateString('it-IT', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric'
                        })}
                      </td>
                      <td className="font-mono font-medium">{order.name.replace('#', '')}</td>
                      <td className="font-medium">
                        {order.shipping_address?.name || order.customer?.displayName || 'N/A'}
                      </td>
                      <td>
                        <span className="badge badge-warning badge-sm whitespace-nowrap">
                          DA RIMBORSARE
                        </span>
                      </td>
                      <td className="font-mono font-medium">
                        {order.total_price} {order.currency}
                      </td>
                      <td>
                        <span className="badge badge-ghost badge-sm whitespace-nowrap">
                          {order.financial_status || 'N/A'}
                        </span>
                      </td>
                      <td className="text-sm max-w-xs">
                        <div className="truncate" title={order.note || 'Nessuna nota'}>
                          {order.note || 'Nessuna nota'}
                        </div>
                      </td>
                      <td className="text-center">
                        {getPhoneNumber(order) ? (
                          <a
                            href={generateWhatsAppLink(order)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-success btn-sm btn-circle"
                            title="Invia messaggio WhatsApp"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                              <path d="M13.601 2.326A7.854 7.854 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.933 7.933 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.898 7.898 0 0 0 13.6 2.326zM7.994 14.521a6.573 6.573 0 0 1-3.356-.92l-.24-.144-2.494.654.666-2.433-.156-.251a6.56 6.56 0 0 1-1.007-3.505c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.557 6.557 0 0 1 1.928 4.66c-.004 3.639-2.961 6.592-6.592 6.592zm3.615-4.934c-.197-.099-1.17-.578-1.353-.646-.182-.065-.315-.099-.445.099-.133.197-.513.646-.627.775-.114.133-.232.148-.43.05-.197-.1-.836-.308-1.592-.985-.59-.525-.985-1.175-1.103-1.372-.114-.198-.011-.304.088-.403.087-.088.197-.232.296-.346.1-.114.133-.198.198-.33.065-.134.034-.248-.015-.347-.05-.099-.445-1.076-.612-1.47-.16-.389-.323-.335-.445-.34-.114-.007-.247-.007-.38-.007a.729.729 0 0 0-.529.247c-.182.198-.691.677-.691 1.654 0 .977.71 1.916.81 2.049.098.133 1.394 2.132 3.383 2.992.47.205.84.326 1.129.418.475.152.904.129 1.246.08.38-.058 1.171-.48 1.338-.943.164-.464.164-.86.114-.943-.049-.084-.182-.133-.38-.232z"/>
                            </svg>
                          </a>
                        ) : (
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
      )}

      {/* Empty State */}
      {data && data.orders.length === 0 && (
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body text-center py-12">
            <div className="text-6xl mb-4">✅</div>
            <h3 className="text-xl font-bold mb-2">Nessun ordine da rimborsare</h3>
            <p className="text-base-content/70">
              Non ci sono ordini con tag RESO e DA RIMBORSARE nel periodo selezionato.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

// Helper functions
function getPhoneNumber(order: RefundOrder): string | null {
  return order.shipping_address?.phone || order.customer?.phone || null;
}

function generateWhatsAppLink(order: RefundOrder): string {
  const phone = getPhoneNumber(order);
  if (!phone) return '#';

  const customerName = order.shipping_address?.name ||
                      order.customer?.displayName ||
                      'Cliente';

  const message = encodeURIComponent(
    `¡Hola ${customerName.split(' ')[0]}! 😊\n\n` +
    `Hemos recibido tu devolución correctamente.\n` +
    `Para poder emitir el reembolso, necesitamos que nos indiques por favor:\n\n` +
    `• IBAN\n` +
    `• Nombre y apellido del titular de la cuenta\n\n` +
    `Quedamos atentos, gracias 🙏\n\n` +
    `Saludos,\n` +
    `AdiBody`
  );

  return `https://web.whatsapp.com/send?phone=${encodeURIComponent(phone.replace(/\D/g, ''))}&text=${message}`;
}

export default Rimborsi;