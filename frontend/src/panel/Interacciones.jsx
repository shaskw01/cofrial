import { useState } from 'react'
import { api } from '../api'
import { Aviso, Cargando } from '../componentes/Basicos'
import { fechaHora } from '../formato'
import { useDatos } from './Panel'

const TIPOS = ['llamada', 'correo', 'reunión', 'cotización', 'reclamo']

/** Historial de interacciones de una oportunidad ({oportunidad: id}) o de un cliente ({cliente: id}). */
export default function Interacciones({ de }) {
  const { datos, error, recargar } = useDatos('/interacciones', { params: de })
  const [tipo, setTipo] = useState('llamada')
  const [detalle, setDetalle] = useState('')
  const [errorForm, setErrorForm] = useState('')
  const [enviando, setEnviando] = useState(false)

  const registrar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setErrorForm('')
    try {
      await api('/interacciones', {
        method: 'POST',
        body: { id_oportunidad: de.oportunidad, id_cliente: de.cliente, tipo, detalle },
      })
      setDetalle('')
      recargar()
    } catch (err) {
      setErrorForm(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section>
      <h3 className="text-xl">Historial de interacciones</h3>
      <form onSubmit={registrar} className="mt-3 space-y-2">
        <Aviso>{errorForm}</Aviso>
        <div className="flex gap-2">
          <select className="campo w-36 shrink-0 capitalize" value={tipo} onChange={(e) => setTipo(e.target.value)} aria-label="Tipo de interacción">
            {TIPOS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <input
            className="campo"
            required
            placeholder="Qué se conversó o acordó"
            aria-label="Detalle de la interacción"
            value={detalle}
            onChange={(e) => setDetalle(e.target.value)}
          />
        </div>
        <button type="submit" className="boton boton-linea boton-chico" disabled={enviando}>
          Registrar interacción
        </button>
      </form>

      <div className="mt-4">
        <Aviso>{error}</Aviso>
        {!datos && !error && <Cargando />}
        {datos?.length === 0 && <p className="text-pizarra">Aún no hay interacciones. Registra la primera arriba.</p>}
        <ul className="divide-y divide-hielo">
          {datos?.map((i) => (
            <li key={i.id_interaccion} className="py-2.5">
              <p className="text-sm text-pizarra">
                <span className={`font-semibold capitalize ${i.tipo === 'reclamo' ? 'text-ruptura' : 'text-camara'}`}>
                  {i.tipo}
                </span>
                , {fechaHora(i.fecha)}
              </p>
              <p className="whitespace-pre-line">{i.detalle}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
