from .base import (
    # DimensionType, MeasureType, JoinType, TimeGranularity,
    # Dimension, Measure, PreAggregation,
    Join, Cube, View, ViewCube
)
from .database import DatabaseInspector
from jinja2 import Environment, FileSystemLoader, DictLoader
from typing import Dict, List, Optional, Any, Union
import os

class SemanticModelGenerator:
    """Main generator class that creates semantic models from database schemas"""

    def __init__(self, database_url: str, default_schema: Optional[str] = None,
                 template_dir: Optional[str] = None):
        self.database_url = database_url
        self.default_schema = default_schema
        self.db_inspector = DatabaseInspector(database_url, default_schema)

        # Set up Jinja environment
        if template_dir and os.path.exists(template_dir):
            self.jinja_env = Environment(
                loader=FileSystemLoader(template_dir),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            # Use default templates
            self.jinja_env = Environment(
                loader=DictLoader(self._get_default_templates()),
                trim_blocks=True,
                lstrip_blocks=True
            )

    def _get_default_templates(self) -> Dict[str, str]:
        """Return default Jinja templates"""
        return {
            'cube.yaml.j2': '''cubes:
  - name: {{ cube.name }}
    {% if cube.sql_table %}
    sql_table: {{ cube.sql_table }}
    {% endif %}
    {% if cube.sql %}
    sql: |
      {{ cube.sql | indent(6) }}
    {% endif %}
    {% if cube.description %}
    description: {{ cube.description }}
    {% endif %}
    {% if cube.extends %}
    extends: {{ cube.extends }}
    {% endif %}

    {% if cube.dimensions %}
    dimensions:
      {% for dimension in cube.dimensions %}
      - name: {{ dimension.name }}
        sql: {{ dimension.sql }}
        type: {{ dimension.type }}
        {% if dimension.primary_key %}
        primary_key: true
        {% endif %}
        {% if dimension.description is not none %}
        description: {{ dimension.description }}
        {% endif %}
        {% if dimension.format %}
        format: {{ dimension.format }}
        {% endif %}
        {% if dimension.granularity %}
        granularity: {{ dimension.granularity }}
        {% endif %}
      {% endfor %}
    {% endif %}

    {% if cube.measures %}
    measures:
      {% for measure in cube.measures %}
      - name: {{ measure.name }}
        type: {{ measure.type }}
        {% if measure.sql %}
        sql: {{ measure.sql }}
        {% endif %}
        {% if measure.description is not none %}
        description: {{ measure.description }}
        {% endif %}
        {% if measure.format %}
        format: {{ measure.format }}
        {% endif %}
        {% if measure.rolling_window %}
        rolling_window: {{ measure.rolling_window }}
        {% endif %}
      {% endfor %}
    {% endif %}

    {% if cube.joins %}
    joins:
      {% for join in cube.joins %}
      - name: {{ join.name }}
        sql: "{{ join.sql }}"
        relationship: {{ join.relationship }}
      {% endfor %}
    {% endif %}

    {% if cube.pre_aggregations %}
    pre_aggregations:
      {% for pre_agg in cube.pre_aggregations %}
      - name: {{ pre_agg.name }}
        measures: {{ pre_agg.measures }}
        dimensions: {{ pre_agg.dimensions }}
        {% if pre_agg.time_dimension %}
        time_dimension: {{ pre_agg.time_dimension }}
        {% endif %}
        {% if pre_agg.granularity %}
        granularity: {{ pre_agg.granularity }}
        {% endif %}
        {% if pre_agg.refresh_key %}
        refresh_key: {{ pre_agg.refresh_key }}
        {% endif %}
      {% endfor %}
    {% endif %}
''',
            'view.yaml.j2': '''views:
  - name: {{ view.name }}
    {% if view.description %}
    description: {{ view.description }}
    {% endif %}
    cubes:
      {% for cube in view.cubes %}
      - join_path: {{ cube.join_path }}
        {% if cube.includes %}
        includes: {{ cube.includes }}
        {% endif %}
        {% if cube.excludes %}
        excludes: {{ cube.excludes }}
        {% endif %}
        {% if cube.prefix %}
        prefix: {{ cube.prefix }}
        {% endif %}
        {% if cube.alias %}
        alias: {{ cube.alias }}
        {% endif %}
      {% endfor %}
''',
            'multi_stage.yaml.j2': '''# Multi-stage calculation example
cubes:
  - name: {{ base_cube_name }}_stage1
    sql_table: {{ table_name }}
    measures:
      {% for measure in stage1_measures %}
      - name: {{ measure.name }}
        type: {{ measure.type }}
        {% if measure.sql %}
        sql: {{ measure.sql }}
        {% endif %}
      {% endfor %}
    dimensions:
      {% for dimension in dimensions %}
      - name: {{ dimension.name }}
        sql: {{ dimension.sql }}
        type: {{ dimension.type }}
        {% if dimension.primary_key %}
        primary_key: true
        {% endif %}
      {% endfor %}

  - name: {{ base_cube_name }}_final
    sql: |
      SELECT * FROM (
        {{ stage1_sql }}
      ) AS stage1
    measures:
      {% for measure in final_measures %}
      - name: {{ measure.name }}
        type: {{ measure.type }}
        {% if measure.sql %}
        sql: {{ measure.sql }}
        {% endif %}
      {% endfor %}
'''
        }

    def generate_cube_from_table(self, table_name: str, schema: Optional[str] = None,
                                template_name: str = 'cube.yaml.j2') -> Cube:
        """Generate a cube from a database table"""
        schema = schema or self.default_schema

        # Get table information
        table_info = self.db_inspector.get_table_info(table_name, schema)
        if not table_info:
            raise ValueError(f"Table {table_name} not found in schema {schema}")

        # Generate dimensions and measures
        dimensions = self.db_inspector.infer_dimensions(table_name, schema)
        measures = self.db_inspector.infer_measures(table_name, schema)

        # Generate joins based on foreign keys
        joins = self._generate_joins(table_name, schema)

        # Create the cube
        cube = Cube(
            name=table_name,
            sql_table=f"{schema}.{table_name}" if schema else table_name,
            description=f"Cube for {table_name} table",
            dimensions=dimensions,
            measures=measures,
            joins=joins
        )

        return cube

    def _generate_joins(self, table_name: str, schema: Optional[str] = None) -> List[Join]:
        """Generate joins based on foreign key relationships"""
        joins = []
        relationships = self.db_inspector.infer_relationships(schema)

        for relationship in relationships.get(table_name, []):
            join = Join(
                name=relationship['target_table'],
                sql=f"{{CUBE}}.{relationship['source_columns'][0]} = {{{relationship['target_table']}.{relationship['target_columns'][0]}}}",
                relationship=relationship['relationship_type'],
                description=f"Join to {relationship['target_table']} table"
            )
            joins.append(join)

        return joins

    def generate_multi_stage_cube(self, table_name: str, schema: Optional[str] = None,
                                 stage_definitions: Optional[List[Dict[str, Any]]] = None) -> List[Cube]:
        """Generate multi-stage calculation cubes"""
        schema = schema or self.default_schema

        if not stage_definitions:
            # Default two-stage calculation
            stage_definitions = [
                {
                    'name': f"{table_name}_stage1",
                    'measures': ['count', 'sum_total'],
                    'description': "First stage aggregation"
                },
                {
                    'name': f"{table_name}_final",
                    'measures': ['total_count', 'avg_per_group'],
                    'description': "Final calculation stage"
                }
            ]

        cubes = []
        base_cube = self.generate_cube_from_table(table_name, schema)

        for i, stage_def in enumerate(stage_definitions):
            if i == 0:
                # First stage uses the base table
                stage_cube = Cube(
                    name=stage_def['name'],
                    sql_table=base_cube.sql_table,
                    description=stage_def['description'],
                    dimensions=base_cube.dimensions,
                    measures=[m for m in base_cube.measures if m.name in stage_def['measures']]
                )
            else:
                # Subsequent stages use SQL from previous stage
                prev_stage = stage_definitions[i-1]['name']
                stage_cube = Cube(
                    name=stage_def['name'],
                    sql=f"SELECT * FROM ({{{prev_stage}}}) AS prev_stage",
                    description=stage_def['description'],
                    dimensions=base_cube.dimensions,
                    measures=[m for m in base_cube.measures if m.name in stage_def['measures']]
                )

            cubes.append(stage_cube)

        return cubes

    def generate_view(self, view_name: str, cube_joins: List[Dict[str, Any]]) -> View:
        """Generate a view that combines multiple cubes"""
        view_cubes = []

        for cube_join in cube_joins:
            view_cube = ViewCube(
                join_path=cube_join['join_path'],
                includes=cube_join.get('includes', ['*']),
                excludes=cube_join.get('excludes', []),
                prefix=cube_join.get('prefix', False),
                alias=cube_join.get('alias')
            )
            view_cubes.append(view_cube)

        return View(
            name=view_name,
            cubes=view_cubes,
            description=f"Combined view: {view_name}"
        )

    def generate_yaml(self, cube_or_view: Union[Cube, View], template_name: str = 'cube.yaml.j2') -> str:
        """Generate YAML from cube or view object"""
        template = self.jinja_env.get_template(template_name)

        if isinstance(cube_or_view, Cube):
            context = {'cube': cube_or_view.to_dict()}
        else:
            context = {'view': cube_or_view.to_dict()}

        return template.render(**context)

    def generate_all_cubes(self, schema: Optional[str] = None, output_dir: str = 'cubes') -> Dict[str, str]:
        """Generate cubes for all tables in the schema"""
        schema = schema or self.default_schema
        results = {}

        os.makedirs(output_dir, exist_ok=True)

        for table_name in self.db_inspector.get_all_tables(schema):
            try:
                cube = self.generate_cube_from_table(table_name, schema)
                yaml_content = self.generate_yaml(cube)

                output_path = os.path.join(output_dir, f"{table_name}.yaml")
                with open(output_path, 'w') as f:
                    f.write(yaml_content)

                results[table_name] = output_path
            except Exception as e:
                print(f"Error generating cube for {table_name}: {e}")

        return results
