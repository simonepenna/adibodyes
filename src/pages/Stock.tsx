import { useQuery } from '@tanstack/react-query';
import { fetchStockData } from '../services/stockService';

const Stock = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['stock'],
    queryFn: fetchStockData,
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
        <span>Errore nel caricamento dei dati</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="alert alert-warning">
        <span>Nessun dato disponibile</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-sm font-bold">Totale Prodotti</p>
                <p className="text-2xl font-bold text-primary">{data.summary.totale_sku}</p>
              </div>
              <div className="text-3xl">📦</div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-sm font-bold">Pezzi in Magazzino</p>
                <p className="text-2xl font-bold text-secondary">{data.summary.totale_magazzino_attuale?.toLocaleString() || 0}</p>
              </div>
              <div className="text-3xl">📦</div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-sm font-bold">Pezzi in Arrivo</p>
                <p className="text-2xl font-bold text-info">{data.summary.totale_in_arrivo?.toLocaleString() || 0}</p>
              </div>
              <div className="text-3xl">🚚</div>
            </div>
          </div>
        </div>
      </div>

      {/* Stock Tables - SLIP e PER affiancati */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tabella SLIP */}
        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <h2 className="card-title font-bold">SLIP</h2>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Taglia</th>
                    <th>Aut.</th>
                    <th>Magazzino</th>
                    <th>In Arrivo</th>
                    <th>Stato</th>
                  </tr>
                </thead>
                <tbody>
                  {data.stock.filter(item => item.modelo.startsWith('SLIP')).map((item) => (
                    <tr key={item.sku}>
                      <td className="font-mono">{item.sku}</td>
                      <td className="font-medium">{item.talla}</td>
                      <td>{item.giorni_autonomia >= 999 ? '∞' : `${item.giorni_autonomia}gg`}</td>
                      <td>{item.magazzino_attuale}</td>
                      <td>{item.in_arrivo}</td>
                      <td>
                        <span className={`badge ${
                          item.urgenza === 'OK' ? 'badge-success' :
                          item.urgenza === 'ORDINARE' ? 'badge-warning' :
                          'badge-error'
                        }`}>
                          {item.urgenza}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Tabella PER */}
        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <h2 className="card-title font-bold">PERIZOMA</h2>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Taglia</th>
                    <th>Aut.</th>
                    <th>Magazzino</th>
                    <th>In Arrivo</th>
                    <th>Stato</th>
                  </tr>
                </thead>
                <tbody>
                  {data.stock.filter(item => item.modelo.startsWith('PER')).map((item) => (
                    <tr key={item.sku}>
                      <td className="font-mono">{item.sku}</td>
                      <td className="font-medium">{item.talla}</td>
                      <td>{item.giorni_autonomia >= 999 ? '∞' : `${item.giorni_autonomia}gg`}</td>
                      <td>{item.magazzino_attuale}</td>
                      <td>{item.in_arrivo}</td>
                      <td>
                        <span className={`badge ${
                          item.urgenza === 'OK' ? 'badge-success' :
                          item.urgenza === 'ORDINARE' ? 'badge-warning' :
                          'badge-error'
                        }`}>
                          {item.urgenza}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Ordine Fornitore Stats */}
      <div className="divider"></div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-sm font-bold">SKU OK</p>
                <p className="text-2xl font-bold text-success">{data.summary.totale_sku - data.summary.sku_critici - data.summary.sku_da_ordinare}</p>
              </div>
              <div className="text-3xl">✅</div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-sm font-bold">SKU Critici</p>
                <p className="text-2xl font-bold text-error">{data.summary.sku_critici}</p>
              </div>
              <div className="text-3xl">🚨</div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-sm font-bold">SKU da Ordinare</p>
                <p className="text-2xl font-bold text-warning">{data.summary.sku_da_ordinare}</p>
              </div>
              <div className="text-3xl">📋</div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base-content/70 text-sm font-bold">Totale Pezzi</p>
                <p className="text-2xl font-bold text-primary">{data.summary.totale_pezzi_ordine.toLocaleString()}</p>
              </div>
              <div className="text-3xl">📦</div>
            </div>
          </div>
        </div>
      </div>

      {/* Dettaglio Ordine Fornitore */}
      <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
        <div className="card-body">
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Prodotto</th>
                  <th>Taglia</th>
                  <th>Autonomia (gg)</th>
                  <th>Quantità</th>
                  <th>Urgenza</th>
                </tr>
              </thead>
              <tbody>
                {data.ordine_fornitore.map((item) => (
                  <tr key={item.sku}>
                    <td className="font-mono text-sm">{item.sku}</td>
                    <td>{item.modelo}</td>
                    <td className="font-medium">{item.talla}</td>
                    <td>{item.giorni_autonomia} gg</td>
                    <td className="font-bold">{item.quantita}</td>
                    <td>
                      <span className={`badge ${
                        item.urgenza === 'CRITICO' ? 'badge-error' : 'badge-warning'
                      }`}>
                        {item.urgenza}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="font-bold">
                  <td colSpan={3}>TOTALE</td>
                  <td>{data.summary.totale_pezzi_ordine.toLocaleString()}</td>
                  <td colSpan={2}></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Stock;