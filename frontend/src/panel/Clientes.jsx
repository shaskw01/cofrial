import { useState } from 'react'
import { api } from '../api'
import { Aviso, Campo, Cargando, Modal } from '../componentes/Basicos'
import Interacciones from './Interacciones'
import { Encabezado, useDatos } from './Panel'

const VACIO = {
  email: '', tipo: 'B2B', id_vendedor: '', nombre_razon_social: '', rut: '', telefono: '', direccion_despacho: '',
}

function Formulario({ cliente, vendedores, onCerrar, onListo }) {
  const [form, setForm] = useState(
    cliente ? { ...cliente, id_vendedor: cliente.id_vendedor ?? '', rut: cliente.rut ?? '' } : VACIO,
  )
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const campo = (nombre) => ({
    value: form[nombre],
    onChange: (e) => setForm({ ...form, [nombre]: e.target.value }),
  })
  const esB2B = form.tipo === 'B2B'

  const guardar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    const body = {
      tipo: form.tipo,
      nombre_razon_social: form.nombre_razon_social,
      rut: form.rut || null,
      telefono: form.telefono,
      direccion_despacho: form.direccion_despacho,
    }
    if (form.id_vendedor) body.id_vendedor = Number(form.id_vendedor)
    else if (cliente) body.id_vendedor = null
    try {
      if (cliente) await api(`/clientes/${cliente.id_cliente}`, { method: 'PATCH', body })
      else await api('/clientes', { method: 'POST', body: { ...body, email: form.email } })
      onListo(cliente ? 'Cambios guardados.' : `Cliente creado. Su cuenta para comprar en la tienda es ${form.email}.`)
    } catch (err) {
      setError(err.message)
      setEnviando(false)
    }
  }

  return (
    <Modal titulo={cliente ? 'Editar cliente' : 'Nuevo cliente'} onCerrar={onCerrar}>
      <form onSubmit={guardar} className="space-y-4">
        <Aviso>{error}</Aviso>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Perfil">
            <select className="campo" {...campo('tipo')}>
              <option value="B2B">Institucional (B2B)</option>
              <option value="B2C">Persona (B2C)</option>
            </select>
          </Campo>
          <Campo etiqueta={esB2B ? 'RUT de la empresa' : 'RUT (opcional)'}>
            <input className="campo" maxLength={12} required={esB2B} {...campo('rut')} />
          </Campo>
        </div>
        <Campo etiqueta={esB2B ? 'Razón social' : 'Nombre completo'}>
          <input className="campo" required maxLength={150} {...campo('nombre_razon_social')} />
        </Campo>
        <Campo etiqueta="Correo de acceso" ayuda={cliente ? 'El correo de acceso no se cambia desde aquí.' : 'Con este correo entra a la tienda.'}>
          <input className="campo" type="email" required maxLength={120} disabled={Boolean(cliente)} {...campo('email')} />
        </Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Teléfono">
            <input className="campo" required maxLength={20} {...campo('telefono')} />
          </Campo>
          <Campo etiqueta="Vendedor asignado">
            <select className="campo" {...campo('id_vendedor')}>
              <option value="">{cliente ? 'Sin vendedor' : 'Yo, o sin vendedor'}</option>
              {vendedores?.map((v) => (
                <option key={v.id_vendedor} value={v.id_vendedor}>
                  {v.nombre}
                </option>
              ))}
            </select>
          </Campo>
        </div>
        <Campo etiqueta="Dirección de despacho">
          <input className="campo" required maxLength={200} {...campo('direccion_despacho')} />
        </Campo>
        <button type="submit" className="boton boton-primario w-full" disabled={enviando}>
          {enviando ? 'Guardando…' : cliente ? 'Guardar cambios' : 'Crear cliente'}
        </button>
      </form>
    </Modal>
  )
}

