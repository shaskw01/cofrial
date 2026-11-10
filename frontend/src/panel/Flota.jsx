import { useEffect, useState } from 'react'
import { Aviso, Cargando } from '../componentes/Basicos'
import { RangoTemp } from '../componentes/Temperatura'
import { haceCuanto, rangoTemp, temp } from '../formato'
import { Encabezado, useDatos } from './Panel'

const FILTROS = [
  ['todos', 'Todos'],
  ['alerta', 'En alerta'],
  ['ruta', 'En ruta'],
]

function Camion({ c }) {
  const l = c.lectura
  const alerta = Boolean(l?.alerta_ruptura_frio)
  return (
    <li
      className={`rounded-md border bg-white p-4 ${alerta ? 'border-ruptura ring-2 ring-ruptura' : 'border-hielo'} ${
        c.activo ? '' : 'opacity-60'
      }`}
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-2xl">{c.camion_id}</h2>
        <span className="text-sm text-pizarra">{c.patente}</span>
      </div>

      {l ? (
        <>
          <p className={`cifra mt-2 text-4xl leading-none font-semibold ${alerta ? 'text-ruptura' : ''}`}>
            {temp(l.temp_camara)}
          </p>
          <p className={`mt-1 text-sm ${alerta ? 'font-semibold text-ruptura' : 'text-pizarra'}`}>
            {alerta ? 'Ruptura de frío: fuera del rango ' : 'Dentro del rango '}
            {rangoTemp(c.rango.temp_min, c.rango.temp_max)}
          </p>
          <RangoTemp
            min={c.rango.temp_min}
            max={c.rango.temp_max}
            actual={l.temp_camara}
            alerta={alerta}
            className="mt-3"
          />
          <dl className="mt-4 grid grid-cols-2 gap-x-3 text-sm">
            <div>
              <dt className="text-pizarra">Combustible</dt>
              <dd className={`cifra text-lg ${l.combustible_pct < 15 ? 'font-semibold text-ambar' : ''}`}>
                {l.combustible_pct} %
              </dd>
            </div>
            <div>
              <dt className="text-pizarra">Posición</dt>
              <dd className="cifra text-lg">
                {Number(l.lat).toFixed(3)}, {Number(l.long).toFixed(3)}
              </dd>
            </div>
          </dl>
          <p className="mt-2 text-sm text-pizarra">Última lectura {haceCuanto(l.fecha_hora)}</p>
        </>
      ) : (
        <p className="mt-3 text-pizarra">Sin lecturas todavía.</p>
      )}

      <p className="mt-3 border-t border-hielo pt-2 text-sm">
        {c.despachos.length > 0
          ? c.despachos.map((d) => `Pedido N.º ${d.id_pedido}, ${d.cliente}`).join('; ')
          : c.activo
            ? 'Sin despacho en ruta'
            : 'Fuera de servicio'}
      </p>
    </li>
  )
}

export default function Flota() {
  const { datos: flota, error } = useDatos('/flota', { cadaMs: 5000 })
  const [filtro, setFiltro] = useState('todos')
  const [, tic] = useState(0)

  // Refresca los "hace X s" entre una consulta y la siguiente
  useEffect(() => {
    const id = setInterval(() => tic((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [])

  const enAlerta = (flota || []).filter((c) => c.lectura?.alerta_ruptura_frio)
  const enRuta = (flota || []).filter((c) => c.despachos.length > 0)
  const conLecturas = (flota || []).some((c) => c.lectura)
  const visibles = filtro === 'alerta' ? enAlerta : filtro === 'ruta' ? enRuta : flota || []
  // Los camiones en alerta van primero
  const ordenados = [...visibles].sort(
    (a, b) => Number(Boolean(b.lectura?.alerta_ruptura_frio)) - Number(Boolean(a.lectura?.alerta_ruptura_frio)),
  )

  return (
    <>
      <Encabezado
        titulo="Flota"
        detalle={
          flota
            ? `${flota.length} camiones, ${enRuta.length} con despacho en ruta, ${enAlerta.length} en alerta de frío. Se actualiza cada 5 segundos.`
            : 'Última lectura de cada camión.'
        }
      >
        <div className="inline-flex rounded border border-hielo bg-white p-0.5" role="group" aria-label="Filtrar camiones">
          {FILTROS.map(([valor, nombre]) => (
            <button
              key={valor}
              type="button"
              aria-pressed={filtro === valor}
              onClick={() => setFiltro(valor)}
              className={`rounded-[3px] px-3 py-1.5 text-sm font-semibold ${
                filtro === valor ? 'bg-camara text-white' : 'text-pizarra hover:text-camara'
              }`}
            >
              {nombre}
            </button>
          ))}
        </div>
      </Encabezado>

      <div className="mb-4 space-y-3">
        <Aviso>{error}</Aviso>
        {flota && !conLecturas && (
          <Aviso tipo="info">
            Todavía no llegan lecturas de los camiones. Aparecerán aquí en cuanto el simulador IoT empiece a enviar
            datos.
          </Aviso>
        )}
      </div>

      {!flota && !error ? (
        <Cargando />
      ) : ordenados.length === 0 ? (
        <p className="py-10 text-pizarra">
          {filtro === 'alerta' ? 'Ningún camión está en alerta de frío.' : 'Ningún camión tiene despachos en ruta.'}
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {ordenados.map((c) => (
            <Camion key={c.camion_id} c={c} />
          ))}
        </ul>
      )}
    </>
  )
}
