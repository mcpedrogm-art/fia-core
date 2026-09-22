"""FIA Core command line interface."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__, assets, modules, store, templates, ui
from .verify import status, verify


def _write_if_absent(path, content):
    if not path.exists():
        path.write_text(content, encoding="utf-8")
        return True
    return False


def _interactive_modules():
    print("\nMódulos opcionales (Enter = solo Core):")
    for index, (name, details) in enumerate(modules.MODULES.items(), start=1):
        print(f"  {index:>2}. {details['label']} [{name}] — {details['level']}")
    try:
        answer = input("Selecciona números o nombres separados por comas: ").strip()
    except EOFError:
        print("(sin entrada disponible: solo Core)")
        return []
    if not answer:
        return []
    choices = list(modules.MODULES)
    names = []
    for item in answer.split(","):
        item = item.strip().lower()
        if item.isdigit() and 1 <= int(item) <= len(choices):
            item = choices[int(item) - 1]
        names.append(item)
    return modules.normalize_names(",".join(names))


def init(root, with_spec=False, selected_modules=None, interactive=None, assets_ref=None):
    root = Path(root).resolve()
    if interactive is None:
        interactive = selected_modules is None and sys.stdin.isatty() and not (root / ".fia" / "modules.json").exists()
    if selected_modules is None:
        selected_modules = _interactive_modules() if interactive else []
    else:
        selected_modules = modules.normalize_names(selected_modules) if isinstance(selected_modules, str) else list(selected_modules)
    root.mkdir(parents=True, exist_ok=True)
    (root / ".fia").mkdir(exist_ok=True)
    (root / ".fia" / "tests").mkdir(exist_ok=True)
    created = []
    for name, content in (("PROJECT.md", templates.PROJECT), ("TASK.md", templates.TASK)):
        if _write_if_absent(root / name, content):
            created.append(name)
    if with_spec and _write_if_absent(root / "SPEC.md", templates.SPEC):
        created.append("SPEC.md")
    if selected_modules:
        active, packs = modules.activate(root, selected_modules)
        created_packs = sum(len(files) for files in packs.values())
        print("Modules: " + ", ".join(selected_modules))
        if created_packs:
            print(f"Packs copied to docs/fia/: {created_packs} file(s)")
    print("FIA Core " + __version__)
    print("Created: " + (", ".join(created) if created else "nothing (existing files preserved)"))
    print("Next: complete PROJECT.md and TASK.md, run `fia test -- <command>`, then `fia verify`.")
    if assets_ref:
        print(f"-> Descargando pack de assets: {assets_ref}")
        assets.fetch_manifest(root, assets_ref)
    return 0


def module_command(root, action, name=None):
    root = Path(root)
    if action == "list":
        active = [row for row in modules.rows(root) if row["enabled"]]
        print("FIA modules")
        for row in modules.rows(root):
            state = "ON" if row["enabled"] else "off"
            print(f"{row['name']:<12} {state:<4} {row['level']:<8} {row['purpose']}")
        print("Active: " + (", ".join(row["name"] for row in active) if active else "none"))
        return 0
    if name not in modules.MODULES:
        print(f"Módulo desconocido: {name}. Usa `fia module list`.", file=sys.stderr)
        return 2
    if action == "info":
        details = modules.MODULES[name]
        print(f"{name}: {details['label']} ({details['level']})")
        print(details["purpose"])
        print(f"Pack: modules/{name}/")
        return 0
    active = modules.set_enabled(root, name, active=action == "enable")
    verb = "activado" if action == "enable" else "desactivado"
    print(f"{name}: {verb}")
    if action == "enable":
        created = modules.install_pack(root, name)
        if created:
            print("Pack disponible en docs/fia/" + name + ": " + str(len(created)) + " archivo(s)")
    print("Active: " + (", ".join(active) if active else "none"))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fia", description="Minimal local verification for agent work.")
    sub = parser.add_subparsers(dest="command", required=True)
    init_parser = sub.add_parser("init", help="Create the minimal project files.")
    init_parser.add_argument("-d", "--dir", default=".")
    init_parser.add_argument("--with-spec", action="store_true", help="Create optional SPEC.md.")
    init_parser.add_argument("--modules", default=None, metavar="LIST",
                             help="Optional modules separated by commas (e.g. ui,security).")
    init_parser.add_argument("--assets", default=None, metavar="URL|MANIFEST",
                             help="Download an asset pack after creating the project files "
                                  "(`fia assets fetch`), e.g. a UI_ASSETS.json URL.")
    test_parser = sub.add_parser("test", help="Run and record a test command.")
    test_parser.add_argument("-d", "--dir", default=".")
    test_parser.add_argument("--timeout", type=float, default=None,
                             help="Seconds before the command is killed (default: no limit).")
    test_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command after --.")
    verify_parser = sub.add_parser("verify", help="Check the project and its current task.")
    verify_parser.add_argument("-d", "--dir", default=".")
    status_parser = sub.add_parser("status", help="Show task and verification status.")
    status_parser.add_argument("-d", "--dir", default=".")
    module_parser = sub.add_parser("module", help="List or activate optional capability packs.")
    module_sub = module_parser.add_subparsers(dest="module_action", required=True)
    module_list = module_sub.add_parser("list", help="List available modules.")
    module_list.add_argument("-d", "--dir", default=".")
    for action in ("enable", "disable", "info"):
        action_parser = module_sub.add_parser(action, help=f"{action.title()} an optional module.")
        action_parser.add_argument("name", choices=sorted(modules.MODULES))
        action_parser.add_argument("-d", "--dir", default=".")
    assets_parser = sub.add_parser("assets", help="Manifests and verified asset-pack downloads.")
    assets_sub = assets_parser.add_subparsers(dest="assets_action", required=True)
    assets_fetch = assets_sub.add_parser("fetch", help="Download and verify a manifest's assets.")
    assets_fetch.add_argument("manifest", nargs="?", default=None,
                              help="Manifest URL or path (default: UI_ASSETS.json in the project).")
    assets_fetch.add_argument("-d", "--dir", default=".")
    assets_manifest = assets_sub.add_parser("manifest", help="Generate a manifest from a local directory.")
    assets_manifest.add_argument("--dir-source", required=True, metavar="DIR",
                                 help="Directory with the assets to publish.")
    assets_manifest.add_argument("--base-url", required=True, metavar="URL",
                                 help="Base URL where the assets will be hosted.")
    assets_manifest.add_argument("-o", "--out", default="UI_ASSETS.json", metavar="FILE")
    assets_manifest.add_argument("-d", "--dir", default=".")
    ui_parser = sub.add_parser("ui", help="Assisted UI/UX pack (opt-in, SHA-256 verified).")
    ui_sub = ui_parser.add_subparsers(dest="ui_action", required=True)
    ui_setup = ui_sub.add_parser("setup", help="Install the UI/UX environment (or recipes only).")
    ui_setup.add_argument("--recetas", action="store_true",
                          help="Install only the recipes (library/).")
    ui_setup.add_argument("--url", default=None, metavar="URL",
                          help="Manifest override (default: official PGMIA pack).")
    ui_setup.add_argument("-d", "--dir", default=".")
    ui_status = ui_sub.add_parser("status", help="Local UI/UX environment state (no network).")
    ui_status.add_argument("-d", "--dir", default=".")
    args = parser.parse_args(argv)
    root = Path(args.dir)
    if args.command == "init":
        try:
            return init(root, args.with_spec, selected_modules=args.modules,
                        assets_ref=args.assets)
        except ValueError as error:
            parser.error(str(error))
        except assets.AssetError as error:
            print(str(error), file=sys.stderr)
            return 1
    if args.command == "test":
        command = list(args.cmd or [])
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            parser.error("fia test necesita un comando: fia test -- python -m unittest")
        try:
            record = store.run(root, command, timeout=args.timeout)
        except TimeoutError as error:
            print(str(error), file=sys.stderr)
            return 2
        if record["timed_out"]:
            print(f"{record['id']}: TIMEOUT tras {args.timeout}s")
            return 1
        print(f"{record['id']}: exit={record['exit_code']} ({record['duration_s']}s)")
        return record["exit_code"]
    if args.command == "verify":
        report = verify(root)
        for name, result in report["checks"]:
            print(f"{name:<8} {result}")
        if report["errors"]:
            print("\nFAIL")
            for error in report["errors"]:
                print(f"- {error}")
        else:
            print("\nPASS — project is verifiable")
        return 0 if report["status"] == "PASS" else 1
    if args.command == "status":
        print(json.dumps(status(root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "module":
        return module_command(Path(args.dir), args.module_action,
                              getattr(args, "name", None))
    if args.command == "assets":
        try:
            if args.assets_action == "fetch":
                ref = args.manifest or str(Path(args.dir) / assets.DEFAULT_MANIFEST)
                return assets.fetch_manifest(Path(args.dir), ref)
            return assets.build_manifest(Path(args.dir_source), args.base_url, Path(args.out))
        except assets.AssetError as error:
            print(str(error), file=sys.stderr)
            return 1
    if args.command == "ui":
        try:
            if args.ui_action == "setup":
                return ui.cmd_ui_setup(Path(args.dir), recipes_only=args.recetas,
                                       url=args.url)
            return ui.cmd_ui_status(Path(args.dir))
        except assets.AssetError as error:
            print(str(error), file=sys.stderr)
            return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
