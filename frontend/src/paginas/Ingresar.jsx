import { useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { Aviso, Campo } from '../componentes/Basicos'
import { inicioSegunRol, useSesion } from '../contexto'

// Cuentas de la demo: solo completan el correo. La contraseña vive en el .env, nunca en el codigo.
const CUENTAS_DEMO = [
  ['compras@hospitalregional.cl', 'Institución (Hospital Regional)'],
  ['cliente@gmail.com', 'Persona'],
  ['vendedor@cofrial.cl', 'Vendedor'],
  ['despacho@cofrial.cl', 'Despacho'],
  ['admin@cofrial.cl', 'Administración'],
]

export default function Ingresar() {
  const { usuario, ingresar } = useSesion()
  const navegar = useNavigate()
  const [params] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const destino = (u) => (u.rol === 'cliente' ? params.get('volver') || '/' : inicioSegunRol(u))
  if (usuario) return <Navigate to={destino(usuario)} replace />

  const enviar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setError('')
    try {
      navegar(destino(await ingresar(email, password)), { replace: true })
    } catch (err) {
      setError(err.message)
      setEnviando(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-4xl gap-10 px-4 py-12 md:grid-cols-[1fr_18rem]">
      <div>
        <h1 className="text-4xl">Ingresar</h1>
        {params.get('perfil') === 'institucion' && (
          <p className="mt-3 max-w-prose text-pizarra">
            Los precios institucionales se muestran al ingresar con la cuenta de tu empresa. Si todavía no tienes
            una, tu vendedor de Cofrial la crea al cerrar el acuerdo comercial.
          </p>
        )}
        <form onSubmit={enviar} className="mt-6 max-w-sm space-y-4">
          <Aviso>{error}</Aviso>
          <Campo etiqueta="Correo">
            <input
              className="campo"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Campo>
          <Campo etiqueta="Contraseña">
            <input
              className="campo"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Campo>
          <button type="submit" className="boton boton-primario w-full" disabled={enviando}>
            {enviando ? 'Ingresando…' : 'Ingresar'}
          </button>
        </form>
      </div>

      <aside className="caja self-start p-4">
        <h2 className="text-xl">Cuentas de demostración</h2>
        <p className="mt-1 text-sm text-pizarra">Elige una para completar el correo. La contraseña es la de la demo.</p>
        <ul className="mt-3 space-y-1">
          {CUENTAS_DEMO.map(([correo, nombre]) => (
            <li key={correo}>
              <button
                type="button"
                onClick={() => setEmail(correo)}
                className="w-full rounded px-2 py-1.5 text-left hover:bg-escarcha"
              >
                <span className="block font-semibold">{nombre}</span>
                <span className="block text-sm text-pizarra">{correo}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
