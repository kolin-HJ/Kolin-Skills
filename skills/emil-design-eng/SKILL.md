---
name: emil-design-eng
description: "Motion and polish craft for web UI from Emil Kowalski: easing curves, durations, springs, enter and exit, gestures, transforms, clip-path, reduced motion. Use when you build or review an animation, transition, popover, drawer, toast or press state, or when asked to make UI feel polished. Not for stress data (break-ui) or phone tells (mobile-native)."
---

# Design Engineering

## Review Format (Required)

Report a review as one table: Before / After / Why

Check for:

| Issue | Fix |
| --- | --- |
| `transition: all` | Specify exact properties: `transition: transform 200ms ease-out` |
| `scale(0)` entry animation | Start from `scale(0.95)` with `opacity: 0` |
| `ease-in` on UI element | Switch to `ease-out` or custom curve |
| `transform-origin: center` on popover | Set to trigger location or use Base UI's `var(--transform-origin)` (modals are exempt: keep centered) |
| Animation on keyboard action | Remove animation entirely |
| Duration > 300ms on UI element | Reduce to 150-250ms |
| Hover animation without media query | Add `@media (hover: hover) and (pointer: fine)` |
| Keyframes on rapidly-triggered element | Use CSS transitions for interruptibility |
| Framer Motion `x`/`y` props under load | Use `transform: "translateX()"` for hardware acceleration |
| Same enter/exit transition speed | Make exit faster than enter (hold-to-delete: press slow, release 200ms) |
| Elements all appear at once | Add stagger delay (30-80ms between items) |

## The Animation Decision Framework

Before writing any animation code, answer these questions in order:

### 1. Should this animate at all?

**Ask:** How often will users see this animation?

| Frequency                                                   | Decision                     |
| ----------------------------------------------------------- | ---------------------------- |
| 100+ times/day (keyboard shortcuts, command palette toggle) | No animation. Ever.          |
| Tens of times/day (hover effects, list navigation)          | Remove or drastically reduce |
| Occasional (modals, drawers, toasts)                        | Standard animation           |
| Rare/first-time (onboarding, feedback forms, celebrations)  | Can add delight              |

**Never animate keyboard-initiated actions.** These actions are repeated hundreds of times daily. Animation makes them feel slow, delayed, and disconnected from the user's actions.

Raycast has no open/close animation. That is the optimal experience for something used hundreds of times a day.

### 2. What is the purpose?

Animate only for spatial consistency, state, explanation, feedback or to stop a jarring change. If it is decorative and seen often, do not.

### 3–4. Easing and duration

Read `references/easing-and-timing.md` before you pick a curve or a duration.

## Reference files

Read the file that matches the task. Each one holds detail that is not repeated here.

| File | Read when |
| --- | --- |
| `references/easing-and-timing.md` | You pick an easing curve or a duration |
| `references/springs.md` | The motion is a spring, drag with momentum, or mouse-tracking |
| `references/components.md` | You build a button, popover, tooltip, toast or enter state |
| `references/transforms-and-clip-path.md` | You use translate, scale, 3D, transform-origin or clip-path |
| `references/gestures.md` | You build swipe, drag or dismiss |
| `references/performance.md` | An animation drops frames, or you choose CSS, WAAPI or JS |
| `references/accessibility.md` | You handle reduced motion |
| `references/craft-principles.md` | You design a component's feel, stagger a list, or match motion to mood |
| `references/debugging-and-review.md` | You debug an animation in slow motion |
