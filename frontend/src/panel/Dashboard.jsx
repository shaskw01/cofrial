import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Aviso, Cargando } from '../componentes/Basicos'
import { pesos, rangoTemp, temp } from '../formato'
import { Encabezado, useDatos } from './Panel'

// Colores de serie validados para daltonismo (web / vendedor). El rojo queda reservado para ruptura de frio.
const COLOR = { web: '#1c5fa6', vendedor: '#c9861a', neutro: '#1c5fa6', ruptura: '#c93a2b' }
const TINTA = '#4a6172'
const GRILLA = '#e6edf2'
const EJE = { fontSize: 13, fill: TINTA, fontFamily: 'Barlow, sans-serif' }

const compacto = (n) => {
  const v = Number(n)
  if (v >= 1_000_000) return `$${(v / 1_000_000).toLocaleString('es-CL', { maximumFractionDigits: 1 })} M`
  if (v >= 1_000) return `$${Math.round(v / 1_000)} mil`
  return `$${v}`
}
const pct = (n) => `${Number(n).toLocaleString('es-CL', { maximumFractionDigits: 1 })} %`
const diaCorto = (iso) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('es-CL', { weekday: 'short', day: 'numeric' }).replace('.', '')
const horaMinuto = (iso) => new Date(iso).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', hour12: false })

function Flotante({ active, payload, label, titulo, formato = (v) => v }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded border border-hielo bg-white px-3 py-2 text-sm shadow-md">
      <p className="font-semibold">{titulo ? titulo(label, payload) : label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="flex items-center gap-2">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: p.color || p.fill }} />
          {p.name}: <span className="cifra text-base font-semibold">{formato(p.value)}</span>
        </p>
      ))}
    </div>
  )
}

function Tarjeta({ titulo, valor, detalle, alerta = false }) {
  return (
    <div className={`rounded-md border bg-white px-4 py-3 ${alerta ? 'border-ruptura' : 'border-hielo'}`}>
      <p className="text-sm text-pizarra">{titulo}</p>
      <p className={`cifra mt-0.5 text-4xl leading-tight font-semibold ${alerta ? 'text-ruptura' : ''}`}>{valor}</p>
      <p className="text-sm text-pizarra">{detalle}</p>
    </div>
  )
}

