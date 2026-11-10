import { useState } from 'react'
import { api } from '../api'
import { Aviso, Campo, Cargando, Modal } from '../componentes/Basicos'
import { useSesion } from '../contexto'
import { pesos } from '../formato'
import { Encabezado, useDatos } from './Panel'

const VACIO = { razon_social: '', rut: '', contacto: '', email: '', telefono: '', monto_estimado: '', id_vendedor: '' }

function Formulario({ prospecto, vendedores, pideVendedor, onCerrar, onListo }) {
  const [form, setForm] = useState(
    prospecto ? { ...VACIO, ...prospecto, rut: prospecto.rut ?? '', telefono: prospecto.telefono ?? '' } : VACIO,
  )
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const campo = (nombre) => ({
    value: form[nombre],
    onChange: (e) => setForm({ ...form, [nombre]: e.target.value }),
  })

  const guardar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    const body = {
      razon_social: form.razon_social,
      rut: form.rut || null,
      contacto: form.contacto,
      email: form.email,
      telefono: form.telefono || null,
    }
    if (form.id_vendedor) body.id_vendedor = Number(form.id_vendedor)
    try {
      if (prospecto) await api(`/prospectos/${prospecto.id_prospecto}`, { method: 'PATCH', body })
      else {
        if (form.monto_estimado !== '') body.monto_estimado = Number(form.monto_estimado)
        await api('/prospectos', { method: 'POST', body })
      }
      onListo(prospecto ? 'Cambios guardados.' : 'Prospecto creado. Ya aparece en el pipeline comercial.')
    } catch (err) {
      setError(err.message)
      setEnviando(false)
    }
  }

  return (
    <Modal titulo={prospecto ? 'Editar prospecto' : 'Nuevo prospecto'} onCerrar={onCerrar}>
      <form onSubmit={guardar} className="space-y-4">
        <Aviso>{error}</Aviso>
        <Campo etiqueta="Empresa o institución">
          <input className="campo" required maxLength={150} {...campo('razon_social')} />
        </Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Persona de contacto">
            <input className="campo" required maxLength={100} {...campo('contacto')} />
          </Campo>
          <Campo etiqueta="Correo de contacto">
            <input className="campo" type="email" required maxLength={120} {...campo('email')} />
          </Campo>
          <Campo etiqueta="Teléfono (opcional)">
            <input className="campo" maxLength={20} {...campo('telefono')} />
          </Campo>
          <Campo etiqueta="RUT (opcional)">
            <input className="campo" maxLength={12} {...campo('rut')} />
          </Campo>
        </div>
        {pideVendedor && (
          <Campo etiqueta="Vendedor responsable">
            <select className="campo" required {...campo('id_vendedor')}>
              <option value="">Elige un vendedor</option>
              {vendedores?.map((v) => (
                <option key={v.id_vendedor} value={v.id_vendedor}>
                  {v.nombre}
                </option>
              ))}
            </select>
          </Campo>
        )}
        {!prospecto && (
          <Campo etiqueta="Monto estimado del negocio (CLP)" ayuda="Abre una oportunidad en la primera etapa del pipeline.">
            <input className="campo" type="number" min="0" step="1000" required {...campo('monto_estimado')} />
          </Campo>
        )}
        <button type="submit" className="boton boton-primario w-full" disabled={enviando}>
          {enviando ? 'Guardando…' : prospecto ? 'Guardar cambios' : 'Crear prospecto'}
        </button>
      </form>
    </Modal>
  )
}

export default function Prospectos() {
  const { usuario } = useSesion()
  const { datos: prospectos, error, recargar } = useDatos('/prospectos')
  const { datos: vendedores } = useDatos('/vendedores')
  const [editando, setEditando] = useState(undefined)
  const [aviso, setAviso] = useState(null)

  const eliminar = async (p) => {
    if (!window.confirm(`¿Eliminar el prospecto ${p.razon_social}? Se borran también sus oportunidades.`)) return
    try {
      await api(`/prospectos/${p.id_prospecto}`, { method: 'DELETE' })
      setAviso({ tipo: 'ok', texto: 'Prospecto eliminado.' })
      recargar()
    } catch (e) {
      setAviso({ tipo: 'error', texto: e.message })
    }
  }

  return (
    <>
      <Encabezado titulo="Prospectos" detalle="Empresas e instituciones que todavía no son clientes.">
        <button type="button" className="boton boton-primario" onClick={() => setEditando(null)}>
          Nuevo prospecto
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

      {!prospectos && !error ? (
        <Cargando />
      ) : prospectos?.length === 0 ? (
        <p className="py-10 text-pizarra">Aún no hay prospectos. Crea el primero con «Nuevo prospecto».</p>
      ) : (
        <div className="caja overflow-x-auto">
          <table className="w-full min-w-[44rem] text-left">
            <thead className="text-sm text-pizarra">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Empresa</th>
                <th className="px-4 py-2.5 font-semibold">Contacto</th>
                <th className="px-4 py-2.5 font-semibold">Vendedor</th>
                <th className="px-4 py-2.5 font-semibold">Oportunidad</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {prospectos?.map((p) => (
                <tr key={p.id_prospecto} className="border-t border-hielo align-top">
                  <td className="px-4 py-3">
                    <p className="font-semibold">{p.razon_social}</p>
                    <p className="text-sm text-pizarra">{p.rut || 'Sin RUT'}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p>{p.contacto}</p>
                    <p className="text-sm text-pizarra">
                      {p.email}
                      {p.telefono && `, ${p.telefono}`}
                    </p>
                  </td>
                  <td className="px-4 py-3">{p.vendedor_nombre}</td>
                  <td className="px-4 py-3">
                    {p.oportunidades.length === 0 && <span className="text-pizarra">Sin oportunidad</span>}
                    {p.oportunidades.map((o) => (
                      <p key={o.id_oportunidad}>
                        {o.etapa}, <span className="cifra text-lg">{pesos(o.monto_estimado)}</span>
                      </p>
                    ))}
                    {p.id_cliente && <p className="text-sm font-semibold text-fresco">Ya es cliente</p>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button type="button" className="boton boton-linea boton-chico" onClick={() => setEditando(p)}>
                        Editar
                      </button>
                      <button type="button" className="boton boton-peligro boton-chico" onClick={() => eliminar(p)}>
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
          prospecto={editando}
          vendedores={vendedores}
          pideVendedor={!editando && usuario.rol === 'administrador'}
          onCerrar={() => setEditando(undefined)}
          onListo={(texto) => {
            setEditando(undefined)
            setAviso({ tipo: 'ok', texto })
            recargar()
          }}
        />
      )}
    </>
  )
}
