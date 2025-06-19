import importlib

def test_struct_agent_src_installed():
    try:
        importlib.import_module("src.struct_agent")
    except ImportError:
        assert False, "src.struct_agent is not installed or not importable."
    else:
        assert True
