# Test on real hardware

### 11. Right in Chrome, wrong on phone

None of the fixes in this skill reproduce in device emulation. Sticky hover, the tap highlight, the URL bar's effect on `vh`, input zoom, the click delay, overscroll, safe areas, the software keyboard — every one is a real-hardware behavior.

- Connect the phone over USB, run the dev server on `0.0.0.0`, open it by the machine's LAN IP.
- iOS: Safari → Develop → the device. Android: `chrome://inspect`.
- Test on a phone that's a few years old, not the newest one on your desk. Test with the keyboard open. Test in landscape once.
- Test as an installed PWA if that's a target; standalone mode changes viewport, safe areas, and status bar behavior.

The Xcode Simulator is a step up from emulation but still misses touch feel. Real hardware is the bar.

