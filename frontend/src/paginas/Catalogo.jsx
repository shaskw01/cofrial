import { useMemo, useState } from 'react'
import { Aviso, Cantidad, Cargando } from '../componentes/Basicos'
import { EscalaTemperatura, EtiquetaZona, RangoTemp } from '../componentes/Temperatura'
import { useCarrito, useCatalogo } from '../contexto'
import { esCongelado, pesos, unidad } from '../formato'

function Producto({ p }) {
  const { items, fijar } = useCarrito()
  const enCarrito = items[p.id_producto] || 0
  const agotado = p.stock_disponible === 0
  const sinPrecio = p.precio == null

  return (
    <li
      className={`flex flex-col rounded-md border border-hielo border-l-4 bg-white p-4 ${
        esCongelado(p.categoria) ? 'border-l-glaciar' : 'border-l-fresco'
      }`}
    >
      <p className="text-sm text-pizarra">
        {p.categoria.nombre} <span className="text-hielo">|</span> {p.sku}
      </p>
      <h3 className="mt-1 text-[1.45rem]">{p.nombre}</h3>

      <div className="mt-3">
        <EtiquetaZona categoria={p.categoria} />
        <RangoTemp min={p.categoria.temp_min} max={p.categoria.temp_max} className="mt-1.5" />
      </div>

      <div className="mt-auto flex items-end justify-between gap-3 pt-5">
        <div>
          <p className="cifra text-3xl leading-none font-semibold">
            {pesos(p.precio)}
            {!sinPrecio && <span className="text-lg font-medium text-pizarra"> / {unidad(p.unidad_medida)}</span>}
          </p>
          <p className={`mt-1.5 text-sm ${agotado ? 'font-semibold text-ruptura' : 'text-pizarra'}`}>
            {agotado ? 'Sin stock por ahora' : `Quedan ${p.stock_disponible} ${unidad(p.unidad_medida, p.stock_disponible)}`}
          </p>
        </div>
        {enCarrito > 0 ? (
          <Cantidad
            valor={enCarrito}
            max={p.stock_disponible}
            onCambiar={(n) => fijar(p.id_producto, n)}
            etiqueta={`Cantidad de ${p.nombre} en el carrito`}
          />
        ) : (
          <button
            type="button"
            className="boton boton-linea"
            disabled={agotado || sinPrecio}
            onClick={() => fijar(p.id_producto, 1)}
          >
            Agregar
          </button>
        )}
      </div>
    </li>
  )
}

export default function Catalogo() {
  const { productos, categorias, cargando, error, tipoPrecio } = useCatalogo()
  const [categoria, setCategoria] = useState(null)
  const [texto, setTexto] = useState('')

  const conteo = useMemo(() => {
    const c = {}
    for (const p of productos) c[p.categoria.id_categoria] = (c[p.categoria.id_categoria] || 0) + 1
    return Object.fromEntries(Object.entries(c).map(([k, n]) => [k, `${n} productos`]))
  }, [productos])

  const visibles = useMemo(() => {
    const q = texto.trim().toLowerCase()
    return productos.filter(
      (p) =>
        (categoria == null || p.categoria.id_categoria === categoria) &&
        (!q || p.nombre.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)),
    )
  }, [productos, categoria, texto])

  const elegida = categorias.find((c) => c.id_categoria === categoria)
  // Orden de la escala: de lo mas frio a lo menos frio
  const ordenadas = useMemo(
    () => [...categorias].sort((a, b) => Number(a.temp_min) - Number(b.temp_min) || a.nombre.localeCompare(b.nombre)),
    [categorias],
  )

  return (
    <>
      <section className="bg-camara text-white">
        <div className="mx-auto max-w-6xl px-4 pt-10 pb-8">
          <h1 className="max-w-3xl text-4xl sm:text-5xl">
            Congelados, refrigerados e insumos clínicos que llegan a la temperatura correcta
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-white/75">
            Cada categoría viaja en su propio rango de conservación. Elige una en la escala para ver sus productos.
          </p>
          <div className="mt-8">
            <EscalaTemperatura categorias={ordenadas} seleccion={categoria} onElegir={setCategoria} conteo={conteo} />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl">{elegida ? elegida.nombre : 'Todos los productos'}</h2>
            <p className="mt-1 text-pizarra">
              {tipoPrecio === 'B2B'
                ? 'Estás viendo la lista de precios institucional.'
                : 'Precios para público general. Las empresas e instituciones ven su lista al ingresar.'}
            </p>
          </div>
          <div className="flex w-full flex-wrap items-center gap-3 sm:w-auto">
            {elegida && (
              <button type="button" className="boton boton-linea" onClick={() => setCategoria(null)}>
                Ver todas las categorías
              </button>
            )}
            <input
              type="search"
              className="campo sm:w-64"
              placeholder="Buscar por nombre o código"
              aria-label="Buscar productos"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
            />
          </div>
        </div>

        <div className="mt-6">
          <Aviso>{error}</Aviso>
          {cargando ? (
            <Cargando texto="Cargando el catálogo…" />
          ) : visibles.length === 0 && !error ? (
            <p className="py-10 text-pizarra">
              Ningún producto coincide con la búsqueda. Prueba con otro nombre o elige otra categoría en la escala.
            </p>
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {visibles.map((p) => (
                <Producto key={p.id_producto} p={p} />
              ))}
            </ul>
          )}
        </div>
      </section>
    </>
  )
}
