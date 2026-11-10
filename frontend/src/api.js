const CLAVE = 'cofrial_token'
let token = localStorage.getItem(CLAVE)

export const hayToken = () => Boolean(token)

export function guardarToken(nuevo) {
  token = nuevo
  if (nuevo) localStorage.setItem(CLAVE, nuevo)
  else localStorage.removeItem(CLAVE)
}

const ETIQUETAS = {
  numero_oc: 'N.º de orden de compra',
  direccion_despacho: 'Dirección de despacho',
  direccion_entrega: 'Dirección de entrega',
  fecha_entrega_solicitada: 'Fecha de entrega',
  nombre_razon_social: 'Nombre o razón social',
  razon_social: 'Razón social',
  rut: 'RUT',
  email: 'Correo',
  telefono: 'Teléfono',
  camion_id: 'Camión',
  id_vendedor: 'Vendedor',
  monto_estimado: 'Monto estimado',
}

function mensajeDe(status, data) {
  if (!data || typeof data !== 'object') {
    return status >= 500 ? 'El servidor no pudo responder. Intenta de nuevo en unos segundos.' : `Error ${status}`
  }
  if (typeof data.detail === 'string') return data.detail
  const partes = []
  for (const [campo, valor] of Object.entries(data)) {
    const texto = Array.isArray(valor) ? valor.join(' ') : typeof valor === 'string' ? valor : JSON.stringify(valor)
    partes.push(campo === 'non_field_errors' ? texto : `${ETIQUETAS[campo] || campo}: ${texto}`)
  }
  return partes.join(' ') || `Error ${status}`
}

export class ApiError extends Error {
  constructor(status, data) {
    super(mensajeDe(status, data))
    this.status = status
    this.data = data
  }
}

export async function api(ruta, { method = 'GET', body, params } = {}) {
  let url = `/api${ruta}`
  if (params) {
    const limpio = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    )
    const qs = new URLSearchParams(limpio).toString()
    if (qs) url += `?${qs}`
  }
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let respuesta
  try {
    respuesta = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError(0, { detail: 'No hay conexión con el servidor. Revisa que el backend esté arriba.' })
  }
  if (respuesta.status === 204) return null
  const data = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    if (respuesta.status === 401 && token && ruta !== '/auth/login') {
      guardarToken(null)
      window.dispatchEvent(new Event('cofrial:sesion-vencida'))
    }
    throw new ApiError(respuesta.status, data)
  }
  return data
}
