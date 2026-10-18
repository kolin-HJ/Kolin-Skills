export function writeJson(value) {
  return new Promise((resolve) => {
    process.stdout.write(`${JSON.stringify(value)}\n`, () => resolve());
  });
}
