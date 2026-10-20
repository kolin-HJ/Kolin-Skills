# UI bar

Part of `foundation`. Applies to every repo with a UI.

- Desktop and phone both look clean and professional. Prove it with screenshots at 390 px and 1440 px, no horizontal scroll, and tap targets of at least 44 x 44 px.
- A data table never shrinks onto a phone: below 768 px it renders designed cards from the same row type and column definitions. Charts get a simple form on phones.
- Colors come from design tokens only. A lint rule bans raw hex and rgb values in components. Every library is themed to the tokens.
- Kolin's library picks: AG Grid and AG Charts Community behind one wrapper (Enterprise needs his yes), shadcn on Base UI for web apps, Polaris web components for Shopify embedded apps. For the rest: cmdk (command menus), Sonner (toasts), input-otp, motion (springs, layout and exit animation; plain CSS for a hover or fade), NumberFlow (animated numbers), dnd kit, Virtuoso (long lists), zustand (shared state), clsx and cva (class names and variants), next-themes. Craft: `emil-design-eng`, `break-ui`, `mobile-native`.
- Inspiration: Linear (status chips on dense lists), Stripe (an error with a plain reason and one Retry), Vercel (status, last sync time and logs per connection), Shopify admin (cards and a health home page), Mercury (calm finance screens).

