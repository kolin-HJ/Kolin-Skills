---
name: mobile-native
description: Fix the small CSS and meta-tag tells that make a web app feel like a website on a phone: sticky hover, tap flash, 100vh, input zoom, laggy taps, overscroll, notch, status bar. Use when building or reviewing a phone layout, PWA, bottom sheet, carousel, full-screen screen or touch interaction, or when it "works in Chrome but feels wrong on my phone". Motion craft is emil-design-eng.
---

# Feeling Native On Mobile

Platform-layer fixes (viewport, touch, scroll, safe areas, browser chrome). Not motion, not React Native.

## Operating Posture

Two failure modes, and the first is worse:

1. **Fixing what the desktop shows you.** The bugs in this skill don't reproduce in Chrome's device emulation. If you only test there, you ship all of them.
2. **Reaching for JavaScript when CSS or a meta tag does it.** Almost every item here is one declaration. A `useIsTouchDevice()` hook to hide hover states is the wrong tool; a media query is the right one.

## Hard Rules

- Gate by capability (`hover`, `pointer`, `env()`, `dvh`), never by user agent or width; one device can have both touch and a mouse.
- Never disable zoom. `user-scalable=no` and `maximum-scale=1` are accessibility failures. Fix the input font size instead, which is what was causing the zoom.

## Symptom table

Match what you see, then read the reference file for the why and the exact code.

| Symptom | Never | Instead | Reference |
| --- | --- | --- | --- |
| Hover state stuck after tap | Ungated `:hover` | `@media (hover: hover) and (pointer: fine)` | `touch-and-press.md` |
| Gray/blue flash on tap | Leave the default highlight | `-webkit-tap-highlight-color: transparent` | `touch-and-press.md` |
| Layout has wrong height | `100vh` for an app shell or bottom-pinned UI | `100dvh` (app); `100svh` on a marketing hero (no layout shift on scroll) | `viewport-and-layout.md` |
| Page zooms into input | `user-scalable=no` or `maximum-scale=1` | Input font size 16px at the minimum | `viewport-and-layout.md` |
| Tap feels laggy | Press feedback on `click` only | `:active` / `pointerdown`, plus `touch-action: manipulation` | `touch-and-press.md` |
| Pull-to-refresh hijacks scroll | `touchmove` + `preventDefault()` | `overscroll-behavior: none` on `html, body` | `scroll-and-chrome.md` |
| Content stops at the notch | `env(safe-area-inset-*)` without `viewport-fit=cover` (the value is `0`) | `viewport-fit=cover` + `env(safe-area-inset-*)` | `viewport-and-layout.md` |
| Long-press selects button text | `user-select: none` on `body` | `user-select: none` on controls only | `touch-and-press.md` |
| Carousel scrolls vertically | `touch-action: none` on something the user must scroll past | `touch-action: pan-y` (or `pan-x`) on the gesture surface | `touch-and-press.md` |
| Status bar color doesn't match | One `theme-color` for both schemes | One `theme-color` per `prefers-color-scheme` | `scroll-and-chrome.md` |
| Right in Chrome, wrong on phone | Declare it fixed from device emulation | Real hardware | `hardware-testing.md` |

## Output

Say which fixes need a phone to confirm.

## Reference files

| File | Read when |
| --- | --- |
| `references/baseline.md` | You start a mobile-facing app |
