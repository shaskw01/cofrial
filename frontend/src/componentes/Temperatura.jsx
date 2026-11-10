import { esCongelado, rangoTemp, temp } from '../formato'

// Eje comun a toda la aplicacion: de −28 a +10 °C. Lo usan el catalogo, las fichas y la flota.
const MIN = -28
const MAX = 10
const MARCAS = [-25, -20, -15, -10, -5, 0, 5]
export const posicion = (t) => Math.min(100, Math.max(0, ((Number(t) - MIN) / (MAX - MIN)) * 100))

function estiloRango(min, max) {
  return { left: `${posicion(min)}%`, width: `${posicion(max) - posicion(min)}%` }
}

/** Barra chica con el rango de conservacion; `actual` dibuja la lectura del camion sobre el mismo eje. */
export function RangoTemp({ min, max, actual, alerta = false, className = '' }) {
  const congelado = Number(max) <= -10
  return (
    <div className={`relative h-2 rounded-full bg-escarcha ${className}`} aria-hidden="true">
      <span className="absolute inset-y-0 w-px bg-hielo" style={{ left: `${posicion(0)}%` }} />
      <span
        className={`absolute inset-y-0 rounded-full ${congelado ? 'bg-glaciar' : 'bg-fresco'} ${actual != null ? 'opacity-35' : ''}`}
        style={estiloRango(min, max)}
      />
      {actual != null && (
        <span
          className={`absolute -top-1 h-4 w-1 -translate-x-1/2 rounded-sm ${alerta ? 'bg-ruptura' : 'bg-camara'}`}
          style={{ left: `${posicion(actual)}%` }}
        />
      )}
    </div>
  )
}

/**
 * Escala de temperatura del catalogo: cada categoria es una franja sobre el mismo eje.
 * Elegir una franja filtra los productos.
 */
export function EscalaTemperatura({ categorias, seleccion, onElegir, conteo = {} }) {
  return (
    <div>
      <div className="hidden md:grid md:grid-cols-[15rem_1fr] md:gap-x-6">
        <span />
        <div className="relative h-6 cifra text-sm text-white/60">
          {MARCAS.map((m) => (
            <span key={m} className="absolute -translate-x-1/2" style={{ left: `${posicion(m)}%` }}>
              {m === 0 ? '0 °C' : String(m).replace('-', '−')}
            </span>
          ))}
        </div>
      </div>

      <ul className="relative">
        {categorias.map((c) => {
          const activa = seleccion === c.id_categoria
          const congelado = esCongelado(c)
          return (
            <li key={c.id_categoria}>
              <button
                type="button"
                aria-pressed={activa}
                onClick={() => onElegir(activa ? null : c.id_categoria)}
                className={`group grid w-full items-center gap-x-6 gap-y-1 border-t border-white/10 py-2.5 text-left md:grid-cols-[15rem_1fr] ${
                  activa ? 'text-white' : 'text-white/75 hover:text-white'
                }`}
              >
                <span className="flex items-baseline justify-between gap-3">
                  <span className={`font-rotulo text-xl ${activa ? 'font-semibold' : 'font-medium'}`}>{c.nombre}</span>
                  <span className="cifra text-sm text-white/50">{conteo[c.id_categoria] ?? ''}</span>
                </span>
                <span className="relative block h-7">
                  {MARCAS.map((m) => (
                    <span
                      key={m}
                      className={`absolute inset-y-0 w-px ${m === 0 ? 'bg-white/35' : 'bg-white/10'}`}
                      style={{ left: `${posicion(m)}%` }}
                    />
                  ))}
                  <span
                    className={`absolute inset-y-1 flex items-center rounded-sm px-2 transition-[filter,box-shadow] ${
                      congelado ? 'bg-[#4f9be6]' : 'bg-[#3fc4b8]'
                    } ${activa ? 'ring-2 ring-white ring-offset-2 ring-offset-camara' : 'brightness-75 group-hover:brightness-100'}`}
                    style={estiloRango(c.temp_min, c.temp_max)}
                  />
                  <span
                    className="cifra absolute top-1/2 -translate-y-1/2 pl-3 text-sm whitespace-nowrap text-white/80"
                    style={{ left: `${posicion(c.temp_max)}%` }}
                  >
                    {congelado ? rangoTemp(c.temp_min, c.temp_max) : ''}
                  </span>
                  {!congelado && (
                    <span
                      className="cifra absolute top-1/2 -translate-x-full -translate-y-1/2 pr-2 text-sm whitespace-nowrap text-white/80"
                      style={{ left: `${posicion(c.temp_min)}%` }}
                    >
                      {/* fondo propio para que la linea de 0 °C no cruce el texto */}
                      <span className="bg-camara px-1.5 py-0.5">{rangoTemp(c.temp_min, c.temp_max)}</span>
                    </span>
                  )}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/** Texto del rango con su zona, para fichas y tablas. */
export function EtiquetaZona({ categoria }) {
  const congelado = esCongelado(categoria)
  return (
    <span className={`cifra text-[0.95rem] font-medium ${congelado ? 'text-glaciar' : 'text-fresco'}`}>
      {congelado ? 'Congelado' : 'Refrigerado'}, {rangoTemp(categoria.temp_min, categoria.temp_max)}
    </span>
  )
}

export { temp }
