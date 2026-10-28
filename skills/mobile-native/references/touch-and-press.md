# Touch and press fixes

### 1. Hover state stuck after tap

Touch has no hover, so browsers fake one: the first tap on an element applies `:hover` and leaves it there until the user taps somewhere else. A button that scales up on hover stays scaled up after being tapped. Gate every hover style behind a capability query.

```css
@media (hover: hover) and (pointer: fine) {
  .button:hover {
    background: var(--gray-3);
    transform: scale(1.02);
  }
}
```

Both conditions matter. `(hover: hover)` means the primary input can hover. `(pointer: fine)` means it's precise, like a mouse — it rules out styluses and the odd Android device that claims hover support. In Tailwind v4 the `hover:` variant already compiles to `@media (hover: hover)`; in v3 set `future.hoverOnlyWhenSupported`.

Touch users still need press feedback. Give it to them through `:active` (see §5), which works on every input type.

### 2. Gray/blue flash on tap

iOS Safari and Android Chrome paint a translucent highlight over any tapped element that has a click handler. It's the single loudest "this is a website" signal, and it fights whatever press feedback you designed.

```css
html {
  -webkit-tap-highlight-color: transparent;
}
```

Set it once, globally. Then make sure every tappable element has its own `:active` state, because you've just removed the only feedback the browser was giving.

### 5. Tap feels laggy

Two separate causes stack here.

**The 300ms click delay.** Browsers wait after a tap to see whether a second tap is coming, because double-tap zooms. Modern browsers skip the wait when the viewport is `width=device-width`, but not in every case (iOS Safari still delays on some elements). `touch-action: manipulation` tells the browser this element never double-tap-zooms, so it fires `click` immediately:

```css
button, a, [role="button"], .tappable {
  touch-action: manipulation;
}
```

**Feedback on release instead of press.** Native buttons respond the instant your finger lands. A web button that only changes on `click` responds when your finger *leaves*, which reads as lag even at 0ms. Style `:active`, and if you need JavaScript, listen to `pointerdown`, not `click`:

```css
.button {
  transition: transform 100ms var(--ease-out), background 100ms;
}
.button:active {
  transform: scale(0.97);
  background: var(--gray-4);
}
```

Press feedback lasts 100-160ms with `ease-out`. If the codebase has motion tokens, use them; don't fork a new curve.

### 8. Long-press selects button text

Hold a finger on a web button and iOS selects its label, or pops the copy/share callout on a link. Native controls never do that. Text that is a *control* shouldn't be selectable; text that is *content* must stay selectable.

```css
button, [role="button"], .tab, .chip, .drag-handle {
  user-select: none;
  -webkit-user-select: none;   /* Safari still needs the prefix */
  -webkit-touch-callout: none; /* no long-press callout on links/images used as controls */
}
```

Never put `user-select: none` on `body`. Users copy addresses, error messages, and order numbers; that is content.

### 9. Carousel scrolls vertically

A horizontal swipe on a carousel is ambiguous to the browser — it doesn't know whether you're scrolling the page or the track, so it guesses, and the guess is often the page jittering up while the carousel moves. Tell it which axes the element owns:

```css
.carousel {
  touch-action: pan-y; /* the carousel handles horizontal; the browser keeps vertical */
}
.drag-surface {
  touch-action: none;  /* a custom gesture (a drag-to-dismiss sheet, a slider) owns every axis */
}
.vertical-sheet-handle {
  touch-action: pan-x; /* the sheet handles vertical drags; horizontal stays with the browser */
}
```

The values name what the *browser* may still do. `pan-y` on a horizontal carousel means "browser, you keep vertical panning; I'm handling horizontal". `none` means the element handles everything — use it only on elements that really do, or the user won't be able to scroll past them.

If the carousel is native scroll rather than a JS gesture, prefer `scroll-snap-type: x mandatory` on the track and `scroll-snap-align: start` on slides — the browser's own physics beat a hand-rolled spring, and `touch-action` becomes unnecessary.

