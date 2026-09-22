# Optional modules

FIA Core is deliberately small. These modules are available separately and are
off by default. Enabling one records only a local preference in
`.fia/modules.json`; it does not add mandatory gates to Core.

```text
fia module list
fia module enable security
fia module enable ui
fia module info ui
fia module disable security
```

Most modules are intentionally light. UI is the exception: it keeps the complete
visual identity workflow from FIA Harness, including Design DNA, divergent
directions, section recipes and asset guidance.

Each folder is a capability pack, not a phase in a bureaucracy. A project can use
zero, one or several packs.
