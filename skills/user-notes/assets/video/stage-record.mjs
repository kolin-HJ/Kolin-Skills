#!/usr/bin/env node
import { spawnSync } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { setTimeout as sleep } from 'node:timers/promises'
import { parseArgs } from 'node:util'
import { launch } from './browser.mjs'

const usage = 'usage: node scripts/stage-record.mjs <preview url> <example> --seconds <s> --out <file.mp4> [--width 960] [--scale 2]'
const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    seconds: { type: 'string' },
    out: { type: 'string' },
    width: { type: 'string', default: '960' },
    scale: { type: 'string', default: '2' },
  },
})
if (positionals.length !== 2 || !values.seconds || !values.out) {
  console.error(usage)
  process.exit(2)
}
const [base, example] = positionals
const seconds = Number(values.seconds)
const width = Number(values.width)
const scale = Number(values.scale)
const out = resolve(values.out)

const browser = await launch()
const page = await browser.newPage({ viewport: { width, height: 1600 }, deviceScaleFactor: scale })
const problems = []
page.on('pageerror', (error) => problems.push(error.message))
page.on('console', (message) => { if (message.type() === 'error') problems.push(message.text()) })

const until = async (check, what) => {
  for (let tries = 0; tries < 300; tries += 1) {
    if (await page.evaluate(check)) return
    await sleep(50)
  }
  console.error(`${example}: timed out waiting for ${what}`)
  process.exit(1)
}

await page.addInitScript(() => window.addEventListener('message', (event) => {
  if (event.data?.type === 'stageshow:status' && 'ready' in event.data) window.__recordReady = event.data
}))
await page.goto(`${base.replace(/\/$/, '')}/?embed=${encodeURIComponent(example)}`)
await until(() => Boolean(window.__stageshow?.clock), 'the stage clock')
await page.evaluate(() => window.postMessage({ type: 'stageshow:control', playing: false, visible: true }, location.origin))
await until(() => Boolean(window.__recordReady), 'the ready signal')
const ready = await page.evaluate(() => window.__recordReady)
if (!ready.ready) {
  console.error(`${example} did not load: ${ready.error}`)
  process.exit(1)
}
await until(() => !window.__stageshow.clock.layoutPending && !document.querySelector('#example [data-placing]'), 'layout to settle')

const fps = await page.evaluate(() => window.__stageshow.clock.fps)
const frames = Math.round(seconds * fps)
const stage = page.locator('#example .ss-stage:visible').first()
const dir = mkdtempSync(join(tmpdir(), 'stage-record-'))
for (let frame = 0; frame < frames; frame += 1) {
  await stage.screenshot({ path: join(dir, `f${String(frame).padStart(5, '0')}.png`), animations: 'allow' })
  await page.evaluate(() => window.__stageshow.clock.step(1))
}
await browser.close()

const ffmpeg = spawnSync('ffmpeg', [
  '-y', '-loglevel', 'error', '-framerate', String(fps), '-i', join(dir, 'f%05d.png'),
  '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', out,
], { stdio: 'inherit' })
rmSync(dir, { recursive: true, force: true })
if (ffmpeg.status !== 0) process.exit(ffmpeg.status ?? 1)
if (problems.length > 0) {
  console.error(`${example} logged errors while recording:\n${problems.join('\n')}`)
  process.exit(1)
}
console.log(`${out} ${frames} frames at ${fps} fps`)
