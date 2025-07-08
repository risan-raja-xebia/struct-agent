from .base import (
    DimensionType, MeasureType, JoinType, TimeGranularity,
    Dimension, Measure#, Segment, Join, PreAggregation, Cube
)
from typing import Dict, List, Optional, Any
from sqlalchemy import create_engine, inspect, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.sql.sqltypes import String, Integer, DateTime, Date, Boolean, Float, Numeric
import logging

logger = logging.getLogger(__name__)

class DatabaseInspector:
    """Enhanced database inspector that extracts semantic information"""

    def __init__(self, database_url: str, default_schema: Optional[str] = None):
        self.database_url = database_url
        self.default_schema = default_schema
        self.engine = self._create_engine()
        self.inspector = inspect(self.engine)
        self.metadata = MetaData()

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with proper configuration"""
        connect_args = {}
        execution_options = {}

        if self.default_schema:
            connect_args = {"options": f"-csearch_path={self.default_schema}"}
            execution_options = {"schema_translate_map": {None: self.default_schema}}

        return create_engine(
            self.database_url,
            connect_args=connect_args,
            execution_options=execution_options
        )

    def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive table information"""
        schema = schema or self.default_schema

        try:
            columns = self.inspector.get_columns(table_name, schema=schema)
            foreign_keys = self.inspector.get_foreign_keys(table_name, schema=schema)
            primary_keys = self.inspector.get_pk_constraint(table_name, schema=schema)
            indexes = self.inspector.get_indexes(table_name, schema=schema)

            return {
                'name': table_name,
                'schema': schema,
                'columns': columns,
                'foreign_keys': foreign_keys,
                'primary_keys': primary_keys.get('constrained_columns', []),
                'indexes': indexes
            }
        except Exception as e:
            logger.error(f"Error inspecting table {table_name}: {e}")
            return {}

    def get_all_tables(self, schema: Optional[str] = None) -> List[str]:
        """Get all table names in the schema"""
        schema = schema or self.default_schema
        return self.inspector.get_table_names(schema=schema)

    def infer_relationships(self, schema: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Infer relationships between tables based on foreign keys"""
        schema = schema or self.default_schema
        relationships = {}

        for table_name in self.get_all_tables(schema):
            table_info = self.get_table_info(table_name, schema)
            relationships[table_name] = []

            for fk in table_info.get('foreign_keys', []):
                relationships[table_name].append({
                    'target_table': fk['referred_table'],
                    'source_columns': fk['constrained_columns'],
                    'target_columns': fk['referred_columns'],
                    'relationship_type': self._infer_relationship_type(table_name, fk, schema)
                })

        return relationships

    def _infer_relationship_type(self, table_name: str, fk: Dict[str, Any], schema: Optional[str]) -> JoinType:
        """Infer the type of relationship based on foreign key constraints"""
        # This is a simplified heuristic - in practice, you'd want more sophisticated logic
        source_col = fk['constrained_columns'][0] if fk['constrained_columns'] else ''

        # If the foreign key column is also a primary key, it's likely one-to-one
        table_info = self.get_table_info(table_name, schema)
        if source_col in table_info.get('primary_keys', []):
            return JoinType.ONE_TO_ONE

        # Otherwise, assume many-to-one (most common case)
        return JoinType.MANY_TO_ONE

    def _sql_type_to_cube_type(self, sql_type) -> DimensionType:
        """Convert SQL types to Cube dimension types"""
        if isinstance(sql_type, (String,)):
            return DimensionType.STRING
        elif isinstance(sql_type, (Integer, Float, Numeric)):
            return DimensionType.NUMBER
        elif isinstance(sql_type, (DateTime, Date)):
            return DimensionType.TIME
        elif isinstance(sql_type, Boolean):
            return DimensionType.BOOLEAN
        else:
            return DimensionType.STRING

    def infer_dimensions(self, table_name: str, schema: Optional[str] = None) -> List[Dimension]:
        """Infer dimensions from table columns"""
        table_info = self.get_table_info(table_name, schema)
        dimensions = []

        for col in table_info.get('columns', []):
            col_type = self._sql_type_to_cube_type(col['type'])
            is_primary_key = col['name'] in table_info.get('primary_keys', [])

            dimension = Dimension(
                name=col['name'],
                sql=col['name'],
                type=col_type,
                primary_key=is_primary_key,
                description=f"Dimension for {col['name']} column"
            )

            # Add time granularities for time dimensions
            if col_type == DimensionType.TIME:
                dimension.granularities = [
                    TimeGranularity.YEAR,
                    TimeGranularity.QUARTER,
                    TimeGranularity.MONTH,
                    TimeGranularity.WEEK,
                    TimeGranularity.DAY
                ]

            dimensions.append(dimension)

        return dimensions

    def infer_measures(self, table_name: str, schema: Optional[str] = None) -> List[Measure]:
        """Infer measures from table columns"""
        table_info = self.get_table_info(table_name, schema)
        measures = []

        # Always add a count measure
        measures.append(Measure(
            name='count',
            type=MeasureType.COUNT,
            description=f"Count of records in {table_name}"
        ))

        # Add sum measures for numeric columns
        for col in table_info.get('columns', []):
            if isinstance(col['type'], (Integer, Float, Numeric)):
                # Skip ID columns for sum measures
                if not col['name'].lower().endswith('_id') and col['name'].lower() != 'id':
                    measures.append(Measure(
                        name=f"total_{col['name']}",
                        type=MeasureType.SUM,
                        sql=col['name'],
                        description=f"Total {col['name']}"
                    ))

                    measures.append(Measure(
                        name=f"avg_{col['name']}",
                        type=MeasureType.AVG,
                        sql=col['name'],
                        description=f"Average {col['name']}"
                    ))

        return measures
