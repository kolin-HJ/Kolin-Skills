import type { DiffArea } from '../types'

export const MOCHA = {
  green: '#a6e3a1',
  yellow: '#f9e2af',
  red: '#f38ba8',
  text: '#cdd6f4',
  subtext: '#a6adc8',
  overlay: '#7f849c',
  surface: '#313244',
  mauve: '#cba6f7',
} as const

export const NET_WARN = 200
export const NET_ALARM = 800

export type Gauge = { label: string; value: string; detail?: string; percent?: number }

export type DiffSummary = {
  base: string
  files: number
  added: number
  deleted: number
  areas: { area: DiffArea; net: number }[]
}

const FONT = `ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Inter, sans-serif`
const HEIGHT = 48
const MID = HEIGHT / 2
const RING_R = 11
const RING_STROKE = 3.5
const RING_TEXT_GAP = 12
const GROUP_GAP = 32
const CHIP_GAP = 8
const CHIP_H = 22
const CHIP_PAD = 10
const VALUE_SIZE = 13
const LABEL_SIZE = 11

export const heat = (percent: number) => (percent >= 90 ? MOCHA.red : percent >= 70 ? MOCHA.yellow : MOCHA.mauve)

export const netColor = (net: number) =>
  net <= 0 ? MOCHA.green : net >= NET_ALARM ? MOCHA.red : net >= NET_WARN ? MOCHA.yellow : MOCHA.text

export const signed = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `−${-n}` : '0')

const textWidth = (text: string, size: number) => Math.ceil(text.length * size * 0.54)

const escape = (text: string) => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

type Piece = { width: number; draw: (x: number) => string }

const gaugePiece = (gauge: Gauge): Piece => {
  const label = gauge.detail === undefined ? gauge.label : `${gauge.label}  ·  ${gauge.detail}`
  const textW = Math.max(textWidth(gauge.value, VALUE_SIZE), textWidth(label, LABEL_SIZE))
  const ringW = RING_R * 2 + RING_STROKE

  return {
    width: ringW + RING_TEXT_GAP + textW,
    draw: x => {
      const cx = x + ringW / 2
      const circumference = 2 * Math.PI * RING_R
      const filled = gauge.percent === undefined ? 0 : (circumference * Math.min(gauge.percent, 100)) / 100
      const tx = x + ringW + RING_TEXT_GAP

      return [
        `<circle cx="${cx}" cy="${MID}" r="${RING_R}" fill="none" stroke="${MOCHA.overlay}" stroke-opacity=".28" stroke-width="${RING_STROKE}"/>`,
        filled === 0
          ? ''
          : `<circle class="fill" cx="${cx}" cy="${MID}" r="${RING_R}" fill="none" stroke="${heat(gauge.percent ?? 0)}" stroke-width="${RING_STROKE}" stroke-linecap="round" stroke-dasharray="${filled.toFixed(2)} ${circumference.toFixed(2)}" transform="rotate(-90 ${cx} ${MID})"/>`,
        `<text x="${tx}" y="${MID - 3}" class="value">${escape(gauge.value)}</text>`,
        `<text x="${tx}" y="${MID + 13}" class="label">${escape(label)}</text>`,
      ].join('')
    },
  }
}

const dividerPiece: Piece = {
  width: 1,
  draw: x => `<line x1="${x + 0.5}" y1="10" x2="${x + 0.5}" y2="${HEIGHT - 10}" stroke="${MOCHA.overlay}" stroke-opacity=".35"/>`,
}

const diffPiece = (diff: DiffSummary): Piece => {
  const added = `+${diff.added}`
  const deleted = ` −${diff.deleted}`
  const net = diff.added - diff.deleted
  const netText = signed(net)
  const top = `${added}${deleted}   net ${netText}`
  const bottom = `vs ${diff.base}  ·  ${diff.files} ${diff.files === 1 ? 'file' : 'files'}`

  return {
    width: Math.max(textWidth(top, VALUE_SIZE), textWidth(bottom, LABEL_SIZE)),
    draw: x =>
      [
        `<text x="${x}" y="${MID - 3}" class="value">`,
        `<tspan fill="${MOCHA.green}">${added}</tspan>`,
        `<tspan fill="${MOCHA.red}">${deleted}</tspan>`,
        `<tspan class="muted" font-weight="400">   net </tspan>`,
        `<tspan fill="${netColor(net)}">${netText}</tspan>`,
        `</text>`,
        `<text x="${x}" y="${MID + 13}" class="label">${escape(bottom)}</text>`,
      ].join(''),
  }
}

const chipPiece = (area: DiffArea, net: number): Piece => {
  const value = signed(net)
  const width = CHIP_PAD * 2 + textWidth(`${area} ${value}`, LABEL_SIZE)

  return {
    width,
    draw: x =>
      [
        `<rect x="${x}" y="${MID - CHIP_H / 2}" width="${width}" height="${CHIP_H}" rx="${CHIP_H / 2}" fill="${MOCHA.surface}"/>`,
        `<text x="${x + CHIP_PAD}" y="${MID + 4}" class="label">${area} <tspan fill="${MOCHA.mauve}" font-weight="600">${value}</tspan></text>`,
      ].join(''),
  }
}

const widthOf = (pieces: Piece[][]) =>
  pieces.reduce((sum, group, i) => sum + (i === 0 ? 0 : GROUP_GAP) + group.reduce((w, p, j) => w + (j === 0 ? 0 : CHIP_GAP) + p.width, 0), 0)

export function bandSvg(gauges: Gauge[], diff: DiffSummary | null, maxWidth: number) {
  const meters: Piece[][] = gauges.map(gauge => [gaugePiece(gauge)])
  const withDiff = diff === null ? [] : [[dividerPiece], [diffPiece(diff)]]
  const chips = diff === null || diff.areas.length === 0 ? [] : [diff.areas.map(({ area, net }) => chipPiece(area, net))]

  const layouts = [[...meters, ...withDiff, ...chips], [...meters, ...withDiff], meters]
  const groups = layouts.find(layout => widthOf(layout) <= maxWidth) ?? meters
  const width = Math.max(1, widthOf(groups))

  let x = 0
  const body = groups
    .map((group, i) => {
      if (i > 0) x += GROUP_GAP
      return group
        .map((piece, j) => {
          if (j > 0) x += CHIP_GAP
          const drawn = piece.draw(x)
          x += piece.width
          return drawn
        })
        .join('')
    })
    .join('')

  const style = [
    `text{font-family:${FONT}}`,
    `.value{font-size:${VALUE_SIZE}px;font-weight:600;fill:${MOCHA.text};font-variant-numeric:tabular-nums}`,
    `.label{font-size:${LABEL_SIZE}px;fill:${MOCHA.overlay};letter-spacing:.02em}`,
    `.muted{fill:${MOCHA.overlay}}`,
    '.fill{animation:fill .9s cubic-bezier(.2,.8,.2,1)}',
    '@keyframes fill{from{stroke-dasharray:0 100}}',
    '@media (prefers-reduced-motion:reduce){.fill{animation:none}}',
  ].join('')

  const alt = [
    ...gauges.map(g => `${g.label} ${g.value}${g.detail === undefined ? '' : `, ${g.detail}`}`),
    ...(diff === null ? [] : [`diff vs ${diff.base}: +${diff.added} −${diff.deleted}, ${diff.files} files`]),
  ].join('; ')

  return {
    source: `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${HEIGHT}" viewBox="0 0 ${width} ${HEIGHT}"><style>${style}</style>${body}</svg>`,
    width,
    height: HEIGHT,
    alt,
  }
}
