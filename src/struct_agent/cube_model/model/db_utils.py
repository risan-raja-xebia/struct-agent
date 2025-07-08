from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

def get_engine(database_url, default_schema=None) -> Engine:
    """
    Returns a SQLAlchemy engine for the given database_url and schema.
    """
    connect_args = {"options": f"-csearch_path={default_schema}"} if default_schema else {}
    execution_options = {"schema_translate_map": {None: default_schema}} if default_schema else {}
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        execution_options=execution_options
    )
    return engine
