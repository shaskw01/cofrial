import { useEffect, useRef } from 'react'

export function Logo({ claro = false }) {
  return (
    <span className={`inline-flex items-center gap-2 ${claro ? 'text-white' : 'text-camara'}`}>
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden="true">
        <rect width="32" height="32" rx="6" fill={claro ? '#ffffff' : '#0F2B3D'} />
        <path
          d="M16 6v20M7.3 11l17.4 10M24.7 11L7.3 21"
          stroke={claro ? '#0F2B3D' : '#BFE0F2'}
          strokeWidth="2.4"
          strokeLinecap="round"
        />
      </svg>
      <span className="font-rotulo text-2xl leading-none font-bold tracking-wide">Cofrial</span>
    </span>
  )
}

const ESTILO_ESTADO = {
  Recibido: 'bg-glaciar-suave text-glaciar',
  'En preparación': 'bg-ambar-suave text-ambar',
  Despachado: 'bg-fresco-suave text-fresco',
  Entregado: 'bg-camara text-white',
  Rechazado: 'bg-ruptura-suave text-ruptura',
}

export function Estado({ nombre }) {
  return (
    <span
      className={`inline-block rounded-sm px-2 py-0.5 text-sm font-semibold whitespace-nowrap ${ESTILO_ESTADO[nombre] || 'bg-escarcha text-pizarra'}`}
    >
      {nombre}
    </span>
  )
}

export function Aviso({ tipo = 'error', children, onCerrar }) {
  if (!children) return null
  const estilo =
    tipo === 'error'
      ? 'border-ruptura bg-ruptura-suave text-ruptura'
      : tipo === 'ok'
        ? 'border-fresco bg-fresco-suave text-[#0b5e59]'
        : 'border-glaciar bg-glaciar-suave text-glaciar'
  return (
    <div role={tipo === 'error' ? 'alert' : 'status'} className={`flex items-start gap-3 rounded border-l-4 px-4 py-3 ${estilo}`}>
      <div className="flex-1">{children}</div>
      {onCerrar && (
        <button type="button" onClick={onCerrar} className="font-semibold underline">
          Cerrar
        </button>
      )}
    </div>
  )
}

export function Campo({ etiqueta, ayuda, children, className = '' }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-sm font-semibold">{etiqueta}</span>
      {children}
      {ayuda && <span className="mt-1 block text-sm text-pizarra">{ayuda}</span>}
    </label>
  )
}

export function Modal({ titulo, onCerrar, children, ancho = 'max-w-lg' }) {
  const ref = useRef(null)
  useEffect(() => {
    const dialogo = ref.current
    if (dialogo && !dialogo.open) dialogo.showModal()
  }, [])
  return (
    <dialog
      ref={ref}
      onClose={onCerrar}
      onClick={(e) => e.target === ref.current && onCerrar()}
      className={`m-auto w-[calc(100%-2rem)] ${ancho} rounded-md bg-white p-0 text-camara shadow-xl backdrop:bg-camara/50`}
    >
      <div className="flex items-start justify-between gap-4 border-b border-hielo px-5 py-4">
        <h2 className="text-2xl">{titulo}</h2>
        <button type="button" onClick={onCerrar} className="boton boton-linea boton-chico">
          Cerrar
        </button>
      </div>
      <div className="max-h-[75vh] overflow-y-auto px-5 py-4">{children}</div>
    </dialog>
  )
}

export function Cantidad({ valor, onCambiar, max, etiqueta }) {
  const fijar = (n) => onCambiar(Math.max(0, Math.min(max ?? Infinity, n)))
  return (
    <div className="inline-flex items-stretch rounded border border-hielo bg-white" role="group" aria-label={etiqueta}>
      <button type="button" className="w-9 text-lg font-semibold hover:bg-escarcha" onClick={() => fijar(valor - 1)} aria-label="Quitar uno">
        −
      </button>
      <input
        className="cifra w-12 border-x border-hielo text-center text-lg [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
        type="number"
        min="0"
        max={max}
        value={valor}
        onChange={(e) => fijar(parseInt(e.target.value, 10) || 0)}
        aria-label="Cantidad"
      />
      <button
        type="button"
        className="w-9 text-lg font-semibold hover:bg-escarcha disabled:opacity-40"
        onClick={() => fijar(valor + 1)}
        disabled={max != null && valor >= max}
        aria-label="Agregar uno"
      >
        +
      </button>
    </div>
  )
}

export function Cargando({ texto = 'Cargando…' }) {
  return <p className="py-10 text-center text-pizarra">{texto}</p>
}
