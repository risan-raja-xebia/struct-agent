import pytest
import json
from unittest.mock import patch, MagicMock
from src.struct_agent.mdl import mdl_loader

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

@patch("src.struct_agent.mdl.mdl_loader.get_engine")
@patch("src.struct_agent.mdl.mdl_loader.sessionmaker")
def test_update_mdl_to_db(mock_sessionmaker, mock_get_engine):
    # Setup mocks
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine
    mock_session = MagicMock()
    mock_sessionmaker.return_value = lambda **kwargs: mock_session
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    mock_session.flush.return_value = None
    mock_session.commit.return_value = None
    mock_session.close.return_value = None
    mock_session.add.return_value = None

    # Patch load_mdl_file to return sample data
    with patch("src.struct_agent.mdl.mdl_loader.load_mdl_file", return_value=sample_mdl()):
        mdl_loader.update_mdl_to_db("dummy_path.json", project_display_name="Test Project")
    # Should call commit and close
    assert mock_session.commit.called
    assert mock_session.close.called
