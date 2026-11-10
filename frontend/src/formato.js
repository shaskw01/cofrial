const clp = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 })
const grados = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 1 })

export const pesos = (n) => (n == null ? 'Sin precio' : clp.format(Number(n)))

// Signo menos tipografico para que las temperaturas negativas se lean bien
const numTemp = (n) => grados.format(Number(n)).replace('-', '−')
export const temp = (n) => `${numTemp(n)} °C`
export const rangoTemp = (min, max) => `${numTemp(min)} a ${temp(max)}`

export const esCongelado = (categoria) => Number(categoria.temp_max) <= -10
export const zona = (categoria) => (esCongelado(categoria) ? 'Congelado' : 'Refrigerado')

export const fecha = (iso) =>
  new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString('es-CL', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

export const fechaHora = (iso) =>
  new Date(iso).toLocaleString('es-CL', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })

export const fechaISO = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)

export const haceCuanto = (iso) => {
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (s < 60) return `hace ${s} s`
  if (s < 3600) return `hace ${Math.round(s / 60)} min`
  if (s < 86400) return `hace ${Math.round(s / 3600)} h`
  return `hace ${Math.round(s / 86400)} d`
}

export const unidad = (u, n = 1) => {
  if (u === 'kg') return 'kg'
  if (u === 'caja') return n === 1 ? 'caja' : 'cajas'
  return n === 1 ? 'unidad' : 'unidades'
}
