import click
import os
from .core.generator import SemanticModelGenerator

@click.group()
def cli():
    """Semantic Modeling CLI - Generate Cube.dev-style models from your database"""
    pass

@cli.command()
@click.option('--database-url', required=True, help='Database connection URL')
@click.option('--schema', help='Database schema name')
@click.option('--table', help='Specific table name (if not provided, generates for all tables)')
@click.option('--output-dir', default='cubes', help='Output directory for generated files')
@click.option('--template-dir', help='Custom template directory')
def generate(database_url, schema, table, output_dir, template_dir):
    """Generate semantic models from database tables"""
    generator = SemanticModelGenerator(database_url, schema, template_dir)

    if table:
        cube = generator.generate_cube_from_table(table, schema)
        yaml_content = generator.generate_yaml(cube)

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{table}.yaml")
        with open(output_path, 'w') as f:
            f.write(yaml_content)

        click.echo(f"Generated cube for {table}: {output_path}")
    else:
        results = generator.generate_all_cubes(schema, output_dir)
        click.echo(f"Generated {len(results)} cubes in {output_dir}")
        for table_name, path in results.items():
            click.echo(f"  {table_name}: {path}")

@cli.command()
@click.option('--database-url', required=True, help='Database connection URL')
@click.option('--schema', help='Database schema name')
@click.option('--table', required=True, help='Base table name')
@click.option('--output-dir', default='cubes', help='Output directory for generated files')
@click.option('--stages', default=2, help='Number of calculation stages')
def generate_multi_stage(database_url, schema, table, output_dir, stages):
    """Generate multi-stage calculation cubes"""
    generator = SemanticModelGenerator(database_url, schema)

    # Generate stage definitions
    stage_definitions = []
    for i in range(stages):
        stage_definitions.append({
            'name': f"{table}_stage{i+1}",
            'measures': ['count'] if i == 0 else ['calculated_measure'],
            'description': f"Stage {i+1} calculation"
        })

    cubes = generator.generate_multi_stage_cube(table, schema, stage_definitions)

    os.makedirs(output_dir, exist_ok=True)

    for cube in cubes:
        yaml_content = generator.generate_yaml(cube)
        output_path = os.path.join(output_dir, f"{cube.name}.yaml")
        with open(output_path, 'w') as f:
            f.write(yaml_content)
        click.echo(f"Generated multi-stage cube: {output_path}")

@cli.command()
@click.option('--database-url', required=True, help='Database connection URL')
@click.option('--schema', help='Database schema name')
def inspect(database_url, schema):
    """Inspect database schema and show relationships"""
    generator = SemanticModelGenerator(database_url, schema)

    tables = generator.db_inspector.get_all_tables(schema)
    click.echo(f"Found {len(tables)} tables in schema '{schema or 'default'}':")

    for table in tables:
        click.echo(f"\n📊 {table}")
        table_info = generator.db_inspector.get_table_info(table, schema)

        # Show columns
        click.echo("  Columns:")
        for col in table_info.get('columns', []):
            pk_marker = " (PK)" if col['name'] in table_info.get('primary_keys', []) else ""
            click.echo(f"    - {col['name']}: {col['type']}{pk_marker}")

        # Show foreign keys
        if table_info.get('foreign_keys'):
            click.echo("  Foreign Keys:")
            for fk in table_info['foreign_keys']:
                click.echo(f"    - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

if __name__ == '__main__':
    cli()
