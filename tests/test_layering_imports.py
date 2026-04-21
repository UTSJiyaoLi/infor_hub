from __future__ import annotations


def test_legacy_graph_wrapper_exports_new_entrypoints():
    import graph
    import orchestration.graph as new_graph

    assert graph.run_collector is new_graph.run_collector
    assert graph.graph is new_graph.graph


def test_tools_package_exports_core_functions():
    import tools

    assert callable(tools.parse_json)


def test_removed_legacy_modules_are_absent():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert not (root / "agent.py").exists()
    assert not (root / "prompts.py").exists()


def test_nextjs_frontend_files_exist():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert (root / "apps" / "web" / "package.json").exists()
    assert (root / "apps" / "web" / "app" / "page.tsx").exists()
