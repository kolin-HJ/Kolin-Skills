---
name: ui-bar
description: Kolin's UI and UX quality bar. Use whenever building, editing or reviewing React, Next.js or Shopify UI components, pages, layouts, tables, forms, modals, drawers or responsive styles.
---

# UI bar

Applies to every repo with a UI.

- Desktop and phone both look clean and professional. Prove changes with screenshots at 390 px and 1440 px, zero horizontal scroll, and tap targets of at least 44 x 44 px.
- A screen's primary action (checkout, add to bag, save, submit) stays visible and reachable on a short phone, with the keyboard open, with browser toolbars shown and inside safe areas, and every modal or slide-out panel keeps a reachable close button. A change to a sticky bar or checkout needs a real iPhone Safari check.
- A data table never shrinks onto a phone: below 768 px it renders designed cards from the same row type and column definitions. Charts get a simple form on phones.
- Colors come from design tokens only—never raw hex or rgb values in components. Theme every third-party library to the tokens behind one wrapper.
- Library picks: AG Grid and AG Charts Community behind one wrapper (Enterprise needs Kolin's yes), shadcn on Base UI for web apps, Polaris web components for Shopify embedded apps; cmdk, Sonner, input-otp, motion (springs/layout/exit; plain CSS for hover/fade), NumberFlow, dnd kit, Virtuoso, zustand, clsx + cva, next-themes.
- Craft bar: Linear (status chips on dense lists), Stripe (plain error reason + one Retry), Vercel (status, last sync time, logs per connection), Shopify admin (cards and health home), Mercury (calm finance screens).
