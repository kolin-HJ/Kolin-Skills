import type { RenderElement } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

const STOCK: RenderElement = { type: 'Text', props: {}, children: ['band below'] }

const BAND = {
  plugin: 'savvy-progress',
  viewport: { columns: 100, rows: 30 },
  surface: 'terminal',
  component: 'AbovePrompt',
  requestId: 'band',
  props: { hasSurvey: false, isWorking: false, maxRows: 4, bodyColumns: 100, scroll: { offset: 0, bodyRows: 4 }, view: {} },
} as const

test('the progress bar draws above the band beneath it, not instead of it', async ($, on) => {
  mock.clock(on, { now: 10_000 })
  on('ui.render', () => STOCK)
  on('settings.read', () => ({ value: {} }))
  on('env.get', () => ({ value: undefined }))
  on('tool.register', () => ({ value: { tool: 'x' } }))
  on('command.register', () => ({ value: { command: 'agents-info' } }))
  on('session.start', () => ({ cwd: '/work' }))

  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })
  await $.tool.call({ tool: 'mcp__savvy-progress__progress', title: 'ZZ demo', total: 4, done: 1, phase: 'delegate' })

  const band = await $.ui.mount(BAND)
  expect(await band.find({ type: 'Text', text: 'band below' })).toBeDefined()
  expect(await band.find({ key: 'savvy-agents' })).toBeDefined()
  expect(await band.find({ type: 'Text', text: 'band below' })).toBeDefined()
})
