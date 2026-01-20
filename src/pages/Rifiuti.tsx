import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import rifiutiService from '../services/rifiutiService';

const Rifiuti = () => {
  const [daysBack, setDaysBack] = useState<number>(4);
  const [taggingAll, setTaggingAll] = useState<boolean>(false);
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [taggingProgress, setTaggingProgress] = useState<{status: 'processing' | 'updating' | 'success', current: number, total: number} | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['rifiuti', daysBack],
    queryFn: () => rifiutiService.getRifiuti(daysBack),
  });

  const rifiuti = data?.rifiuti || [];
  const summary = data?.summary || null;
  const ordiniDaTaggare = data?.ordini_da_taggare || [];

  const handleTagAllDaTaggare = async () => {
    console.log('🎯 Click su Tagga Tutti');
    const daTaggare = ordiniDaTaggare.length;
    console.log('📊 daTaggare:', daTaggare);
    console.log('📋 ordiniDaTaggare:', ordiniDaTaggare);

    if (daTaggare === 0) {
      alert('Non ci sono ordini da taggare');
      return;
    }

    // Apri modal di preview
    setShowPreviewModal(true);
  };

  const handleConfirmTagging = async () => {
    setShowPreviewModal(false);
    
    const orderIds = ordiniDaTaggare.map(o => o.order_id);
    
    console.log('📦 ordiniDaTaggare:', ordiniDaTaggare.length, 'elementi');
    console.log('🆔 orderIds:', orderIds);
    
    console.log('✅ Confirm confermato, inizio tagging...');
    
    // Inizializza progresso
    setTaggingProgress({ status: 'processing', current: 0, total: orderIds.length });
    
    // Procedi con il tagging effettivo (senza preview)
    setTaggingAll(true);
    try {
      // Aggiorna progresso durante processamento
      setTaggingProgress({ status: 'processing', current: 0, total: orderIds.length });
      
      const result = await rifiutiService.tagOrdini(orderIds, false);
      
      console.log('✅ Risultato tagging:', result);
      
      // Passa allo stato di aggiornamento dati
      setTaggingProgress({ status: 'updating', current: orderIds.length, total: orderIds.length });
      
      // Ricarica i dati immediatamente
      await refetch();
      
      // Ora che i dati sono aggiornati, passa a success
      setTaggingProgress({ status: 'success', current: orderIds.length, total: orderIds.length });
      
      // Mantieni il banner verde per 1 secondo
      setTimeout(() => {
        setTaggingAll(false);
        setTaggingProgress(null);
      }, 1000);
      
    } catch (err) {
      console.error('❌ Errore tagging:', err);
      alert(`❌ Errore: ${err instanceof Error ? err.message : 'Errore sconosciuto'}`);
      setTaggingAll(false);
      setTaggingProgress(null);
    }
  };

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
        <span>Errore nel caricamento dei dati: {error.message}</span>
      </div>
    );
  }

  const daTaggare = summary?.da_taggare || 0;
  const totale = summary?.totale || 0;
  const inTransito = summary?.in_transito || 0;
  const consegnati = summary?.consegnati || 0;
  const giaTaggati = summary?.gia_taggati || 0;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        
        <div className="flex items-center gap-2">
          <span className="text-base">Giorni:</span>
          <select 
            className="select select-bordered min-w-40 pl-4"
            value={daysBack}
            onChange={(e) => setDaysBack(Number(e.target.value))}
          >
            <option value={4}>4 giorni</option>
            <option value={7}>7 giorni</option>
            <option value={14}>14 giorni</option>
            <option value={30}>30 giorni</option>
            <option value={45}>45 giorni</option>
          </select>
        </div>

        <div 
          className={`card bg-base-100 shadow-sm hover:shadow-md transition-shadow cursor-pointer ${
            daTaggare === 0 ? 'opacity-50' : 'hover:bg-base-200'
          }`}
          onClick={daTaggare > 0 && !taggingAll ? handleTagAllDaTaggare : undefined}
        >
          <div className="card-body p-3">
            <div className="flex items-center gap-2">
              <div className="text-2xl">
                {taggingAll ? (
                  <span className="loading loading-spinner loading-md text-error"></span>
                ) : (
                  <svg className="w-6 h-6 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                )}
              </div>
              <div>
                <div className="text-xl font-bold text-error">{daTaggare}</div>
                <div className="text-sm text-base-content/70">
                  {taggingAll ? 'Applicando...' : 'Tagga Tutti'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Banner di progresso tagging */}
      {taggingAll && taggingProgress && (
        <div className={`alert shadow-lg mb-6 ${
          taggingProgress.status === 'success' 
            ? 'alert-success' 
            : 'alert-info'
        }`}>
          <div className="flex items-center gap-3">
            {taggingProgress.status === 'success' ? (
              <svg className="w-6 h-6 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <span className="loading loading-spinner loading-md"></span>
            )}
            <div>
              <div className="font-semibold">
                {taggingProgress.status === 'success' 
                  ? '✅ Tag applicati con successo!'
                  : taggingProgress.status === 'updating'
                  ? '🔄 Aggiornando dati...'
                  : '🏷️ Applicando tag RIFIUTO agli ordini...'
                }
              </div>
              <div className="text-sm">
                {taggingProgress.status === 'success' 
                  ? `${taggingProgress.total} ordini taggati`
                  : `${taggingProgress.current} / ${taggingProgress.total} ordini processati`
                }
              </div>
              {taggingProgress.status === 'processing' && (
                <progress 
                  className="progress progress-info w-full mt-2" 
                  value={taggingProgress.current} 
                  max={taggingProgress.total}
                ></progress>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body p-4">
            <div className="text-4xl mb-2">📦</div>
            <div className="text-3xl font-bold">{totale}</div>
            <div className="text-base text-base-content/70">Totale Rientri</div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body p-4">
            <div className="text-4xl mb-2">🚚</div>
            <div className="text-3xl font-bold">{inTransito}</div>
            <div className="text-base text-base-content/70">In Transito</div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body p-4">
            <div className="text-4xl mb-2">✅</div>
            <div className="text-3xl font-bold">{consegnati}</div>
            <div className="text-base text-base-content/70">Consegnati</div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body p-4">
            <div className="text-4xl mb-2">🏷️</div>
            <div className="text-3xl font-bold">{daTaggare}</div>
            <div className="text-base text-base-content/70">Da Taggare</div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="card-body p-4">
            <div className="text-4xl mb-2">✓</div>
            <div className="text-3xl font-bold">{giaTaggati}</div>
            <div className="text-base text-base-content/70">Già Taggati</div>
          </div>
        </div>

      </div>

      <div className="card bg-base-100 shadow-sm">
        <div className="card-body p-0">
          <div className="overflow-x-auto">
            <table className="table table-zebra">
              <thead>
                <tr className="text-base">
                  <th>Data</th>
                  <th>Tracking</th>
                  <th>Ordine</th>
                  <th>Destinatario</th>
                  <th>Località</th>
                  <th>Stato Spedizione</th>
                  <th>Stato Pagamento</th>
                  <th>Tag RIFIUTO</th>
                </tr>
              </thead>
              <tbody>
                {rifiuti.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-base-content/50">
                      Nessun rientro trovato negli ultimi {daysBack} giorni
                    </td>
                  </tr>
                ) : (
                  rifiuti.map((rifiuto) => (
                    <tr key={rifiuto.expedicion}>
                      <td className="text-sm">{rifiuto.fecha}</td>
                      <td className="text-sm font-mono">{rifiuto.expedicion}</td>
                      <td className="text-sm font-semibold">{rifiuto.referencia}</td>
                      <td className="text-sm">{rifiuto.destinatario}</td>
                      <td className="text-sm">{rifiuto.localidad}</td>
                      <td className="text-sm">
                        <span className="badge badge-sm badge-ghost">{rifiuto.estado}</span>
                      </td>
                      <td>
                        {rifiuto.stato_pagamento ? (
                          <span className={`badge badge-sm ${
                            rifiuto.stato_pagamento === 'PAID' ? 'badge-success' :
                            rifiuto.stato_pagamento === 'PENDING' ? 'badge-warning' :
                            'badge-ghost'
                          }`}>
                            {rifiuto.stato_pagamento}
                          </span>
                        ) : '-'}
                      </td>
                      <td>
                        {rifiuto.ha_tag_rifiuto ? (
                          <span className="badge badge-sm badge-success">✓ Sì</span>
                        ) : (
                          <span className="badge badge-sm badge-ghost">- No</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Modal di preview per tagging bulk */}
      <dialog className={`modal ${showPreviewModal ? 'modal-open' : ''}`}>
        <div className="modal-box max-w-2xl">
          <h3 className="font-bold text-lg mb-4">🗂️ Preview Tagging RIFIUTO</h3>
          
          <div className="alert alert-info mb-4">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="font-semibold">Conferma tagging di {ordiniDaTaggare.length} ordini</p>
              <p className="text-sm">Gli ordini verranno taggati con "RIFIUTO" in Shopify</p>
            </div>
          </div>

          <div className="max-h-60 overflow-y-auto">
            <table className="table table-zebra w-full">
              <thead>
                <tr>
                  <th>Referenza</th>
                  <th>Destinatario</th>
                  <th>Data</th>
                  <th>Pagamento</th>
                </tr>
              </thead>
              <tbody>
                {[...ordiniDaTaggare]
                  .sort((a, b) => a.referenza.localeCompare(b.referenza))
                  .map((ordine, index) => (
                  <tr key={index}>
                    <td className="font-mono text-sm">{ordine.referenza}</td>
                    <td>{ordine.destinatario}</td>
                    <td>{ordine.fecha}</td>
                    <td>
                      <span className={`badge ${ordine.stato_pagamento === 'PENDING' ? 'badge-warning' : 'badge-success'}`}>
                        {ordine.stato_pagamento}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="modal-action">
            <button 
              className="btn btn-ghost px-6" 
              onClick={() => setShowPreviewModal(false)}
              disabled={taggingAll}
            >
              Annulla
            </button>
            <button 
              className="btn btn-error px-6" 
              onClick={handleConfirmTagging}
              disabled={taggingAll}
            >
              {taggingAll ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Applicando...
                </>
              ) : (
                'Conferma'
              )}
            </button>
          </div>
        </div>
      </dialog>
    </div>
  );
};

export default Rifiuti;