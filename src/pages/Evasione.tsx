import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchFulfillmentData } from '../services/fulfillmentService';
import type { FulfillmentOrder } from '../services/fulfillmentService';

const Evasione = () => {
  const [days, setDays] = useState(4);

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
                <p className="text-3xl font-bold text-primary">{data.summary.total}</p>
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
                <p className="text-3xl font-bold text-success">{data.summary.green}</p>
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
                <p className="text-3xl font-bold text-warning">{data.summary.yellow}</p>
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
                <p className="text-3xl font-bold text-error">{data.summary.red}</p>
              </div>
              <div className="text-4xl">❌</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabella Unica con tutti gli ordini */}
      <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
        <div className="card-body">
          <div className="overflow-x-auto">
            <table className="table">
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
                </tr>
              </thead>
              <tbody>
                {allOrders.map((order) => (
                  <tr key={order.id} className="hover">
                    <td className="font-mono font-bold text-base">{order.name}</td>
                    <td className="text-base">{new Date(order.created_at).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' })}</td>
                    <td className="text-base">{order.customer_name}</td>
                    <td className="text-sm max-w-xs truncate">{formatAddress(order)}</td>
                    <td className="text-base">€{parseFloat(order.total_price).toFixed(2)}</td>
                    <td>
                      <span className="badge badge-sm badge-ghost">
                        {order.financial_status}
                      </span>
                    </td>
                    <td className="text-sm max-w-xs truncate">{formatItems(order)}</td>
                    <td>{getStatusBadge(order)}</td>
                    <td className="text-sm">
                      {order.warnings.length > 0 ? order.warnings.join('; ') : '-'}
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