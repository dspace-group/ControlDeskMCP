"""Diagnostic: discover correct COM property names for IXaProjectRoot and IXaExperiment."""
import asyncio
import sources.com_bridge as com_bridge


async def main():
    await com_bridge.startup()
    conn = com_bridge.get_connection()
    await com_bridge.ensure_connected()

    def _probe():
        app = conn.get_app()

        # ── 1. Project root properties ─────────────────────────────────────
        roots = app.ProjectRoots
        print(f"ProjectRoots.Count = {roots.Count}")

        # Add a temp root so we can inspect it
        roots.Add("C:\\Temp\\MCPDiagRoot")
        print("Root added")

        # Try to get it by path string (which is how Add() registered it)
        root = roots.Item("C:\\Temp\\MCPDiagRoot")
        print(f"root type: {type(root)}")
        props_to_try = ["Path", "Name", "FolderPath", "Location", "Directory",
                        "ProjectRootPath", "RootPath", "FullPath", "AbsolutePath"]
        for prop in props_to_try:
            try:
                val = getattr(root, prop)
                print(f"  root.{prop} = {val!r}")
            except Exception as e:
                print(f"  root.{prop} ERROR: {e}")

        # Try by index 1
        root_by_idx = roots.Item(1)
        print(f"root by index 1 type: {type(root_by_idx)}")
        for prop in props_to_try:
            try:
                val = getattr(root_by_idx, prop)
                print(f"  root_by_idx.{prop} = {val!r}")
            except Exception as e:
                print(f"  root_by_idx.{prop} ERROR: {e}")

        root.Remove()
        print("Root removed")

    await com_bridge.dispatch(_probe)

    # ── 2. Experiment properties ───────────────────────────────────────────
    # Need a project open to probe experiments
    def _probe_exp():
        app = conn.get_app()
        roots = app.ProjectRoots
        roots.Add("C:\\Temp\\MCPDiagRoot2")
        root = roots.Item("C:\\Temp\\MCPDiagRoot2")
        root.Activate()

        project = app.ActiveProjectRoot.Projects.Add("DiagProject")
        app.ActiveProjectRoot.Projects.Item("DiagProject").Open()

        exps = app.ActiveProject.Experiments
        print(f"Experiments.Count before = {exps.Count}")
        exps.Add("DiagExp1", True)
        print(f"Experiments.Count after = {exps.Count}")

        # Try index 0 and 1
        for idx in [0, 1]:
            try:
                exp = exps.Item(idx)
                print(f"  exps.Item({idx}) type: {type(exp)}")
                print(f"  exps.Item({idx}).Name = {exp.Name!r}")
            except Exception as e:
                print(f"  exps.Item({idx}) ERROR: {e}")

        app.ActiveProject.Close(False)
        root.Projects.Item("DiagProject").Remove(True)
        root.Remove()
        print("Cleanup done")

    await com_bridge.dispatch(_probe_exp)

    await com_bridge.shutdown()


asyncio.run(main())
