import type { RenderElement } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

const STOCK: RenderElement = { type: 'Text', props: {}, children: ['stock band'] }

const BAND = (surface: 'desktop' | 'terminal') =>
  ({
    plugin: 'usage-band',
    viewport: { columns: 100, rows: 30 },
    surface,
    component: 'AbovePrompt',
    requestId: 'band',
    props: { hasSurvey: false, isWorking: false, maxRows: 4, bodyColumns: 100, scroll: { offset: 0, bodyRows: 4 }, view: {} },
  }) as const

test('the desktop band draws context, limits and the diff as one card above the stock band', async ($, on) => {
  mock.clock(on, { now: 10_000 })
  on('ui.render', () => STOCK)
  on('session.cwd', () => ({ value: '/work' }))
  on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200000, tokens: 50000, percent: 25 }, rateLimits: [] } }))
  on('process.run', ($, e) => {
    const argv = e.argv.join(' ')
    if (argv.startsWith('git rev-parse')) return { value: { exitCode: 0, stdout: 'abc\n', stderr: '' } }
    if (argv.startsWith('git merge-base')) return { value: { exitCode: 0, stdout: 'abc\n', stderr: '' } }
    if (argv.startsWith('git diff')) return { value: { exitCode: 0, stdout: '10\t2\tsrc/a.ts\n4\t0\tsrc/a.test.ts\n', stderr: '' } }
    return { value: { exitCode: 0, stdout: '', stderr: '' } }
  })
  on('session.start', () => ({ cwd: '/work' }))

  await $.session.start({ surface: 'desktop', isInteractive: true, cwd: '/work' })

  const band = await $.ui.mount(BAND('desktop'))
  const svg = (await band.find({ type: 'Svg' })) as { props: { alt: string; source: string } } | undefined
  expect(svg?.props.alt).toBe('Context 50k / 200k, 25%; Session –; Week –; diff vs staging: +14 −2, 2 files')
  expect(svg?.props.source).toContain('tests <tspan')
  expect(await band.find({ type: 'Text', text: 'stock band' })).toBeDefined()
  expect(await band.find({ type: 'Button' })).toBeUndefined()
})
