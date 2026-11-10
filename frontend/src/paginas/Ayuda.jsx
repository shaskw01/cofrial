import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Aviso, Campo } from '../componentes/Basicos'
import { useSesion } from '../contexto'
import { NOMBRE_CATEGORIA, Prioridad } from '../panel/Requerimientos'

export default function Ayuda() {
  const { usuario, esCliente, esInterno } = useSesion()
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [respuesta, setRespuesta] = useState(null)

  const enviar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setError('')
    try {
      setRespuesta(await api('/contacto', { method: 'POST', body: { texto } }))
      setTexto('')
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-4xl">Ayuda</h1>
      <p className="mt-2 text-pizarra">
        Cuéntanos qué necesitas: un reclamo, una consulta por tu pedido o una cotización. Tu mensaje llega de
        inmediato al equipo de Cofrial.
      </p>

      {!usuario && (
        <div className="caja mt-6 p-5">
          <p>Para escribirnos necesitas ingresar con tu cuenta, así sabemos a qué cliente responder.</p>
          <Link to="/ingresar?volver=/ayuda" className="boton boton-primario mt-3">
            Ingresar para escribir
          </Link>
        </div>
      )}
      {esInterno && (
        <div className="mt-6">
          <Aviso tipo="info">
            Estás con una cuenta interna. Este formulario es para clientes; sus mensajes se ven en el panel, en
            «Requerimientos».
          </Aviso>
        </div>
      )}

      {esCliente && (
        <form onSubmit={enviar} className="mt-6 space-y-4">
          <Aviso>{error}</Aviso>
          <Campo etiqueta="Tu mensaje">
            <textarea
              className="campo min-h-36"
              required
              minLength={5}
              maxLength={2000}
              placeholder="Ej.: el pedido llegó con la carne blanda y caliente."
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
            />
          </Campo>
          <button type="submit" className="boton boton-primario" disabled={enviando}>
            {enviando ? 'Enviando…' : 'Enviar mensaje'}
          </button>
        </form>
      )}

      {respuesta && (
        <section className="caja mt-6 border-l-4 border-l-fresco p-5" role="status">
          <h2 className="text-2xl">Mensaje enviado</h2>
          <p className="mt-2 whitespace-pre-line">{respuesta.respuesta_sugerida}</p>
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-hielo pt-3 text-sm text-pizarra">
            {respuesta.clasificado ? (
              <>
                <span>Nuestro asistente lo registró como</span>
                <span className="font-semibold text-camara">{NOMBRE_CATEGORIA[respuesta.categoria]}</span>
                <Prioridad valor={respuesta.prioridad} />
              </>
            ) : (
              <span>Quedó registrado para revisión de un ejecutivo.</span>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
