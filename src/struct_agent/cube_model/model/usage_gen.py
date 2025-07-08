from .cube_gen import generate_yaml_for_table
from .db_utils import get_engine
import os

def main():
    # Hardcoded example usage for testing/demo
    database_url = 'postgresql+psycopg2://admin:admin123@172.19.215.172:5432/ecommerce_db'
    schema = 'ecommerce'
    table_name = None  # Set to None to trigger all tables
    output_dir = os.path.join(os.path.dirname(__file__), 'cubes')
    os.makedirs(output_dir, exist_ok=True)

    engine = get_engine(database_url, default_schema=schema)
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema=schema)

    if table_name:
        # Only generate for the specified table
        output_path = os.path.join(output_dir, f'{table_name}.yaml')
        yaml_str = generate_yaml_for_table(table_name, database_url, schema=schema, output_path=output_path)
        print(f"YAML generated and saved to {output_path}\n")
        print(yaml_str)
    else:
        # Generate for all tables in the schema
        for tbl in tables:
            output_path = os.path.join(output_dir, f'{tbl}.yaml')
            yaml_str = generate_yaml_for_table(tbl, database_url, schema=schema, output_path=output_path)
            print(f"YAML generated and saved to {output_path}\n")
            print(yaml_str)

if __name__ == "__main__":
    main()
