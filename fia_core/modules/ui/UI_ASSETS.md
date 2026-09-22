# UI_ASSETS.md — Pack de assets UI

> El kit **no distribuye contenido de terceros**: lleva el *mecanismo* (manifiesto +
> descarga verificada). El *contenido* lo aloja quien tenga derechos (p. ej. un
> bucket de Supabase self-hosted, un GitHub Release o cualquier estático con HTTPS).

---

## 0. Pack oficial (mantenido por PGMIA)

Manifiesto:
`https://supabase.pgmia.es/storage/v1/object/public/fia-assets/UI_ASSETS.json`

Incluye los **media** de las recetas (`media/…`) y las **recetas** completas
(`library/UI_LIBRARY.md`). Con el módulo UI habilitado:

```text
fia ui setup            # pack completo (media + recetas)
fia ui setup --recetas  # solo las recetas (library/UI_LIBRARY.md)
fia ui status           # estado local sin red: completo / parcial / ausente
```

O directamente con el descargador de assets:

```text
fia assets fetch https://supabase.pgmia.es/storage/v1/object/public/fia-assets/UI_ASSETS.json
fia init --assets https://supabase.pgmia.es/storage/v1/object/public/fia-assets/UI_ASSETS.json
```

`fia ui setup` usa el pack oficial por defecto (override con `--url` o la variable
`FIA_UI_PACK_URL`) y guarda el manifiesto usado en el `UI_ASSETS.json` del proyecto.
El protocolo pide **confirmación humana** antes de instalarlo (Paso 0 de
`UI_UX_EXCLUSIVA.md` §8): nada se descarga sin tu OK.

- **Opt-in**: nada se descarga si no ejecutas el comando (sin llamadas por defecto).
- **Idempotente**: si el archivo ya existe y su hash coincide, no se toca.
- **Atómico**: se descarga a `.part`, se verifica y luego se mueve a su sitio.
- **Fail-closed**: si el SHA-256 no coincide, no se escribe nada.
- Los assets quedan **autohospedados** en el proyecto (lo que piden las recetas:
  nada de hotlinks en producción). Para no inflar el repo: `media/` puede ir a
  `.gitignore` o usar Git LFS según el peso.

## 1. Manifiesto `UI_ASSETS.json`

```json
{
  "version": 1,
  "assets": [
    {
      "path": "media/hero-aurora.mp4",
      "url": "https://cdn.ejemplo.com/fia-assets/v1/media/hero-aurora.mp4",
      "sha256": "<64 hex>"
    }
  ]
}
```

- `path`: ruta **relativa** dentro del proyecto (se rechazan absolutas y `..`).
- `url`: `http(s)://` o `file://` (para pruebas locales).
- `sha256`: hash del archivo; **fail-closed**: si no coincide, no se escribe nada.

## 2. Uso en un proyecto

```text
fia assets fetch                 # usa UI_ASSETS.json del proyecto
fia assets fetch https://cdn.ejemplo.com/fia-assets/v1/UI_ASSETS.json
fia init --assets https://cdn.ejemplo.com/fia-assets/v1/UI_ASSETS.json   # init + pack
```

## 3. Publicar un pack (mantenedor)

```text
fia assets manifest --dir-source ./pack --base-url https://cdn.ejemplo.com/fia-assets/v1
# -> UI_ASSETS.json con path/url/sha256 de cada archivo
```

Sube `pack/` y `UI_ASSETS.json` a tu hosting (bucket público o URLs firmadas) y
comparte la URL del manifiesto. **Licencia:** publica solo material que puedas
redistribuir; el kit no incluye media de terceros.

## 4. Seguridad

- Sin traversal: el manifiesto no puede escribir fuera del proyecto.
- Sin ejecución: solo se descargan datos; no hay scripts ni instalación.
- HTTPS recomendado para el hosting; `file://` solo para pruebas.
- El manifiesto **no está firmado** (v1): si el hosting se compromete, un manifiesto
  malicioso podría servir otros binarios *con su hash*; por eso el pack debe vivir
  en infraestructura propia y sobre HTTPS. La firma del manifiesto es trabajo futuro.
