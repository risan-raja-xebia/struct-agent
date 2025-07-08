from jinja2 import Environment, FileSystemLoader
from .db_utils import get_engine
from sqlalchemy import inspect
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

def generate_yaml_for_table(table_name, database_url, schema=None, template_name='base_cube.j2', output_path=None):
    """
    Connects to the database, inspects the table, and generates a YAML config using a Jinja template.
    User must provide database_url and (optionally) schema.
    """
    engine = get_engine(database_url, default_schema=schema)
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name, schema=schema)
    dimensions = []
    for col in columns:
        dtype = 'time' if 'date' in col['name'] or 'time' in col['name'] else 'string'
        dimensions.append({'name': col['name'], 'type': dtype, 'sql': col['name']})
    measures = [{'name': 'count', 'type': 'count'}]
    context = {
        'cube_name': table_name,
        'table_name': table_name if not schema else f"{schema}.{table_name}",
        'dimensions': dimensions,
        'measures': measures
    }
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(template_name)
    yaml_str = template.render(**context)
    if output_path:
        with open(output_path, 'w') as f:
            f.write(yaml_str)
    return yaml_str
