import pytest
import json
from struct_agent.mdl import mdl_loader
from sqlalchemy import create_engine

# Sample MDL data for testing
def sample_mdl():
    return {
        "catalog": "test_catalog",
        "schema": "test_schema",
        "models": [
            {
                "name": "TestModel",
                "tableReference": {"table": "test_table"},
                "columns": [
                    {"name": "id", "type": "int", "notNull": True},
                    {"name": "value", "type": "str"}
                ],
                "primaryKey": "id"
            }
        ],
        "relationships": [
            {
                "name": "TestRel",
                "models": ["TestModel", "TestModel"],
                "condition": "TestModel.id = TestModel.id",
                "joinType": "inner"
            }
        ]
    }

def test_load_mdl_file(tmp_path):
    mdl_path = tmp_path / "mdl.json"
    data = sample_mdl()
    mdl_path.write_text(json.dumps(data))
    loaded = mdl_loader.load_mdl_file(str(mdl_path))
    assert loaded == data

    # Test file not found
    with pytest.raises(FileNotFoundError):
        mdl_loader.load_mdl_file(str(tmp_path / "notfound.json"))

    # Test invalid JSON
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{bad json}")
    with pytest.raises(ValueError):
        mdl_loader.load_mdl_file(str(bad_path))

def test_update_mdl_to_db(tmp_path, monkeypatch):
    # Patch load_mdl_file to return sample data
    monkeypatch.setattr(mdl_loader, "load_mdl_file", lambda _: sample_mdl())
    engine = create_engine("sqlite:///:memory:")
    # Create all tables
    from src.struct_agent.mdl import schema
    schema.Base.metadata.create_all(engine)
    # Should not raise
    mdl_loader.update_mdl_to_db("dummy_path.json", project_display_name="Test Project", engine=engine)
