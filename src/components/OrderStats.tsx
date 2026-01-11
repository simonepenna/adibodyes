import { useState, useEffect } from 'react';
import { getOrderStats } from '../services/shopifyService';
import type { OrderStats as OrderStatsType } from '../services/shopifyService';

const OrderStats = () => {
  const [stats, setStats] = useState<OrderStatsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<'30days' | '7days' | 'today'>('30days');

  useEffect(() => {
    loadStats();
  }, [dateRange]);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const today = new Date();
      let startDate: string | undefined;
      let endDate: string | undefined;

      switch (dateRange) {
        case 'today':
          startDate = endDate = today.toISOString().split('T')[0];
          break;
        case '7days':
          const sevenDaysAgo = new Date(today);
          sevenDaysAgo.setDate(today.getDate() - 7);
          startDate = sevenDaysAgo.toISOString().split('T')[0];
          endDate = today.toISOString().split('T')[0];
          break;
        case '30days':
        default:
          const thirtyDaysAgo = new Date(today);
          thirtyDaysAgo.setDate(today.getDate() - 30);
          startDate = thirtyDaysAgo.toISOString().split('T')[0];
          endDate = today.toISOString().split('T')[0];
          break;
      }

      const data = await getOrderStats(startDate, endDate);
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore nel caricamento dati');
      console.error('Errore caricamento statistiche:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency: currency || 'EUR',
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="loading loading-spinner loading-lg text-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-error">
        <span>❌ {error}</span>
        <button className="btn btn-sm" onClick={loadStats}>Riprova</button>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      {/* Header con filtri */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-base-content">📊 Statistiche Ordini Shopify</h2>
        <div className="btn-group">
          <button 
            className={`btn btn-sm ${dateRange === 'today' ? 'btn-active' : ''}`}
            onClick={() => setDateRange('today')}
          >
            Oggi
          </button>
          <button 
            className={`btn btn-sm ${dateRange === '7days' ? 'btn-active' : ''}`}
            onClick={() => setDateRange('7days')}
          >
            7 giorni
          </button>
          <button 
            className={`btn btn-sm ${dateRange === '30days' ? 'btn-active' : ''}`}
            onClick={() => setDateRange('30days')}
          >
            30 giorni
          </button>
        </div>
      </div>

      {/* Cards principali */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Totale Ordini */}
        <div className="card bg-gradient-to-br from-primary to-primary-focus text-primary-content shadow-xl">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-80">Totale Ordini</p>
                <p className="text-3xl font-bold">{stats.total_orders}</p>
              </div>
              <div className="text-4xl opacity-80">📦</div>
            </div>
            <div className="text-xs opacity-70 mt-2">
              Periodo: {new Date(stats.metadata.start_date).toLocaleDateString('it-IT')} - {new Date(stats.metadata.end_date).toLocaleDateString('it-IT')}
            </div>
          </div>
        </div>

        {/* Revenue */}
        <div className="card bg-gradient-to-br from-success to-success-focus text-success-content shadow-xl">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-80">Revenue Totale</p>
                <p className="text-3xl font-bold">{formatCurrency(stats.total_revenue, stats.currency)}</p>
              </div>
              <div className="text-4xl opacity-80">💰</div>
            </div>
            <div className="text-xs opacity-70 mt-2">
              Media: {formatCurrency(stats.total_revenue / stats.total_orders, stats.currency)}
            </div>
          </div>
        </div>

        {/* Evasi */}
        <div className="card bg-gradient-to-br from-info to-info-focus text-info-content shadow-xl">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-80">Ordini Evasi</p>
                <p className="text-3xl font-bold">{stats.percentages.fulfilled}%</p>
              </div>
              <div className="text-4xl opacity-80">✅</div>
            </div>
            <div className="text-xs opacity-70 mt-2">
              {stats.fulfillment_status.FULFILLED} di {stats.total_orders}
            </div>
          </div>
        </div>

        {/* Pagati */}
        <div className="card bg-gradient-to-br from-secondary to-secondary-focus text-secondary-content shadow-xl">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-80">Completamente Pagati</p>
                <p className="text-3xl font-bold">{stats.percentages.fully_paid}%</p>
              </div>
              <div className="text-4xl opacity-80">💳</div>
            </div>
            <div className="text-xs opacity-70 mt-2">
              {stats.payment_status.fully_paid} di {stats.total_orders}
            </div>
          </div>
        </div>
      </div>

      {/* Cards problematiche */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Resi */}
        <div className="card bg-base-100 shadow-xl border-l-4 border-warning">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-base-content/70 text-sm">RESI</p>
                <div className="flex items-baseline gap-2">
                  <p className="text-2xl font-bold text-warning">{stats.orders_by_tag.RESO}</p>
                  <span className="text-sm text-base-content/60">({stats.percentages.reso}%)</span>
                </div>
              </div>
              <div className="text-3xl">🔄</div>
            </div>
            <div className="w-full bg-base-300 rounded-full h-2 mt-2">
              <div 
                className="bg-warning h-2 rounded-full" 
                style={{ width: `${stats.percentages.reso}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Cambi */}
        <div className="card bg-base-100 shadow-xl border-l-4 border-info">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-base-content/70 text-sm">CAMBI</p>
                <div className="flex items-baseline gap-2">
                  <p className="text-2xl font-bold text-info">{stats.orders_by_tag.CAMBIO}</p>
                  <span className="text-sm text-base-content/60">({stats.percentages.cambio}%)</span>
                </div>
              </div>
              <div className="text-3xl">🔁</div>
            </div>
            <div className="w-full bg-base-300 rounded-full h-2 mt-2">
              <div 
                className="bg-info h-2 rounded-full" 
                style={{ width: `${stats.percentages.cambio}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Rifiuti */}
        <div className="card bg-base-100 shadow-xl border-l-4 border-error">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-base-content/70 text-sm">RIFIUTI</p>
                <div className="flex items-baseline gap-2">
                  <p className="text-2xl font-bold text-error">{stats.orders_by_tag.RIFIUTO}</p>
                  <span className="text-sm text-base-content/60">({stats.percentages.rifiuto}%)</span>
                </div>
              </div>
              <div className="text-3xl">❌</div>
            </div>
            <div className="w-full bg-base-300 rounded-full h-2 mt-2">
              <div 
                className="bg-error h-2 rounded-full" 
                style={{ width: `${stats.percentages.rifiuto}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* Dettagli aggiuntivi */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Fulfillment Status */}
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h3 className="card-title text-lg">📋 Stato Evasione</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm">Evasi</span>
                <span className="badge badge-success">{stats.fulfillment_status.FULFILLED}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Non Evasi</span>
                <span className="badge badge-warning">{stats.fulfillment_status.UNFULFILLED}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Parzialmente Evasi</span>
                <span className="badge badge-info">{stats.fulfillment_status.PARTIALLY_FULFILLED}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Financial Status */}
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h3 className="card-title text-lg">💳 Stato Finanziario</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm">Pagati</span>
                <span className="badge badge-success">{stats.financial_status.PAID}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">In Attesa</span>
                <span className="badge badge-warning">{stats.financial_status.PENDING}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Rimborsati</span>
                <span className="badge badge-error">{stats.financial_status.REFUNDED}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Cancellati</span>
                <span className="badge badge-ghost">{stats.cancelled_orders}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer con metadata */}
      <div className="text-xs text-base-content/60 text-center">
        Ultimo aggiornamento: {new Date(stats.metadata.generated_at).toLocaleString('it-IT')}
      </div>
    </div>
  );
};

export default OrderStats;
