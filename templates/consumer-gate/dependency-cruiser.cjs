module.exports = {
  forbidden: [
    {
      name: "no-circular",
      comment: "A cycle hides the owner of a module.",
      severity: "error",
      from: {},
      to: { circular: true },
    },
    {
      name: "data-never-imports-features",
      comment: "The data layer never imports feature code.",
      severity: "error",
      from: { path: "^src/(data|foundation|db)/" },
      to: { path: "^src/features/" },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
  },
};
