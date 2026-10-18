import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextUsage, SessionRateLimit } from 'claude-code'

import type { AreaCount, Diff, DiffArea, Usage, UsageLimit } from '../types'
import { bandSvg, heat, MOCHA, netColor, signed } from './band'
import type { DiffSummary, Gauge } from './band'

const usage = atom({ plugin: 'usage-band', key: 'usage' } as const, null)
const diff = atom({ plugin: 'usage-band', key: 'diff' } as const, null)

const AREAS: readonly DiffArea[] = ['app', 'tests', 'docs', 'gates']
const BASE_CANDIDATES = ['origin/staging', 'origin/HEAD', 'origin/main']
const EDITING_TOOLS = new Set(['Edit', 'Write', 'NotebookEdit', 'Bash'])

const areaOf = (file: string): DiffArea => {
  if (/\.(test|spec)\.[cm]?[jt]sx?$/.test(file)) return 'tests'
  if (/\.md$/.test(file) || file.startsWith('docs/')) return 'docs'
  if (/^(scripts|\.github|\.agents|\.claude|\.pstack)\//.test(file)) return 'gates'
  return 'app'
}

const emptyAreas = (): Record<DiffArea, AreaCount> => ({
  app: { added: 0, deleted: 0 },
  tests: { added: 0, deleted: 0 },
  docs: { added: 0, deleted: 0 },
  gates: { added: 0, deleted: 0 },
})

const readDiff = async ($: EngineInterface): Promise<Diff | null> => {
  const cwd = await $.session.cwd()
  const git = (...argv: string[]) => $.process.run(['git', ...argv], { cwd, timeoutMs: 10000 })

  let baseRef: string | undefined
  for (const candidate of BASE_CANDIDATES) {
    const probe = await git('rev-parse', '--verify', '--quiet', candidate)
    if (probe.exitCode === 0) {
      baseRef = candidate
      break
    }
  }
  if (baseRef === undefined) return null
  const mergeBase = await git('merge-base', baseRef, 'HEAD')
  if (mergeBase.exitCode !== 0) return null

  const [tracked, untracked] = await Promise.all([
    git('diff', '--numstat', mergeBase.stdout.trim()),
    $.process.run(
      ['sh', '-c', 'git ls-files -o --exclude-standard -z | xargs -0 -r wc -l'],
      { cwd, timeoutMs: 10000 },
    ),
  ])

  const areas = emptyAreas()
  let files = 0
  for (const line of tracked.stdout.split('\n')) {
    const [added, deleted, file] = line.split('\t')
    if (file === undefined || added === '-') continue
    const area = areas[areaOf(file)]
    area.added += Number(added)
    area.deleted += Number(deleted)
    files += 1
  }
  for (const line of untracked.stdout.split('\n')) {
    const [, count, file] = /^\s*(\d+)\s+(.+)$/.exec(line) ?? []
    if (count === undefined || file === undefined || file === 'total') continue
    areas[areaOf(file)].added += Number(count)
    files += 1
  }
  return { base: baseRef.replace(/^origin\//, ''), files, areas }
}

const refreshDiff = async ($: EngineInterface) => {
  const next = await readDiff($)
  await update($, diff, () => next)
}

const BAR_CELLS = 8

const toUsage = (context: SessionContextUsage, rateLimits: SessionRateLimit[]): Usage =>
  context.tokens === undefined
    ? { contextWindow: context.window, rateLimits }
    : { contextTokens: context.tokens, contextWindow: context.window, rateLimits }

const kilo = (tokens: number) => `${Math.round(tokens / 1000)}k`

const until = (resetsAt: string | undefined, now: number) => {
  if (resetsAt === undefined) return undefined
  const minutes = Math.max(0, Math.round((Date.parse(resetsAt) - now) / 60000))
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes % 60}m`
  return `${minutes}m`
}

const findLimit = (limits: UsageLimit[], kind: string) => limits.find(limit => limit.kind === kind)

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const result = await next(e)
    const { context, rateLimits } = await $.session.usage()
    await update($, usage, () => toUsage(context, rateLimits))
    await refreshDiff($)
    return result
  })

  on('tool.call', async ($, e, next) => {
    const result = await next(e)
    if (EDITING_TOOLS.has(e.tool)) await refreshDiff($)
    return result
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    await refreshDiff($)
    return result
  })

  on('session.measure', async ($, e, next) => {
    await update($, usage, () => toUsage(e.context, e.rateLimits))
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const current = await read($, usage)
    const changes = await read($, diff)
    if (e.props.hasSurvey || current === null) return next(e)
    const theirs = await next(e)

    const ui = $.ui.resolve(e)
    const { Box, Text } = ui
    const now = await $.clock.now()

    const contextPercent =
      current.contextTokens === undefined ? undefined : (current.contextTokens / current.contextWindow) * 100
    const limitGauge = (label: string, limit: UsageLimit | undefined): Gauge => {
      const left = until(limit?.resetsAt, now)
      return {
        label,
        value: limit === undefined ? '–' : `${Math.round(limit.percentUsed)}%`,
        ...(left === undefined ? {} : { detail: `resets in ${left}` }),
        ...(limit === undefined ? {} : { percent: limit.percentUsed }),
      }
    }
    const gauges: Gauge[] = [
      {
        label: 'Context',
        value:
          current.contextTokens === undefined
            ? `– / ${kilo(current.contextWindow)}`
            : `${kilo(current.contextTokens)} / ${kilo(current.contextWindow)}`,
        ...(contextPercent === undefined ? {} : { detail: `${Math.round(contextPercent)}%`, percent: contextPercent }),
      },
      limitGauge('Session', findLimit(current.rateLimits, 'five_hour')),
      limitGauge('Week', findLimit(current.rateLimits, 'seven_day')),
    ]

    const summary: DiffSummary | null =
      changes === null
        ? null
        : {
            base: changes.base,
            files: changes.files,
            added: AREAS.reduce((sum, area) => sum + changes.areas[area].added, 0),
            deleted: AREAS.reduce((sum, area) => sum + changes.areas[area].deleted, 0),
            areas: AREAS.filter(area => changes.areas[area].added + changes.areas[area].deleted > 0).map(area => ({
              area,
              net: changes.areas[area].added - changes.areas[area].deleted,
            })),
          }

    if ('Svg' in ui) {
      const { Svg } = ui
      const band = bandSvg(gauges, summary, Math.max(240, (e.props.bodyColumns || 100) * 8 - 48))
      return (
        <Box flexDirection="column" rowGap={1}>
          <Box paddingX={1} paddingY={1}>
            <Svg source={band.source} alt={band.alt} width={band.width} height={band.height} />
          </Box>
          {theirs}
        </Box>
      )
    }

    const meter = (gauge: Gauge) => {
      const filled = gauge.percent === undefined ? 0 : Math.round((Math.min(gauge.percent, 100) / 100) * BAR_CELLS)
      return (
        <Box key={gauge.label} flexDirection="row" gap={1}>
          <Text color={MOCHA.overlay}>{gauge.label}</Text>
          <Text>
            <Text color={gauge.percent === undefined ? MOCHA.overlay : heat(gauge.percent)}>{'▰'.repeat(filled)}</Text>
            <Text color={MOCHA.overlay}>{'▱'.repeat(BAR_CELLS - filled)}</Text>
          </Text>
          <Text color={MOCHA.text} bold>
            {gauge.value}
          </Text>
          {gauge.detail === undefined ? null : <Text color={MOCHA.overlay}>{gauge.detail}</Text>}
        </Box>
      )
    }

    const diffLine =
      summary === null ? null : (
        <Box key="diff" flexDirection="row" flexWrap="wrap" columnGap={3}>
          <Box flexDirection="row" gap={1}>
            <Text color={MOCHA.overlay}>vs {summary.base}</Text>
            <Text color={MOCHA.green}>+{summary.added}</Text>
            <Text color={MOCHA.red}>−{summary.deleted}</Text>
          </Box>
          <Text color={MOCHA.overlay}>
            net <Text color={netColor(summary.added - summary.deleted)} bold>{signed(summary.added - summary.deleted)}</Text>
          </Text>
          <Text color={MOCHA.overlay}>{summary.files} files</Text>
          {summary.areas.map(({ area, net }) => (
            <Text key={area} color={MOCHA.overlay}>
              {area} <Text color={MOCHA.mauve}>{signed(net)}</Text>
            </Text>
          ))}
        </Box>
      )

    return (
      <Box flexDirection="column">
        <Box flexDirection="column" paddingX={1} paddingY={1} rowGap={1}>
          <Box flexDirection="row" flexWrap="wrap" columnGap={4}>
            {gauges.map(meter)}
          </Box>
          {diffLine}
        </Box>
        {theirs}
      </Box>
    )
  })
}
