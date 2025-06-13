from .utils import examples_to_str, read_json, write_json
from .type_engine import TypeEngine
from typing import Any, Dict, List, Optional


class MSchema:
    def __init__(self, db_id: str = 'Anonymous', type_engine: Optional[TypeEngine] = None,
                 schema: Optional[str] = None):
        self.db_id = db_id
        self.schema = schema
        self.tables = {}
        self.foreign_keys = []
        self.type_engine = type_engine

    def add_table(self, name, fields={}, comment=None):
        self.tables[name] = {"fields": fields.copy(), 'examples': [], 'comment': comment}

    def add_field(self, table_name: str, field_name: str, field_type: str = "",
            primary_key: bool = False, nullable: bool = True, default: Any = None,
            autoincrement: bool = False, unique: bool = False,
            comment: str = "",
            examples: list = [], category: str = '', dim_or_meas: Optional[str] = '', **kwargs):
        self.tables[table_name]["fields"][field_name] = {
            "type": field_type,
            "primary_key": primary_key,
            "nullable": nullable,
            "default": default if default is None else f'{default}',
            "autoincrement": autoincrement,
            "unique": unique,
            "comment": comment,
            "examples": examples.copy(),
            "category": category,
            "dim_or_meas": dim_or_meas,
            **kwargs}

    def add_foreign_key(self, table_name, field_name, ref_schema, ref_table_name, ref_field_name):
        self.foreign_keys.append([table_name, field_name, ref_schema, ref_table_name, ref_field_name])

    def get_abbr_field_type(self, field_type, simple_mode=True)->str:
        if not simple_mode:
            return field_type
        else:
            return field_type.split("(")[0]

    def erase_all_table_comment(self):
        """Clear all table descriptions."""
        for table_name in self.tables.keys():
            self.tables[table_name]['comment'] = ''

    def erase_all_column_comment(self):
        """Clear all column descriptions."""
        for table_name in self.tables.keys():
            fields = self.tables[table_name]['fields']
            for field_name, field_info in fields.items():
                self.tables[table_name]['fields'][field_name]['comment'] = ''

    def has_table(self, table_name: str) -> bool:
        """Check if the given table_name exists in M-Schema."""
        if table_name in self.tables.keys():
            return True
        else:
            return False

    def has_column(self, table_name: str, field_name: str) -> bool:
        if self.has_table(table_name):
            if field_name in self.tables[table_name]["fields"].keys():
                return True
            else:
                return False
        else:
            return False

    def set_table_property(self, table_name: str, key: str, value: Any):
        if not self.has_table(table_name):
            print("The table name {} does not exist in M-Schema.".format(table_name))
        else:
            self.tables[table_name][key] = value

    def set_column_property(self, table_name: str, field_name: str, key: str, value: Any):
        if not self.has_column(table_name, field_name):
            print("The table name {} or column name {} does not exist in M-Schema.".format(table_name, field_name))
        else:
            self.tables[table_name]['fields'][field_name][key] = value

    def get_field_info(self, table_name: str, field_name: str) -> Dict:
        try:
            return self.tables[table_name]['fields'][field_name]
        except Exception as e:  # noqa: F841
            return {}

    def get_category_fields(self, category: str, table_name: str) -> List:
        """
        Given table_name and category, get all field names of the specified category in the current table.
        category: Value should be from type_engine.field_category_all_labels
        """
        assert category in self.type_engine.field_category_all_labels, \
                        'Invalid category {}'.format(category)
        if self.has_table(table_name):
            res = []
            fields = self.tables[table_name]['fields']
            for field_name, field_info in fields.items():
                _ = field_info.get('category', '')
                if _ == category:
                    res.append(field_name)
            return res
        else:
            return []

    def get_dim_or_meas_fields(self, dim_or_meas: str, table_name: str) -> List:
        """Given dim_or_meas and table_name, get all field names of the specified type in the current table."""
        assert dim_or_meas in self.type_engine.dim_measure_labels, 'Invalid dim_or_meas {}'.format(dim_or_meas)
        if self.has_table(table_name):
            res = []
            fields = self.tables[table_name]['fields']
            for field_name, field_info in fields.items():
                _ = field_info.get('dim_or_meas', '')
                if _ == dim_or_meas:
                    res.append(field_name)
            return res
        else:
            return []

    def single_table_mschema(self, table_name: str, selected_columns: Optional[List] = None, example_num=3, show_type_detail=False) -> str:
        table_info = self.tables.get(table_name, {})
        output = []
        table_comment = table_info.get('comment', '')
        if table_comment is not None and table_comment != 'None' and len(table_comment) > 0:
            if self.schema is not None and len(self.schema) > 0:
                output.append(f"# Table: {self.schema}.{table_name}, {table_comment}")
            else:
                output.append(f"# Table: {table_name}, {table_comment}")
        else:
            if self.schema is not None and len(self.schema) > 0:
                output.append(f"# Table: {self.schema}.{table_name}")
            else:
                output.append(f"# Table: {table_name}")

        field_lines = []
        # Process each field in the table
        for field_name, field_info in table_info['fields'].items():
            if selected_columns is not None and field_name.lower() not in selected_columns:
                continue

            raw_type = self.get_abbr_field_type(field_info['type'], not show_type_detail)
            field_line = f"({field_name}:{raw_type.upper()}"
            if len(field_info['comment']) > 0:
                field_line += f", {field_info['comment'].strip()}"

            ## Mark as primary key
            is_primary_key = field_info.get('primary_key', False)
            if is_primary_key:
                field_line += ", Primary Key"

            # If there are examples, add them
            if len(field_info.get('examples', [])) > 0 and example_num > 0:
                examples = field_info['examples']
                examples = [s for s in examples if s is not None]
                examples = examples_to_str(examples)
                if len(examples) > example_num:
                    examples = examples[:example_num]

                if raw_type in ['DATE', 'TIME', 'DATETIME', 'TIMESTAMP']:
                    examples = [examples[0]]
                elif len(examples) > 0 and max([len(s) for s in examples]) > 20:
                    if max([len(s) for s in examples]) > 50:
                        examples = []
                    else:
                        examples = [examples[0]]
                else:
                    pass
                if len(examples) > 0:
                    example_str = ', '.join([str(example) for example in examples])
                    field_line += f", Examples: [{example_str}]"
                else:
                    pass
            else:
                field_line += ""
            field_line += ")"

            field_lines.append(field_line)
        output.append('[')
        output.append(',\n'.join(field_lines))
        output.append(']')

        return '\n'.join(output)

    def to_mschema(self, selected_tables: List = None, selected_columns: List = None,
                   example_num=3, show_type_detail=False) -> str:
        """
        Convert to a MSchema string.
        selected_tables: Default is None, which means all tables are selected
        selected_columns: Default is None, which means all columns are selected, format ['table_name.column_name']
        """
        output = []

        output.append(f"【DB_ID】 {self.db_id}")
        output.append("【Schema】")

        if selected_tables is not None:
            selected_tables = [s.lower() for s in selected_tables]
        if selected_columns is not None:
            selected_columns = [s.lower() for s in selected_columns]
            selected_tables = [s.split('.')[0].lower() for s in selected_columns]

        # Process each table in order
        for table_name, table_info in self.tables.items():
            if selected_tables is None or table_name.lower() in selected_tables:
                column_names = list(table_info['fields'].keys())
                if selected_columns is not None:
                    cur_selected_columns = [c for c in column_names if f"{table_name}.{c}".lower() in selected_columns]
                else:
                    cur_selected_columns = selected_columns
                output.append(self.single_table_mschema(table_name, cur_selected_columns, example_num, show_type_detail))

        # Add foreign key information, do not display foreign keys when table_type is view
        if self.foreign_keys:
            output.append("【Foreign keys】")
            for fk in self.foreign_keys:
                ref_schema = fk[2]
                table1, column1, _, table2, column2 = fk
                if selected_tables is None or \
                        (table1.lower() in selected_tables and table2.lower() in selected_tables):
                    if ref_schema == self.schema:
                        output.append(f"{fk[0]}.{fk[1]}={fk[3]}.{fk[4]}")

        return '\n'.join(output)

    def dump(self):
        schema_dict = {
            "db_id": self.db_id,
            "schema": self.schema,
            "tables": self.tables,
            "foreign_keys": self.foreign_keys
        }
        return schema_dict

    def save(self, file_path: str):
        schema_dict = self.dump()
        write_json(file_path, schema_dict)

    def load(self, file_path: str):
        data = read_json(file_path)
        self.db_id = data.get("db_id", "Anonymous")
        self.schema = data.get("schema", None)
        self.tables = data.get("tables", {})
        self.foreign_keys = data.get("foreign_keys", [])
