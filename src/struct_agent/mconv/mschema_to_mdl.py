import json
from typing import Dict, List, Any



class WrenMDLConverter:
    """Converts mschema JSON format to Wren.ai MDL format"""

    def __init__(self, catalog: str = None, schema: str = "public", use_table_reference: bool = True):
        """
        Initialize the converter.

        Args:
            catalog (str): The catalog name. If None, will try to get from environment variable POSTGRES_DB
            schema (str): The schema name. Defaults to "public"
            use_table_reference (bool): If True, uses tableReference; if False, uses refSql. Defaults to True
        """

        self.catalog = catalog
        self.schema = schema
        self.use_table_reference = use_table_reference
        self.models = []
        self.relationships = []


    @classmethod
    def from_config(cls, config: Dict[str, str]):
        """
        Create converter instance from configuration dictionary.

        Args:
            config (Dict[str, str]): Configuration dictionary with 'catalog', optionally 'schema' and 'use_table_reference'

        Returns:
            WrenMDLConverter: Configured converter instance

        Raises:
            ValueError: If catalog is not provided in config
        """
        catalog = config.get('catalog')
        if not catalog:
            raise ValueError("'catalog' key is required in config dictionary")

        schema = config.get('schema', 'public')
        use_table_reference = config.get('use_table_reference', 'true').lower() == 'true'
        return cls(catalog=catalog, schema=schema, use_table_reference=use_table_reference)



    def convert(self, mschema_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main conversion method following Wren.ai MDL structure"""
        # Reset for each conversion
        self.models = []
        self.relationships = []

        # Extract database information
        db_id = mschema_data.get("db_id", "database")
        tables = mschema_data.get("tables", {})
        foreign_keys = mschema_data.get("foreign_keys", [])

        # Convert tables to models
        for table_name, table_data in tables.items():
            model = self._convert_table_to_model(table_name, table_data, db_id)
            self.models.append(model)

        # Convert foreign keys to relationships
        self._convert_foreign_keys_to_relationships(foreign_keys)

        # Add relationship columns to models (as per Wren.ai examples)
        self._add_relationship_columns()

        # Build final MDL structure following Wren.ai format
        mdl = {
            "catalog": self.catalog,
            "schema": self.schema,
            "models": self.models
        }

        # Only add relationships if they exist
        if self.relationships:
            mdl["relationships"] = self.relationships

        return mdl

    def convert_from_file(self, input_file: str) -> Dict[str, Any]:
        """Convert from mschema JSON file"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                mschema_data = json.load(f)
            return self.convert(mschema_data)
        except FileNotFoundError:
            raise FileNotFoundError(f"File '{input_file}' not found")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON - {e}")

    def save_to_file(self, mdl_data: Dict[str, Any], output_file: str, pretty: bool = True) -> None:
        """Save MDL data to file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(mdl_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(mdl_data, f, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Error writing output file: {e}")

    def convert_and_save(self, input_file: str, output_file: str = "mdl.json", pretty: bool = True) -> Dict[str, Any]:
        """Convert from file and save to file in one step"""
        mdl_data = self.convert_from_file(input_file)
        self.save_to_file(mdl_data, output_file, pretty)
        return mdl_data

    def get_conversion_stats(self, mdl_data: Dict[str, Any]) -> Dict[str, int]:
        """Get statistics about the conversion"""
        return {
            "models": len(mdl_data.get('models', [])),
            "relationships": len(mdl_data.get('relationships', []))
        }

    def _convert_table_to_model(self, table_name: str, table_data: Dict[str, Any], db_id: str) -> Dict[str, Any]:
        """Convert table to Wren.ai MDL model format"""
        # Following Wren.ai model structure
        model = {
            "name": self._pascal_case(table_name),
            "properties": {},
            "columns": []
        }

        # Add table reference or refSql based on configuration
        if self.use_table_reference:
            model["tableReference"] = {
                "catalog": self.catalog,
                "schema": self.schema,
                "table": table_name
            }
        else:
            # Use refSql format - handle special characters in table names if needed
            table_ref = f'"{self.catalog}".{self.schema}."{table_name}"'
            model["refSql"] = f"select * from {table_ref}"

        # Add description to properties if available
        if table_data.get("comment"):
            model["properties"]["description"] = table_data["comment"]

        fields = table_data.get("fields", {})
        primary_key = None

        # Convert columns
        for field_name, field_data in fields.items():
            # Basic column structure as per Wren.ai
            column = {
                "name": self._camel_case(field_name),
                "type": self._map_to_wren_type(field_data.get("type", "VARCHAR")),
                "notNull": not field_data.get("nullable", True),  # Map nullable to notNull (inverse)
                "expression": field_name,
                "properties": {}
            }

            # Add column description if available
            if field_data.get("comment"):
                column["properties"]["description"] = field_data["comment"]

            model["columns"].append(column)

            # Track primary key
            if field_data.get("primary_key", False):
                primary_key = self._camel_case(field_name)

        # Set primary key after columns (as shown in Wren.ai examples)
        if primary_key:
            model["primaryKey"] = primary_key

        return model

    def _convert_foreign_keys_to_relationships(self, foreign_keys: List[List]):
        """Convert foreign keys to Wren.ai relationship format"""
        for fk in foreign_keys:
            if len(fk) >= 5:
                from_table = fk[0]
                from_column = fk[1]
                to_table = fk[3]
                to_column = fk[4]

                # Relationship naming as per Wren.ai examples
                rel_name = f"{self._pascal_case(from_table)}{self._pascal_case(to_table)}"

                # Wren.ai relationship structure
                '''TODO: Here to dynamically obtain the joinType information.
                Here Currently we have hardcoded MANY_TO_ONE,DUE To we are taking mschema.json converting Mdl.json
                IN MSCHEMA we don't have relationship type, so we are assuming it is MANY_TO_ONE,only foreign keys's available
                Challenge Here how to map  not available relationship type in mschema.json to mdl.json
                '''
                relationship = {
                    "name": rel_name,
                    "models": [
                        self._pascal_case(from_table),
                        self._pascal_case(to_table)
                    ],
                    "joinType": "MANY_TO_ONE",  # Foreign keys are typically MANY_TO_ONE
                    "condition": f"{self._pascal_case(from_table)}.{self._camel_case(from_column)} = {self._pascal_case(to_table)}.{self._camel_case(to_column)}"
                }

                self.relationships.append(relationship)

    def _add_relationship_columns(self):
        """Add relationship columns following Wren.ai pattern"""
        for relationship in self.relationships:
            rel_name = relationship["name"]
            from_model_name = relationship["models"][0]
            to_model_name = relationship["models"][1]

            # Find the source model and add relationship column
            for model in self.models:
                if model["name"] == from_model_name:
                    # Add relationship column (as shown in Wren.ai examples)
                    rel_column = {
                        "name": self._camel_case(to_model_name),
                        "type": to_model_name,
                        "relationship": rel_name  # This references the relationship name
                    }
                    model["columns"].append(rel_column)
                    break

    def _map_to_wren_type(self, mschema_type: str) -> str:
        """Map database types to Wren.ai MDL types"""
        # Based on Wren.ai examples, these are the common types used
        wren_type_mapping = {
            # Integer types
            "INTEGER": "integer",
            "INT": "integer",
            "BIGINT": "integer",
            "SMALLINT": "integer",
            "SERIAL": "integer",
            "BIGSERIAL": "integer",

            # String types
            "VARCHAR": "varchar",
            "CHAR": "varchar",
            "TEXT": "varchar",
            "CHARACTER VARYING": "varchar",

            # Numeric types
            "NUMERIC": "integer",  # Wren.ai examples use integer for numeric
            "DECIMAL": "integer",
            "REAL": "integer",
            "DOUBLE PRECISION": "integer",
            "FLOAT": "integer",

            # Date/Time types
            "DATE": "date",
            "TIME": "time",
            "TIMESTAMP": "timestamp",
            "TIMESTAMPTZ": "timestamp",

            # Boolean
            "BOOLEAN": "boolean",
            "BOOL": "boolean",

            # Other
            "UUID": "varchar",
            "JSON": "varchar",
            "JSONB": "varchar"
        }

        # Extract base type
        base_type = mschema_type.split("(")[0].upper().strip()

        # Return mapped type or default to varchar
        return wren_type_mapping.get(base_type, "varchar")

    def _pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase (following Wren.ai convention)"""
        if not snake_str:
            return ""
        components = snake_str.split('_')
        return ''.join(x.capitalize() for x in components if x)

    def _camel_case(self, snake_str: str) -> str:
        """Convert snake_case to camelCase (following Wren.ai convention)"""
        if not snake_str:
            return ""
        components = snake_str.split('_')
        if not components:
            return ""
        return components[0].lower() + ''.join(x.capitalize() for x in components[1:] if x)


# Usage Examples:

# Example 1: Direct instantiation with tableReference (default)
# converter = WrenMDLConverter(catalog="my_database", schema="public")

# Example 2: Direct instantiation with refSql
# converter = WrenMDLConverter(catalog="my_database", schema="public", use_table_reference=False)

# Example 3: Using configuration dictionary with tableReference
# config = {"catalog": "production_db", "schema": "public", "use_table_reference": "true"}
# converter = WrenMDLConverter.from_config(config)

# Example 4: Using configuration dictionary with refSql
# config = {"catalog": "production_db", "schema": "public", "use_table_reference": "false"}
# converter = WrenMDLConverter.from_config(config)

# Example 5: Complete usage
# converter = WrenMDLConverter(catalog="ecommerce_db", schema="public", use_table_reference=True)
# mdl_data = converter.convert_and_save("schema.json", "output.mdl.json")
# stats = converter.get_conversion_stats(mdl_data)
# print(f"Converted {stats['models']} models and {stats['relationships']} relationships")
