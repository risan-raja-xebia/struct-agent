import pytest
import json
from struct_agent.mconv.mschema_to_mdl import WrenMDLConverter

def sample_mschema():
    return {
        "db_id": "testdb",
        "tables": {
            "orders": {
                "fields": {
                    "order_id": {"type": "INTEGER", "primary_key": True, "nullable": False},
                    "amount": {"type": "NUMERIC", "nullable": True, "comment": "Order amount"}
                },
                "comment": "Orders table"
            },
            "customers": {
                "fields": {
                    "customer_id": {"type": "INTEGER", "primary_key": True, "nullable": False},
                    "name": {"type": "VARCHAR", "nullable": False}
                }
            }
        },
        "foreign_keys": [
            ["orders", "customer_id", None, "customers", "customer_id"]
        ]
    }

def test_convert_basic():
    converter = WrenMDLConverter(catalog="testdb", schema="public")
    mdl = converter.convert(sample_mschema())
    assert mdl["catalog"] == "testdb"
    assert mdl["schema"] == "public"
    assert len(mdl["models"]) == 2
    assert any(m["name"] == "Orders" for m in mdl["models"])
    assert "relationships" in mdl
    assert mdl["relationships"][0]["name"] == "OrdersCustomers"

def test_convert_from_file_and_save(tmp_path):
    converter = WrenMDLConverter(catalog="testdb")
    mschema_path = tmp_path / "mschema.json"
    mdl_path = tmp_path / "mdl.json"
    mschema_path.write_text(json.dumps(sample_mschema()))
    mdl = converter.convert_from_file(str(mschema_path))
    assert "models" in mdl
    converter.save_to_file(mdl, str(mdl_path))
    assert json.loads(mdl_path.read_text())["catalog"] == "testdb"

def test_convert_and_save(tmp_path):
    converter = WrenMDLConverter(catalog="testdb")
    mschema_path = tmp_path / "mschema.json"
    mschema_path.write_text(json.dumps(sample_mschema()))
    mdl = converter.convert_and_save(str(mschema_path), str(tmp_path / "mdl.json"))
    assert "models" in mdl

def test_from_config():
    config = {"catalog": "abc", "schema": "myschema", "use_table_reference": "false"}
    converter = WrenMDLConverter.from_config(config)
    assert converter.catalog == "abc"
    assert converter.schema == "myschema"
    assert converter.use_table_reference is False
    with pytest.raises(ValueError):
        WrenMDLConverter.from_config({})

def test_get_conversion_stats():
    converter = WrenMDLConverter(catalog="testdb")
    mdl = converter.convert(sample_mschema())
    stats = converter.get_conversion_stats(mdl)
    assert stats["models"] == 2
    assert stats["relationships"] == 1

def test_save_to_file_error(monkeypatch):
    converter = WrenMDLConverter(catalog="testdb")
    mdl = converter.convert(sample_mschema())
    monkeypatch.setattr("builtins.open", lambda *a, **k: (_ for _ in ()).throw(IOError("fail")))
    with pytest.raises(IOError):
        converter.save_to_file(mdl, "badfile.json")
