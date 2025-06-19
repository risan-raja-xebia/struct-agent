from src.struct_agent.mdl import schema


def test_check_connection_success():
    # Use SQLite in-memory DB for connection check
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    # Create tables before checking connection
    schema.Base.metadata.create_all(engine)
    with engine.connect() as conn:
        result = conn.execute(schema.Base.metadata.tables["model"].select().limit(1))
        assert result is not None

def test_model_table_creation(tmp_path):
    # Use SQLite in-memory DB for ORM model creation
    from sqlalchemy import create_engine, MetaData
    engine = create_engine("sqlite:///:memory:")
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
