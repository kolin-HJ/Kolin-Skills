# Debugging animations

Play the animation at 2-5x duration, or slow it in the DevTools Animations panel, and step through it frame by frame. Look for these:

- Two distinct states overlapping instead of a smooth color change.
- An abrupt start or stop, or a wrong `transform-origin`.
- Animated properties (opacity, transform, color) out of sync.
