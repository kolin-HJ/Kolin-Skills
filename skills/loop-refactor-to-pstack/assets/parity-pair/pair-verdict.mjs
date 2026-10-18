export function related(a, b) {
  return a === b || a.startsWith(`${b}.`) || b.startsWith(`${a}.`);
}

export function featureOf(at, names) {
  const key = at.startsWith("deep.") ? at.slice(5) : at;
  return names.find(
    (name) => key === name || key.startsWith(`${name}.`) || key.startsWith(`${name} `)
  );
}

export function candidates(report) {
  return [...(report.changes ?? []), ...(report.unsettled ?? [])].map((change) => change.at);
}

export function headOnlyErrors(report, names) {
  const baseOwners = new Set(
    (report.against ?? []).flatMap((baseline) => baseline.errors).map((at) => featureOf(at, names))
  );
  return report.errors.filter((at) => {
    const owner = featureOf(at, names);
    return owner === undefined || !baseOwners.has(owner);
  });
}

export function featuresToRecheck(report, names) {
  const failing = [
    ...candidates(report),
    ...report.errors,
    ...(report.against ?? []).flatMap((baseline) => baseline.errors),
  ];
  const owners = failing.map((at) => featureOf(at, names));
  return owners.includes(undefined) ? null : [...new Set(owners)];
}

export function verdict(firstAts, secondAts) {
  const changes = secondAts.filter((at) => firstAts.some((other) => related(at, other)));
  return {
    changes,
    onlyInPass2: secondAts.filter((at) => !changes.includes(at)),
    driftCleared: firstAts.filter((at) => !secondAts.some((other) => related(at, other))),
  };
}

export function merge(parts) {
  const observed = { head: parts[0].head, at: parts[0].at, ms: {}, features: {}, deep: {} };
  const moved = new Set();
  for (const part of parts) {
    Object.assign(observed.ms, part.ms);
    Object.assign(observed.features, part.features);
    Object.assign(observed.deep, part.deep);
    for (const table of part.worldChanged ?? []) moved.add(table);
  }
  if (moved.size) observed.worldChanged = [...moved];
  return observed;
}