function Grafico({ titulo, detalle, leyenda, children }) {
  return (
    <section className="caja p-4">
      <h2 className="text-xl">{titulo}</h2>
      <p className="text-sm text-pizarra">{detalle}</p>
      {leyenda && (
        <ul className="mt-2 flex gap-4 text-sm">
          {leyenda.map(([nombre, color]) => (
            <li key={nombre} className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
              {nombre}
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3 h-56">{children}</div>
    </section>
  )
}

function BarrasHorizontales({ datos, clave, formato, nombre }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={datos} layout="vertical" margin={{ top: 0, right: 64, bottom: 0, left: 0 }} barCategoryGap={8}>
        <XAxis type="number" hide domain={[0, 'dataMax']} />
        <YAxis type="category" dataKey="nombre" width={132} tick={EJE} axisLine={false} tickLine={false} />
        <Tooltip cursor={{ fill: GRILLA }} content={<Flotante formato={formato} />} />
        <Bar dataKey={clave} name={nombre} fill={COLOR.neutro} radius={[0, 4, 4, 0]} maxBarSize={20} isAnimationActive={false}>
          <LabelList dataKey={clave} position="right" formatter={formato} style={{ ...EJE, fill: '#0f2b3d', fontWeight: 600 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export default function Dashboard() {
  const { datos, error } = useDatos('/bi/resumen', { cadaMs: 5000 })
  const [, tic] = useState(0)
  useEffect(() => {
    const id = setInterval(() => tic((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [])

  if (!datos && !error) return <Cargando texto="Cargando el dashboard…" />
  if (!datos) return <Aviso>{error}</Aviso>

  const { comercial: c, operativo: o, cruce: x } = datos
  const segundos = Math.max(0, Math.round((Date.now() - new Date(datos.generado).getTime()) / 1000))
  const enRiesgo = x.pedidos_en_riesgo
  const sinTelemetria = o.camiones_reportando === 0
  const ventasDia = c.ventas_por_dia.map((d) => ({ ...d, dia: diaCorto(d.fecha) }))
  const serieAlertas = o.alertas_por_minuto.map((m) => ({ ...m, hora: horaMinuto(m.minuto) }))
  const camiones = [...o.temperatura_por_camion].sort((a, b) => b.alertas_15min - a.alertas_15min)

  return (
    <>
      <Encabezado titulo="Dashboard" detalle="Ventas y cadena de frío en una sola vista, con datos en vivo de la base.">
        <p className="flex items-center gap-2 text-sm text-pizarra" role="status">
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${error ? 'bg-ruptura' : 'bg-fresco'}`} />
          {error ? 'Sin conexión, reintentando.' : `Actualizado hace ${segundos} s`}
        </p>
      </Encabezado>

      {sinTelemetria && (
        <div className="mb-4">
          <Aviso tipo="info">
            No llegan lecturas de los camiones en los últimos 2 minutos. Revisa que el simulador IoT esté corriendo.
          </Aviso>
        </div>
      )}

      {/* El cruce comercial x IoT: lo primero que se ve */}
      <section
        className={`grid gap-x-8 gap-y-4 rounded-md border-l-4 bg-white p-5 lg:grid-cols-[minmax(0,20rem)_1fr] ${
          enRiesgo.length ? 'border-l-ruptura' : 'border-l-fresco'
        }`}
      >
        <div>
          <h2 className="text-xl">Ventas en riesgo por ruptura de frío</h2>
          <p className={`cifra mt-1 text-6xl leading-none font-semibold ${enRiesgo.length ? 'text-ruptura' : ''}`}>
            {pesos(x.monto_en_riesgo)}
          </p>
          <p className="mt-2 text-pizarra">
            {enRiesgo.length
              ? `${enRiesgo.length} de ${x.pedidos_en_ruta} pedidos en ruta viajan ahora en un camión con alerta: ${pct(x.pct_monto_en_riesgo)} de los ${pesos(x.monto_en_ruta)} en ruta.`
              : `Ninguno de los ${x.pedidos_en_ruta} pedidos en ruta (${pesos(x.monto_en_ruta)}) viaja en un camión con alerta.`}
          </p>
        </div>
        {enRiesgo.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[30rem] text-left">
              <thead className="text-sm text-pizarra">
                <tr>
                  <th className="py-1 pr-3 font-semibold">Pedido</th>
                  <th className="py-1 pr-3 font-semibold">Cliente</th>
                  <th className="py-1 pr-3 font-semibold">Camión</th>
                  <th className="py-1 pr-3 font-semibold">Temperatura</th>
                  <th className="py-1 text-right font-semibold">Monto</th>
                </tr>
              </thead>
              <tbody>
                {enRiesgo.map((p) => (
                  <tr key={p.id_pedido} className="border-t border-hielo">
                    <td className="cifra py-1.5 pr-3 text-lg">N.º {p.id_pedido}</td>
                    <td className="py-1.5 pr-3">{p.cliente}</td>
                    <td className="cifra py-1.5 pr-3 text-lg">{p.camion_id}</td>
                    <td className="py-1.5 pr-3">
                      <span className="cifra text-lg font-semibold text-ruptura">{temp(p.temp_camara)}</span>
                      <span className="text-sm text-pizarra"> (rango {rangoTemp(p.temp_min_rango, p.temp_max_rango)})</span>
                    </td>
                    <td className="cifra py-1.5 text-right text-lg font-semibold">{pesos(p.monto)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Tarjeta titulo="Ventas de hoy" valor={pesos(c.ventas_hoy)} detalle={`${c.pedidos_hoy} pedidos`} />
        <Tarjeta titulo="Ventas de los últimos 7 días" valor={pesos(c.ventas_7d)} detalle={`${c.pedidos_7d} pedidos`} />
        <Tarjeta
          titulo="Pedidos por la tienda web"
          valor={pct(c.pct_pedidos_web)}
          detalle={`${c.por_canal[0].pedidos} web y ${c.por_canal[1].pedidos} por vendedor, en 7 días`}
        />
        <Tarjeta
          titulo="Conversión del pipeline"
          valor={pct(c.pipeline.conversion_pct)}
          detalle={`${c.pipeline.ganadas} ganadas de ${c.pipeline.oportunidades} oportunidades`}
        />
        <Tarjeta
          titulo="Camiones en alerta ahora"
          valor={o.camiones_en_alerta}
          detalle={`de ${o.camiones_reportando} camiones reportando`}
          alerta={o.camiones_en_alerta > 0}
        />
        <Tarjeta
          titulo="Lecturas en alerta, última hora"
          valor={o.alertas_ultima_hora.toLocaleString('es-CL')}
          detalle={`de ${o.lecturas_ultima_hora.toLocaleString('es-CL')} lecturas recibidas`}
        />
        <Tarjeta
          titulo="Despachos con alguna alerta"
          valor={pct(x.pct_despachos_con_alerta)}
          detalle={`${x.despachos_con_alerta} de ${x.despachos_total} despachos`}
        />
        <Tarjeta
          titulo="Ventas por perfil, 7 días"
          valor={pesos(c.por_perfil[0].monto)}
          detalle={`institucional; ${pesos(c.por_perfil[1].monto)} personas`}
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Grafico
          titulo="Ventas por día y canal"
          detalle="Últimos 7 días, sin pedidos rechazados."
          leyenda={[['Tienda web', COLOR.web], ['Vendedor', COLOR.vendedor]]}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ventasDia} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke={GRILLA} />
              <XAxis dataKey="dia" tick={EJE} axisLine={{ stroke: GRILLA }} tickLine={false} />
              <YAxis tick={EJE} tickFormatter={compacto} axisLine={false} tickLine={false} width={64} />
              <Tooltip
                cursor={{ fill: GRILLA }}
                content={<Flotante formato={pesos} titulo={(l, p) => `${l}, ${p[0].payload.pedidos} pedidos`} />}
              />
              <Bar dataKey="web" name="Tienda web" stackId="v" fill={COLOR.web} stroke="#fff" strokeWidth={2} maxBarSize={24} isAnimationActive={false} />
              <Bar dataKey="vendedor" name="Vendedor" stackId="v" fill={COLOR.vendedor} stroke="#fff" strokeWidth={2} radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </Grafico>

        <Grafico titulo="Camiones con ruptura de frío por minuto" detalle="Últimos 30 minutos, según las lecturas IoT.">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={serieAlertas} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke={GRILLA} />
              <XAxis dataKey="hora" tick={EJE} axisLine={{ stroke: GRILLA }} tickLine={false} interval={4} />
              <YAxis tick={EJE} allowDecimals={false} axisLine={false} tickLine={false} width={32} />
              <Tooltip
                cursor={{ stroke: TINTA, strokeWidth: 1 }}
                content={<Flotante formato={(v) => `${v} camiones`} titulo={(l) => `${l} h`} />}
              />
              <Area
                type="monotone"
                dataKey="camiones_en_alerta"
                name="En alerta"
                stroke={COLOR.ruptura}
                strokeWidth={2}
                fill={COLOR.ruptura}
                fillOpacity={0.1}
                activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Grafico>

        <Grafico titulo="Pedidos por estado" detalle="Pedidos creados en los últimos 7 días.">
          <BarrasHorizontales datos={c.por_estado} clave="pedidos" nombre="Pedidos" formato={(v) => v} />
        </Grafico>

        <Grafico titulo="Pipeline comercial por etapa" detalle="Monto estimado de las oportunidades en cada etapa.">
          <BarrasHorizontales datos={c.pipeline.etapas} clave="monto" nombre="Monto estimado" formato={compacto} />
        </Grafico>
      </div>

      <details className="caja mt-4 p-4">
        <summary className="font-rotulo text-xl font-semibold">
          Temperatura promedio por camión, últimos 15 minutos
        </summary>
        <div className="mt-3 max-h-96 overflow-auto">
          <table className="w-full min-w-[34rem] text-left">
            <thead className="sticky top-0 bg-white text-sm text-pizarra">
              <tr>
                <th className="py-1 pr-3 font-semibold">Camión</th>
                <th className="py-1 pr-3 font-semibold">Rango de la carga</th>
                <th className="py-1 pr-3 text-right font-semibold">Promedio</th>
                <th className="py-1 pr-3 text-right font-semibold">Máxima</th>
                <th className="py-1 text-right font-semibold">Lecturas en alerta</th>
              </tr>
            </thead>
            <tbody>
              {camiones.map((k) => (
                <tr key={k.camion_id} className="border-t border-hielo">
                  <td className="cifra py-1 pr-3 text-lg">
                    {k.camion_id}
                    {k.en_alerta && <span className="ml-2 font-sans text-sm font-semibold text-ruptura">En alerta</span>}
                  </td>
                  <td className="cifra py-1 pr-3 text-lg">{rangoTemp(k.temp_min_rango, k.temp_max_rango)}</td>
                  <td className="cifra py-1 pr-3 text-right text-lg">{temp(k.temp_promedio)}</td>
                  <td className="cifra py-1 pr-3 text-right text-lg">{temp(k.temp_maxima)}</td>
                  <td className="cifra py-1 text-right text-lg">{k.alertas_15min}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  )
}
