import { useEffect, useRef, useState } from 'react';
import {
  fetchGLSAlmacenadoData,
  fetchAgenziaDetails,
  parseGLSEmail,
  buildWhatsAppMessage,
  CATEGORIA_CONFIG,
} from '../services/glsAlmacenadoService';
import type { GLSAlmacenadoItem, ParsedEmailEntry } from '../services/glsAlmacenadoService';

type EnrichedShipment = GLSAlmacenadoItem & { emailEntry: ParsedEmailEntry };
type PageState = 'idle' | 'loading' | 'results';

const WA_ICON = (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
    <path d="M13.601 2.326A7.854 7.854 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.933 7.933 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.898 7.898 0 0 0 13.6 2.326zM7.994 14.521a6.573 6.573 0 0 1-3.356-.92l-.24-.144-2.494.654.666-2.433-.156-.251a6.56 6.56 0 0 1-1.007-3.505c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.557 6.557 0 0 1 1.928 4.66c-.004 3.639-2.961 6.592-6.592 6.592zm3.615-4.934c-.197-.099-1.17-.578-1.353-.646-.182-.065-.315-.099-.445.099-.133.197-.513.646-.627.775-.114.133-.232.148-.43.05-.197-.1-.836-.308-1.592-.985-.59-.525-.985-1.175-1.103-1.372-.114-.198-.011-.304.088-.403.087-.088.197-.232.296-.346.1-.114.133-.198.198-.33.065-.134.034-.248-.015-.347-.05-.099-.445-1.076-.612-1.47-.16-.389-.323-.335-.445-.34-.114-.007-.247-.007-.38-.007a.729.729 0 0 0-.529.247c-.182.198-.691.677-.691 1.654 0 .977.71 1.916.81 2.049.098.133 1.394 2.132 3.383 2.992.47.205.84.326 1.129.418.475.152.904.129 1.246.08.38-.058 1.171-.48 1.338-.943.164-.464.164-.86.114-.943-.049-.084-.182-.133-.38-.232z"/>
  </svg>
);

