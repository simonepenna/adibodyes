import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getOrderStats } from '../services/shopifyService';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const Dashboard = () => {
  const [dateRange, setDateRange] = useState<'today' | '7days' | '30days' | '60days' | '90days' | 'custom'>('30days');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);

  const { data: stats, isLoading: loading, error, refetch } = useQuery({
    queryKey: ['dashboard-stats', dateRange, customStartDate, customEndDate],
    queryFn: async () => {
      const today = new Date();
      let startDate: string | undefined;
      let endDate: string | undefined;

      if (dateRange === 'custom') {
        if (!customStartDate || !customEndDate) {
          throw new Error('Seleziona date personalizzate');
        }
        startDate = customStartDate;
        endDate = customEndDate;
      } else {
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
          case '60days':
            const sixtyDaysAgo = new Date(today);
            sixtyDaysAgo.setDate(today.getDate() - 60);
            startDate = sixtyDaysAgo.toISOString().split('T')[0];
            endDate = today.toISOString().split('T')[0];
            break;
          case '90days':
            const ninetyDaysAgo = new Date(today);
            ninetyDaysAgo.setDate(today.getDate() - 90);
            startDate = ninetyDaysAgo.toISOString().split('T')[0];
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
      }

      return await getOrderStats(startDate, endDate);
    },
  });


  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] p-8">
        <div className="loading loading-spinner loading-lg text-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-error">
        <span>❌ {error.message || 'Errore nel caricamento dati'}</span>
        <button className="btn btn-sm" onClick={() => refetch()}>Riprova</button>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  // Prepara dati per grafico timeline (formatta le date per leggibilità)
  const timelineData = stats.orders_timeline.map(item => ({
    date: new Date(item.date).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' }),
    ordini: item.count
  }));

  // Dati per il grafico a torta (usando i valori pre-calcolati dalla Lambda)
  const pieData = [
    { name: 'Consegnati', value: stats.consegnati_senza_problemi, color: '#22c55e' }, // green-500 (più vivido)
    { name: 'Rifiuti', value: stats.orders_by_tag.RIFIUTO, color: '#ef4444' }, // red-500
    { name: 'Cambi', value: stats.orders_by_tag.CAMBIO, color: '#3b82f6' }, // blue-500
    { name: 'Resi', value: stats.orders_by_tag.RESO, color: '#f59e0b' }, // amber-500
  ];

  console.log('pieData:', pieData);

  return (
    <div className="space-y-6">
      {/* Selettore Periodo */}
      <div className="card bg-base-100 shadow-sm border border-base-300 hover:shadow-md transition-shadow">
        <div className="card-body p-4">
          <h2 className="text-sm font-semibold text-base-content/70 mb-3">Periodo Selezionato</h2>
          
          {/* Bottoni periodo */}
          <div className="flex flex-wrap gap-2 mb-3">
            <button
              className={`btn btn-sm ${dateRange === 'today' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setDateRange('today')}
            >
              Oggi
            </button>
            <button
              className={`btn btn-sm ${dateRange === '7days' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setDateRange('7days')}
            >
              7 giorni
            </button>
            <button
              className={`btn btn-sm ${dateRange === '30days' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setDateRange('30days')}
            >
              30 giorni
            </button>
            <button
              className={`btn btn-sm ${dateRange === '60days' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setDateRange('60days')}
            >
              60 giorni
            </button>
            <button
              className={`btn btn-sm ${dateRange === '90days' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setDateRange('90days')}
            >
              90 giorni
            </button>
            <button
              className={`btn btn-sm ${dateRange === 'custom' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setDateRange('custom')}
            >
              Custom
            </button>
          </div>

          {/* Date picker per custom */}
          {dateRange === 'custom' && (
            <div className="flex flex-wrap gap-3 items-end mt-2">
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-xs">Data Inizio</span>
                </label>
                <input
                  type="date"
                  className="input input-sm input-bordered"
                  value={customStartDate}
                  onChange={(e) => setCustomStartDate(e.target.value)}
                />
              </div>
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-xs">Data Fine</span>
                </label>
                <input
                  type="date"
                  className="input input-sm input-bordered"
                  value={customEndDate}
                  onChange={(e) => setCustomEndDate(e.target.value)}
                />
              </div>
              <button 
                className="btn btn-sm btn-primary"
                onClick={() => refetch()}
                disabled={!customStartDate || !customEndDate}
              >
                Applica
              </button>
            </div>
          )}

          <p className="text-xs text-base-content/60 mt-2">
            Dal {new Date(stats.metadata.start_date).toLocaleDateString('it-IT')} al {new Date(stats.metadata.end_date).toLocaleDateString('it-IT')}
          </p>
        </div>
      </div>

      {/* Grid Card Principali */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card Totale Ordini */}
        <div className="card bg-base-100 shadow-sm border border-base-300 hover:shadow-md transition-shadow">
          <div className="card-body">
            <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Totale Ordini</p>
            <p className="text-3xl font-bold text-base-content mt-2">{stats.total_orders.toLocaleString('it-IT')}</p>
          </div>
        </div>

        {/* Card Rifiuti */}
        <div className="card bg-base-100 shadow-sm border border-red-200 hover:shadow-md transition-shadow">
          <div className="card-body">
            <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Rifiuti</p>
            <p className="text-3xl font-bold text-red-600 mt-2">{stats.orders_by_tag.RIFIUTO.toLocaleString('it-IT')}</p>
            <p className="text-xs text-base-content/50">{stats.percentages.rifiuto.toFixed(2)}% su fulfilled</p>
          </div>
        </div>

        {/* Card Cambi */}
        <div className="card bg-base-100 shadow-sm border border-blue-200 hover:shadow-md transition-shadow">
          <div className="card-body">
            <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Cambi</p>
            <p className="text-3xl font-bold text-blue-600 mt-2">{stats.orders_by_tag.CAMBIO.toLocaleString('it-IT')}</p>
            <p className="text-xs text-base-content/50">{stats.percentages.cambio.toFixed(2)}% su fulfilled</p>
          </div>
        </div>

        {/* Card Resi */}
        <div className="card bg-base-100 shadow-sm border border-amber-200 hover:shadow-md transition-shadow">
          <div className="card-body">
            <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Resi</p>
            <p className="text-3xl font-bold text-amber-600 mt-2">{stats.orders_by_tag.RESO.toLocaleString('it-IT')}</p>
            <p className="text-xs text-base-content/50">{stats.percentages.reso.toFixed(2)}% su fulfilled</p>
          </div>
        </div>

      </div>

      {/* Grafici */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* Grafico Andamento Mensile */}
        <div className="card bg-base-100 shadow-sm border border-base-300 hover:shadow-md transition-shadow">
          <div className="card-body">
            <h2 className="card-title text-base">Andamento Ordini</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timelineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="ordini" stroke="#8b5cf6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Grafico a Torta */}
        <div className="card bg-base-100 shadow-sm border border-base-300 hover:shadow-md transition-shadow">
          <div className="card-body">
            <h2 className="card-title text-base">Distribuzione Ordini</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                {/* Layer base con tutti gli spicchi */}
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                  onMouseEnter={(_, index) => setActiveIndex(index)}
                  onMouseLeave={() => setActiveIndex(undefined)}
                >
                  {pieData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.color}
                      fillOpacity={activeIndex === undefined || activeIndex === index ? 1 : 0.6}
                      style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                    />
                  ))}
                </Pie>
                
                {/* Layer hover ingrandito - mostra solo lo spicchio attivo */}
                {activeIndex !== undefined && (
                  <Pie
                    data={[pieData[activeIndex]]}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={108}
                    fill="#8884d8"
                    dataKey="value"
                    startAngle={pieData.slice(0, activeIndex).reduce((sum, item) => sum + (item.value / pieData.reduce((s, i) => s + i.value, 0)) * 360, 0)}
                    endAngle={pieData.slice(0, activeIndex + 1).reduce((sum, item) => sum + (item.value / pieData.reduce((s, i) => s + i.value, 0)) * 360, 0)}
                    isAnimationActive={false}
                  >
                    <Cell fill={pieData[activeIndex].color} style={{ pointerEvents: 'none' }} />
                  </Pie>
                )}
                
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-base-100 shadow-lg border border-base-300 px-3 py-2 rounded">
                          <p className="text-sm font-semibold">{payload[0].value}</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            
            {/* Legenda custom con ordine forzato */}
            <div className="flex flex-wrap justify-center gap-4 mt-2">
              {pieData.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3" 
                    style={{ backgroundColor: item.color }}
                  ></div>
                  <span className="text-sm text-base-content/70">{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>

      {/* Card Pagamenti */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* Ordini Pagati */}
        <div className="card bg-base-100 shadow-sm border border-green-200 hover:shadow-md transition-shadow">
          <div className="card-body">
            <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Ordini Pagati</p>
            <p className="text-3xl font-bold text-green-600 mt-2">{stats.payment_status.fully_paid.toLocaleString('it-IT')}</p>
            <p className="text-xs text-base-content/50">{stats.percentages.fully_paid.toFixed(2)}%</p>
          </div>
        </div>

        {/* Ordini Non Pagati */}
        <div className="card bg-base-100 shadow-sm border border-gray-300 hover:shadow-md transition-shadow">
          <div className="card-body">
            <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Ordini Non Pagati</p>
            <p className="text-3xl font-bold text-gray-600 mt-2">{stats.payment_status.partially_paid.toLocaleString('it-IT')}</p>
            <p className="text-xs text-base-content/50">{((stats.payment_status.partially_paid / stats.total_orders) * 100).toFixed(2)}%</p>
          </div>
        </div>

      </div>


    </div>
  );
};

export default Dashboard;
