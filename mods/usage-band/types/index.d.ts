export type UsageLimit = { kind: string; percentUsed: number; resetsAt?: string }

export type Usage = {
  contextTokens?: number
  contextWindow: number
  rateLimits: UsageLimit[]
}

export type DiffArea = 'app' | 'tests' | 'docs' | 'gates'

export type AreaCount = { added: number; deleted: number }

export type Diff = {
  base: string
  files: number
  areas: Record<DiffArea, AreaCount>
}

declare module 'claude-code' {
  interface PluginState {
    'usage-band': { usage: Usage | null; diff: Diff | null }
  }
}
