from src.struct_agent.mdl import schema

def test_get_engine_env(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "testdb")
    engine = schema.get_engine()
    url = engine.url
    assert url.get_backend_name() == "postgresql"
    assert url.username == "user"
    assert url.host == "localhost"
    assert url.port == 5432
    assert url.database == "testdb"

def test_check_connection_success(monkeypatch):
    class DummyConn:
        def execute(self, _):
            class DummyResult:
                def fetchone(self):
                    return (1,)
            return DummyResult()
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    class DummyEngine:
        def connect(self): return DummyConn()
    monkeypatch.setattr(schema, "get_engine", lambda: DummyEngine())
    schema.check_connection()  # Should print success

def test_model_table_creation(tmp_path, monkeypatch):
    # Use SQLite in-memory DB for ORM model creation
    from sqlalchemy import create_engine, MetaData
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(schema, "get_engine", lambda: engine)
    # Create all referenced tables for 'model'
    tables_to_create = [
        schema.Base.metadata.tables["project"],
        schema.Base.metadata.tables["table_reference"],
        schema.Base.metadata.tables["model"]
    ]
    metadata = MetaData()
    for t in tables_to_create:
        t.to_metadata(metadata)
    metadata.create_all(engine, checkfirst=True)
    insp = engine.dialect.get_table_names(engine.connect())
    assert "model" in insp
    assert "project" in insp
    assert "table_reference" in insp
