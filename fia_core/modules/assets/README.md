# Assets module

Optional verified manifests for images, fonts and other files. Downloads are
explicit and SHA-256 checked; hosting and licensing remain project concerns.

```text
fia assets fetch [url|manifiesto]   # download + verify (default: UI_ASSETS.json)
fia assets manifest --dir-source DIR --base-url URL   # build a manifest to publish
```

The UI pack uses the same mechanism (`fia ui setup`); see
`docs/fia/ui/UI_ASSETS.md` after enabling the UI module.
