import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchGLSAlmacenadoData } from '../services/glsAlmacenadoService';
import type { GLSAlmacenadoItem } from '../services/glsAlmacenadoService';

const GLSAlmacenado = () => {
  const [daysBack, setDaysBack] = useState(15);

  // Aggiorna il titolo della pagina
  useEffect(() => {
    document.title = 'AdiBody ES - GLS Almacenado';
  }, []);

  const { data, isLoading, error } = useQuery({
    queryKey: ['gls-almacenado', daysBack],
    queryFn: () => fetchGLSAlmacenadoData(daysBack),
  });

  const handleDaysChange = (newDays: number) => {
    setDaysBack(newDays);
  };

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
        <span>Errore nel caricamento delle spedizioni GLS: {error.message}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Selettore Periodo */}
      <div className="card bg-base-100 shadow-sm border border-base-300 hover:shadow-md transition-shadow">
        <div className="card-body p-4">
          <h2 className="text-sm font-semibold text-base-content/70 mb-3">Periodo Selezionato</h2>

          {/* Bottoni periodo */}
          <div className="flex flex-wrap gap-2">
            <button
              className={`btn btn-sm ${daysBack === 7 ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => handleDaysChange(7)}
            >
              7 giorni
            </button>
            <button
              className={`btn btn-sm ${daysBack === 15 ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => handleDaysChange(15)}
            >
              15 giorni
            </button>
            <button
              className={`btn btn-sm ${daysBack === 30 ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => handleDaysChange(30)}
            >
              30 giorni
            </button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="card-body">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base-content/70 text-sm font-bold">Totale Spedizioni</p>
                  <p className="text-2xl font-bold text-primary">{data.metadata.total_shipments}</p>
                </div>
                <div className="text-3xl">📦</div>
              </div>
            </div>
          </div>

          <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="card-body">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base-content/70 text-sm font-bold">Periodo</p>
                  <p className="text-lg font-bold text-secondary">{data.metadata.period}</p>
                </div>
                <div className="text-3xl">📅</div>
              </div>
            </div>
          </div>

          <div className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="card-body">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base-content/70 text-sm font-bold">Stato Filtro</p>
                  <p className="text-lg font-bold text-accent">ALMACENADO</p>
                </div>
                <div className="text-3xl">🏪</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      {data && data.shipments.length > 0 && (
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h2 className="card-title font-bold">Spedizioni Almacenado</h2>
            <div className="overflow-x-auto">
              <table className="table table-zebra">
                <thead>
                  <tr>
                    <th>Expedición</th>
                    <th>Referencia</th>
                    <th>Destinatario</th>
                    <th>Dirección</th>
                    <th>Localidad</th>
                    <th>Fecha Envío</th>
                    <th>POD / Stato</th>
                    <th>Estado</th>
                    <th className="text-center">WhatsApp</th>
                  </tr>
                </thead>
                <tbody>
                  {data.shipments.map((shipment: GLSAlmacenadoItem, index: number) => (
                    <tr key={shipment.expedicion || index}>
                      <td className="font-mono font-medium">{shipment.expedicion}</td>
                      <td className="font-mono text-sm">{shipment.referencia}</td>
                      <td className="font-medium">{shipment.destinatario}</td>
                      <td className="text-sm max-w-xs truncate" title={shipment.direccion}>
                        {shipment.direccion}
                      </td>
                      <td>{shipment.localidad}</td>
                      <td>{shipment.fecha}</td>
                      <td className="text-sm">{shipment.pod}</td>
                      <td className="text-center">
                        <span className="badge badge-warning badge-sm whitespace-nowrap">
                          ALMACENADO
                        </span>
                      </td>
                      <td className="text-center">
                        {shipment.phone ? (
                          <a
                            href={`https://web.whatsapp.com/send?phone=${encodeURIComponent(shipment.phone.replace(/\D/g, ''))}&text=${encodeURIComponent(
                              `¡Hola ${shipment.destinatario.split(' ')[0]}! Somos el equipo de AdiBody.\n\n` +
                              `Tu paquete está almacenado en la agencia GLS de tu zona.\n` +
                              `Puedes ir a recogerlo antes de que sea devuelto al remitente.\n\n` +
                              `📦 Número de pedido: #ES${shipment.referencia}\n\n` +
                              (shipment.indirizzo_agenzia ? `📍 Dirección agencia: ${shipment.indirizzo_agenzia}\n` : '') +
                              (shipment.telefono_agenzia ? `📞 Teléfono: ${shipment.telefono_agenzia}\n` : '') +
                              (shipment.orari_agenzia ? `🕐 Horarios: ${shipment.orari_agenzia}\n` : '') +
                              `\n🔗 Seguimiento:\n` +
                              `https://mygls.gls-spain.es/e/${shipment.expedicion.replace('586-', '')}/${shipment.cp_dst}/es\n\n` +
                              `En el enlace puedes solicitar recoger tu paquete en la agencia.`
                            )}`}
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
      {data && data.shipments.length === 0 && (
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body text-center py-12">
            <div className="text-6xl mb-4">📦</div>
            <h3 className="text-xl font-bold mb-2">Nessuna spedizione trovata</h3>
            <p className="text-base-content/70">
              Non ci sono spedizioni in stato ALMACENADO nel periodo selezionato.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default GLSAlmacenado;