const GLSAlmacenado = () => {
  useEffect(() => { document.title = 'AdiBody ES - GLS No Entregado'; }, []);

  const [pageState, setPageState] = useState<PageState>('idle');
  const [isDragging, setIsDragging] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [enriched, setEnriched] = useState<EnrichedShipment[]>([]);
  const [period, setPeriod] = useState<string>('');
  const dropRef = useRef<HTMLDivElement>(null);

  const processText = async (text: string) => {
    const parsed = parseGLSEmail(text);
    if (parsed.length === 0) {
      setParseError('No se encontraron expediciones en el texto. Verifica el formato del email.');
      return;
    }
    setParseError(null);
    setPageState('loading');
    try {
      const lambdaData = await fetchGLSAlmacenadoData(30);
      const lambdaMap = new Map(lambdaData.shipments.map(s => [s.expedicion.replace('586-', ''), s]));
      const enrichedRows: EnrichedShipment[] = [];
      for (const entry of parsed) {
        const shipment = lambdaMap.get(entry.expedicion);
        if (shipment) enrichedRows.push({ ...shipment, emailEntry: entry });
      }

      // Fetch agenzia details in parallel for RECOGIDA shipments
      const recogidaRows = enrichedRows.filter(r => r.emailEntry.categoria === 'RECOGIDA');
      if (recogidaRows.length > 0) {
        await Promise.all(recogidaRows.map(async r => {
          try {
            const ag = await fetchAgenziaDetails(r.expedicion);
            r.indirizzo_agenzia = ag.indirizzo_agenzia;
            r.telefono_agenzia = ag.telefono_agenzia;
            r.orari_agenzia = ag.orari_agenzia;
          } catch { /* lascia null */ }
        }));
      }

      setEnriched(enrichedRows);
      setPeriod(lambdaData.metadata.period);
      setPageState('results');
    } catch {
      setPageState('idle');
      setParseError('Error al cargar datos GLS. Comprueba tu conexión e inténtalo de nuevo.');
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = ev => processText(ev.target?.result as string ?? '');
      reader.readAsText(file);
    } else {
      const text = e.dataTransfer.getData('text/plain');
      if (text) processText(text);
    }
  };

  // ─── IDLE ─────────────────────────────────────────────────────────────────
  if (pageState === 'idle') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] gap-6 px-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-1">GLS Spedizioni Problematiche</h1>
        </div>

        <div
          ref={dropRef}
          className={`w-full max-w-2xl border-2 border-dashed rounded-2xl transition-all duration-200 cursor-pointer ${
            isDragging
              ? 'border-primary bg-primary/10 scale-[1.02]'
              : 'border-base-300 bg-base-100 hover:border-primary/50'
          }`}
          onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <div className="p-12 flex flex-col items-center gap-3 text-center select-none">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-12 h-12 text-base-content/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              {isDragging
                ? <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                : <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              }
            </svg>
            <p className="text-base-content/60 text-sm">
              {isDragging ? 'Rilascia il file qui...' : "Trascina qui il file .txt dell'email GLS"}
            </p>
          </div>
        </div>

        {parseError && (
          <div className="alert alert-error py-2 text-sm max-w-2xl w-full">{parseError}</div>
        )}
      </div>
    );
  }

  // ─── LOADING ──────────────────────────────────────────────────────────────
  if (pageState === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <span className="loading loading-spinner loading-lg text-primary"></span>
        <p className="text-base-content/60 text-sm">Caricamento dati GLS...</p>
      </div>
    );
  }

  // ─── RESULTS ──────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body py-4">
            <p className="text-xs text-base-content/50 uppercase font-semibold tracking-wide">Periodo riferimento</p>
            <p className="text-sm font-bold mt-1">{period}</p>
          </div>
        </div>
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body py-4">
            <p className="text-xs text-base-content/50 uppercase font-semibold tracking-wide">Spedizioni problematiche</p>
            <p className="text-2xl font-bold mt-1 text-warning">{enriched.length}</p>
          </div>
        </div>
        <div className="card bg-base-100 shadow-sm cursor-pointer hover:bg-base-200 transition-colors" onClick={() => setPageState('idle')}>
          <div className="card-body py-4 flex flex-col items-center justify-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7 text-base-content/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <p className="text-sm font-bold">Nuova analisi</p>
          </div>
        </div>
      </div>

      {/* Main table */}
      {enriched.length > 0 && (
        <div className="card bg-base-100 shadow-sm">
          <div className="overflow-x-auto">
          <table className="table table-zebra table-sm">
            <thead>
              <tr>
                <th>Expedición</th>
                <th>Referencia</th>
                <th>Destinatario</th>
                <th>Dirección</th>
                <th>Localidad</th>
                <th>Fecha Envío</th>
                <th>Reembolso</th>
                <th>Motivo GLS</th>
                <th>Categoría</th>
                <th className="text-center">WhatsApp</th>
              </tr>
            </thead>
            <tbody>
              {[...enriched].sort((a, b) => {
                const toDate = (f: string) => { const [d, m, y] = f.split('/'); return new Date(`${y}-${m}-${d}`).getTime(); };
                return toDate(b.fecha) - toDate(a.fecha);
              }).map((s, i) => {
                const cfg = CATEGORIA_CONFIG[s.emailEntry.categoria];
                return (
                  <tr key={s.expedicion || i}>
                    <td className="font-mono font-medium">
                      <a
                        href={`https://mygls.gls-spain.es/e/${s.expedicion.replace('586-', '')}/${s.cp_dst}/es`}
                        target="_blank" rel="noopener noreferrer"
                        className="link link-primary"
                      >
                        {s.expedicion}
                      </a>
                    </td>
                    <td className="font-mono text-xs">{s.referencia}</td>
                    <td className="font-medium">{s.destinatario}</td>
                    <td className="text-xs max-w-[180px] truncate" title={s.direccion}>{s.direccion}</td>
                    <td className="text-xs">{s.localidad}</td>
                    <td className="text-xs">{s.fecha}</td>
                    <td className="font-bold text-warning">{s.reembolso}</td>
                    <td className="text-xs min-w-[180px] max-w-[260px] whitespace-normal">{s.emailEntry.motivoRaw}</td>
                    <td>
                      <span className={`badge badge-sm whitespace-nowrap ${cfg.badgeClass}`}>
                        {cfg.label}
                      </span>
                    </td>
                    <td className="text-center">
                      {s.phone ? (
                        <a
                          href={`https://web.whatsapp.com/send?phone=${encodeURIComponent(s.phone.replace(/\D/g, ''))}&text=${encodeURIComponent(buildWhatsAppMessage(s.emailEntry, s.referencia, s.reembolso, s.emailEntry.categoria === 'RECOGIDA' ? { indirizzo_agenzia: s.indirizzo_agenzia, telefono_agenzia: s.telefono_agenzia, orari_agenzia: s.orari_agenzia } : undefined, s.expedicion))}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-success btn-sm btn-circle"
                          title={`Messaggio: ${cfg.label}`}
                        >
                          {WA_ICON}
                        </a>
                      ) : (
                        <span className="text-xs text-error" title="Telefono non disponibile">❌</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {enriched.length === 0 && (
        <div className="text-center py-16 text-base-content/50">
          Nessuna spedizione trovata. Riprova con un testo diverso.
        </div>
      )}
    </div>
  );
};

export default GLSAlmacenado;