export default function Clientes() {
  const [tipo, setTipo] = useState('')
  const [texto, setTexto] = useState('')
  const { datos: clientes, error, recargar } = useDatos('/clientes', { params: { tipo, q: texto } })
  const { datos: vendedores } = useDatos('/vendedores')
  const [editando, setEditando] = useState(undefined) // undefined = cerrado, null = nuevo
  const [ficha, setFicha] = useState(null)
  const [aviso, setAviso] = useState(null)

  const eliminar = async (c) => {
    if (!window.confirm(`¿Eliminar a ${c.nombre_razon_social}? También se elimina su cuenta de acceso.`)) return
    try {
      await api(`/clientes/${c.id_cliente}`, { method: 'DELETE' })
      setAviso({ tipo: 'ok', texto: 'Cliente eliminado.' })
      recargar()
    } catch (e) {
      setAviso({ tipo: 'error', texto: e.message })
    }
  }

  return (
    <>
      <Encabezado titulo="Clientes" detalle="Instituciones y personas que compran en Cofrial.">
        <input
          type="search"
          className="campo w-52"
          placeholder="Buscar por nombre"
          aria-label="Buscar clientes"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
        <select className="campo w-44" value={tipo} onChange={(e) => setTipo(e.target.value)} aria-label="Filtrar por perfil">
          <option value="">Todos los perfiles</option>
          <option value="B2B">Institucionales</option>
          <option value="B2C">Personas</option>
        </select>
        <button type="button" className="boton boton-primario" onClick={() => setEditando(null)}>
          Nuevo cliente
        </button>
      </Encabezado>
      <div className="mb-4 space-y-3">
        <Aviso>{error}</Aviso>
        {aviso && (
          <Aviso tipo={aviso.tipo} onCerrar={() => setAviso(null)}>
            {aviso.texto}
          </Aviso>
        )}
      </div>

      {!clientes && !error ? (
        <Cargando />
      ) : clientes?.length === 0 ? (
        <p className="py-10 text-pizarra">Ningún cliente coincide con el filtro.</p>
      ) : (
        <div className="caja overflow-x-auto">
          <table className="w-full min-w-[46rem] text-left">
            <thead className="text-sm text-pizarra">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Cliente</th>
                <th className="px-4 py-2.5 font-semibold">Perfil</th>
                <th className="px-4 py-2.5 font-semibold">Contacto</th>
                <th className="px-4 py-2.5 font-semibold">Vendedor</th>
                <th className="px-4 py-2.5 text-right font-semibold">Pedidos</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {clientes?.map((c) => (
                <tr key={c.id_cliente} className="border-t border-hielo align-top">
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      className="text-left font-semibold underline decoration-hielo underline-offset-4 hover:decoration-camara"
                      onClick={() => setFicha(c)}
                    >
                      {c.nombre_razon_social}
                    </button>
                    <p className="text-sm text-pizarra">{c.rut || 'Sin RUT'}</p>
                  </td>
                  <td className="px-4 py-3">{c.tipo === 'B2B' ? 'Institucional' : 'Persona'}</td>
                  <td className="px-4 py-3">
                    <p>{c.email}</p>
                    <p className="text-sm text-pizarra">{c.telefono}</p>
                  </td>
                  <td className="px-4 py-3">{c.vendedor_nombre || <span className="text-pizarra">Sin asignar</span>}</td>
                  <td className="cifra px-4 py-3 text-right text-xl">{c.total_pedidos}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button type="button" className="boton boton-linea boton-chico" onClick={() => setEditando(c)}>
                        Editar
                      </button>
                      <button type="button" className="boton boton-peligro boton-chico" onClick={() => eliminar(c)}>
                        Eliminar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editando !== undefined && (
        <Formulario
          cliente={editando}
          vendedores={vendedores}
          onCerrar={() => setEditando(undefined)}
          onListo={(texto) => {
            setEditando(undefined)
            setAviso({ tipo: 'ok', texto })
            recargar()
          }}
        />
      )}
      {ficha && (
        <Modal titulo={ficha.nombre_razon_social} onCerrar={() => setFicha(null)} ancho="max-w-2xl">
          <p className="text-pizarra">
            {ficha.tipo === 'B2B' ? 'Cliente institucional' : 'Persona'}, {ficha.email}, {ficha.telefono}. Despacho en{' '}
            {ficha.direccion_despacho}.
          </p>
          <div className="mt-4 border-t border-hielo pt-4">
            <Interacciones de={{ cliente: ficha.id_cliente }} />
          </div>
        </Modal>
      )}
    </>
  )
}
