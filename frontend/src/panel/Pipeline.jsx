import { useState } from 'react'
import { api } from '../api'
import { Aviso, Campo, Cargando, Modal } from '../componentes/Basicos'
import { fecha, pesos } from '../formato'
import Interacciones from './Interacciones'
import { Encabezado, useDatos } from './Panel'

const COLOR_ETAPA = {
  Ganado: 'border-t-fresco',
  Perdido: 'border-t-ruptura',
}

/** Al ganar una oportunidad se crea el cliente institucional: se piden los datos que el prospecto no tiene. */
function Ganar({ oportunidad, onCerrar, onListo }) {
  const p = oportunidad.prospecto
  const [form, setForm] = useState({ direccion_despacho: '', telefono: p.telefono || '', rut: p.rut || '' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const campo = (nombre) => ({
    value: form[nombre],
    onChange: (e) => setForm({ ...form, [nombre]: e.target.value }),
  })

  const enviar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    try {
      await api(`/oportunidades/${oportunidad.id_oportunidad}`, { method: 'PATCH', body: { etapa: 'Ganado', ...form } })
      onListo(`${p.razon_social} ya es cliente institucional. Su cuenta para comprar en la tienda es ${p.email}.`)
    } catch (err) {
      setError(err.message)
      setEnviando(false)
    }
  }

  return (
    <Modal titulo={`Ganar a ${p.razon_social}`} onCerrar={onCerrar}>
      <form onSubmit={enviar} className="space-y-4">
        <p className="text-pizarra">
          Se creará el cliente institucional y su cuenta de acceso ({p.email}) con la lista de precios B2B.
        </p>
        <Aviso>{error}</Aviso>
        <Campo etiqueta="RUT de la empresa">
          <input className="campo" required maxLength={12} placeholder="76.123.456-7" {...campo('rut')} />
        </Campo>
        <Campo etiqueta="Teléfono de contacto">
          <input className="campo" required maxLength={20} {...campo('telefono')} />
        </Campo>
        <Campo etiqueta="Dirección de despacho">
          <input className="campo" required maxLength={200} placeholder="Calle, número y comuna" {...campo('direccion_despacho')} />
        </Campo>
        <button type="submit" className="boton boton-primario w-full" disabled={enviando}>
          {enviando ? 'Creando cliente…' : 'Marcar como ganado y crear cliente'}
        </button>
      </form>
    </Modal>
  )
}

function Ficha({ oportunidad, etapas, onMover, onCerrar }) {
  const p = oportunidad.prospecto
  return (
    <Modal titulo={p.razon_social} onCerrar={onCerrar} ancho="max-w-2xl">
      <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-pizarra">Monto estimado</dt>
          <dd className="cifra text-2xl font-semibold">{pesos(oportunidad.monto_estimado)}</dd>
        </div>
        <div>
          <dt className="text-sm text-pizarra">Etapa</dt>
          <dd>
            <select
              className="campo"
              value={oportunidad.etapa}
              onChange={(e) => onMover(oportunidad, e.target.value)}
              aria-label="Mover a otra etapa"
            >
              {etapas.map((e) => (
                <option key={e.id_etapa} value={e.nombre}>
                  {e.nombre}
                </option>
              ))}
            </select>
          </dd>
        </div>
        <div>
          <dt className="text-sm text-pizarra">Contacto</dt>
          <dd>
            {p.contacto}
            <span className="block text-sm text-pizarra">
              {p.email}
              {p.telefono && `, ${p.telefono}`}
            </span>
          </dd>
        </div>
        <div>
          <dt className="text-sm text-pizarra">Vendedor y fechas</dt>
          <dd>
            {p.vendedor_nombre}
            <span className="block text-sm text-pizarra">
              Abierta el {fecha(oportunidad.fecha_creacion)}
              {oportunidad.fecha_cierre && `, cerrada el ${fecha(oportunidad.fecha_cierre)}`}
            </span>
          </dd>
        </div>
      </dl>
      {p.id_cliente && (
        <p className="mt-3 rounded bg-fresco-suave px-3 py-2 text-sm text-[#0b5e59]">
          Ya es cliente institucional (cliente N.º {p.id_cliente}).
        </p>
      )}
      <div className="mt-5 border-t border-hielo pt-4">
        <Interacciones de={{ oportunidad: oportunidad.id_oportunidad }} />
      </div>
    </Modal>
  )
}

export default function Pipeline() {
  const { datos: etapas, error: errorEtapas } = useDatos('/etapas')
  const { datos: oportunidades, error, recargar } = useDatos('/oportunidades')
  const [arrastrando, setArrastrando] = useState(null)
  const [sobre, setSobre] = useState(null)
  const [ganando, setGanando] = useState(null)
  const [fichaId, setFichaId] = useState(null)
  const [aviso, setAviso] = useState(null)

  const mover = async (oportunidad, etapa) => {
    if (etapa === oportunidad.etapa) return
    if (etapa === 'Ganado' && !oportunidad.prospecto.id_cliente) {
      setFichaId(null)
      setGanando(oportunidad)
      return
    }
    try {
      await api(`/oportunidades/${oportunidad.id_oportunidad}`, { method: 'PATCH', body: { etapa } })
      setAviso(null)
      recargar()
    } catch (e) {
      setAviso({ tipo: 'error', texto: e.message })
    }
  }

  const soltar = (e, etapa) => {
    e.preventDefault()
    setSobre(null)
    const op = oportunidades.find((o) => o.id_oportunidad === arrastrando)
    setArrastrando(null)
    if (op) mover(op, etapa)
  }

  if ((!etapas || !oportunidades) && !error && !errorEtapas) return <Cargando />
  const ficha = oportunidades?.find((o) => o.id_oportunidad === fichaId)

  return (
    <>
      <Encabezado
        titulo="Pipeline comercial"
        detalle="Arrastra una oportunidad a otra etapa, o ábrela para ver su historial."
      />
      <div className="mb-4 space-y-3">
        <Aviso>{error || errorEtapas}</Aviso>
        {aviso && (
          <Aviso tipo={aviso.tipo} onCerrar={() => setAviso(null)}>
            {aviso.texto}
          </Aviso>
        )}
      </div>

      <div className="flex gap-3 overflow-x-auto p-0.5 pb-4">
        {etapas?.map((etapa) => {
          const tarjetas = (oportunidades || []).filter((o) => o.etapa === etapa.nombre)
          const total = tarjetas.reduce((s, o) => s + Number(o.monto_estimado), 0)
          return (
            <section
              key={etapa.id_etapa}
              aria-label={etapa.nombre}
              onDragOver={(e) => {
                e.preventDefault()
                setSobre(etapa.nombre)
              }}
              onDragLeave={() => setSobre((s) => (s === etapa.nombre ? null : s))}
              onDrop={(e) => soltar(e, etapa.nombre)}
              className={`flex min-w-40 flex-1 basis-0 flex-col rounded-md border-t-4 bg-white ${
                COLOR_ETAPA[etapa.nombre] || 'border-t-glaciar'
              } ${sobre === etapa.nombre ? 'ring-2 ring-glaciar' : 'ring-1 ring-hielo'}`}
            >
              <header className="px-3 pt-3 pb-2">
                <h2 className="text-xl">{etapa.nombre}</h2>
                <p className="cifra text-pizarra">
                  {tarjetas.length} {tarjetas.length === 1 ? 'oportunidad' : 'oportunidades'}, {pesos(total)}
                </p>
              </header>
              <ul className="min-h-24 flex-1 space-y-2 px-2 pb-2">
                {tarjetas.map((o) => (
                  <li
                    key={o.id_oportunidad}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.effectAllowed = 'move'
                      setArrastrando(o.id_oportunidad)
                    }}
                    onDragEnd={() => setArrastrando(null)}
                    className={`cursor-grab rounded border border-hielo bg-escarcha/60 p-3 active:cursor-grabbing ${
                      arrastrando === o.id_oportunidad ? 'opacity-40' : ''
                    }`}
                  >
                    <button
                      type="button"
                      className="text-left font-semibold underline decoration-hielo underline-offset-4 hover:decoration-camara"
                      onClick={() => setFichaId(o.id_oportunidad)}
                    >
                      {o.prospecto.razon_social}
                    </button>
                    <p className="cifra mt-1 text-xl font-semibold">{pesos(o.monto_estimado)}</p>
                    <p className="text-sm text-pizarra">{o.prospecto.contacto}</p>
                    <label className="mt-2 block text-sm text-pizarra">
                      Mover a
                      <select
                        className="campo mt-1 min-h-8 py-1 text-sm"
                        value={o.etapa}
                        onChange={(e) => mover(o, e.target.value)}
                      >
                        {etapas.map((e) => (
                          <option key={e.id_etapa} value={e.nombre}>
                            {e.nombre}
                          </option>
                        ))}
                      </select>
                    </label>
                  </li>
                ))}
              </ul>
            </section>
          )
        })}
      </div>

      {ficha && <Ficha oportunidad={ficha} etapas={etapas} onMover={mover} onCerrar={() => setFichaId(null)} />}
      {ganando && (
        <Ganar
          oportunidad={ganando}
          onCerrar={() => setGanando(null)}
          onListo={(texto) => {
            setGanando(null)
            setAviso({ tipo: 'ok', texto })
            recargar()
          }}
        />
      )}
    </>
  )
}
