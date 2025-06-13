from llama_index.core.prompts import PromptTemplate
from llama_index.core.prompts.prompt_type import PromptType

DEFAULT_IS_DATE_TIME_FIELD_TMPL = """You are a data analyst. Given information about a column in a data table, determine if the column is of date/time type. Only answer "Yes" or "No".
A date/time type is composed of one or more of year, month, day, hour, minute, or second. The month must be between 1-12, day between 1-31, hour between 0-23, and minute/second between 0-59.

{field_info_str}
"""

DEFAULT_IS_DATE_TIME_FIELD_PROMPT = PromptTemplate(
    DEFAULT_IS_DATE_TIME_FIELD_TMPL,
    prompt_type=PromptType.CUSTOM,
)

# Minimum granularity for date/time fields
DEFAULT_DATE_TIME_MIN_GRAN_TMPL = """You are a data analyst. Given a field in a data table that is related to date/time, infer the minimum time granularity based on its format and sample data.

Minimum time granularity refers to the smallest time unit the field can represent.

Common time units:
YEAR: e.g., 2024
MONTH: e.g., 2024-12
DAY: e.g., 2024-12-31
WEEK: e.g., 2024-34 (week number)
QUARTER: e.g., Q1, Q2, Q3, Q4
HOUR: e.g., 23 (hour of day)
MINUTE: e.g., 59 (minute of hour)
SECOND: e.g., 59 (second of minute)
MILLISECOND: millisecond
MICROSECOND: microsecond
OTHER: Other units not listed above (e.g., half-year, quarter-hour, etc.)

Directly provide the name of the minimum time unit.

Reference examples:
[Field Info]
Field Name: dt
Data Type: DOUBLE
Value Examples: [202412.0, 202301.0, 202411.0, 202201.0, 202308.0, 202110.0, 202211.0]
Minimum Time Unit: MONTH

[Field Info]
Field Name: dt
Data Type: TEXT
Value Examples: ['2022-12', '2022-14', '2021-40', '2021-37', '2021-01', '2021-32', '2023-04', '2023-37']
Minimum Time Unit: WEEK

[Field Info]
Field Name: dt
Data Type: TEXT
Value Examples: ['12:30:30', '23:45:23', '01:23:12', '12:12:12', '14:34:31', '18:43:01', '22:13:21']
Minimum Time Unit: SECOND

Based on the above examples, infer the minimum time unit for the following field. Directly provide the name of the minimum time unit.
[Field Info]
{field_info_str}
Minimum Time Unit: """

DEFAULT_DATE_TIME_MIN_GRAN_PROMPT = PromptTemplate(
    DEFAULT_DATE_TIME_MIN_GRAN_TMPL,
    prompt_type=PromptType.CUSTOM,
)


DEFAULT_STRING_CATEGORY_FIELD_TMPL = '''You are a data analyst. Given information about a column in a data table, determine if the column is of type "enum", "code", or "text". Only answer "enum", "code", or "text".

enum: Values are limited to a predefined set, usually short and fixed, often used for status or type fields.
code: Encoded values with specific meaning, often following a pattern or standard, e.g., user ID, ID number.
text: Free text, used for descriptions or notes, with no restriction on length or format.

{field_info_str}
'''

DEFAULT_STRING_CATEGORY_FIELD_PROMPT = PromptTemplate(
    DEFAULT_STRING_CATEGORY_FIELD_TMPL,
    prompt_type=PromptType.CUSTOM,
)

DEFAULT_NUMBER_CATEGORY_FIELD_TMPL = """You are a data analyst. Given information about a column in a data table, determine if the column is of type "enum", "code", or "measure". Only answer "enum", "code", or "measure".

enum: Values are limited to a predefined set, usually short, often used for status or type fields.
code: Encoded values with specific meaning, often following a pattern or standard, e.g., user ID, ID number.
measure: Metric or value used for calculation or aggregation, e.g., average, max, etc.

{field_info_str}
"""

DEFAULT_NUMBER_CATEGORY_FIELD_PROMPT = PromptTemplate(
    DEFAULT_NUMBER_CATEGORY_FIELD_TMPL,
    prompt_type=PromptType.CUSTOM,
)

DEFAULT_UNKNOWN_CATEGORY_FIELD_TMPL = """You are a data analyst. Given information about a column in a data table, determine if the column is of type "enum", "measure", "code", or "text". Only answer "enum", "measure", "code", or "text".

enum: Values are limited to a predefined set, usually short, often used for status or type fields.
code: Encoded values with specific meaning, often following a pattern or standard, e.g., user ID, ID number.
text: Free text, used for descriptions or notes, with no restriction on length or format.
measure: Metric or value used for calculation or aggregation, e.g., average, max, etc.

{field_info_str}
"""

DEFAULT_UNKNOWN_FIELD_PROMPT = PromptTemplate(
    DEFAULT_UNKNOWN_CATEGORY_FIELD_TMPL,
    prompt_type=PromptType.CUSTOM,
)

DEFAULT_COLUMN_DESC_GEN_CHINESE_TMPL = '''You are a data analyst. Given the following field information and sample data for a table:

{table_mschema}

[SQL]
{sql}
[Examples]
{sql_res}

Below is detailed information for the field "{field_name}":
{field_info_str}

Reference information:
{supp_info}

Please carefully review the above and provide a concise and accurate name for the field "{field_name}" that reflects its business meaning. Do not deviate from the original description. The name should not exceed 30 characters. Output in JSON format:
```json
{"chinese_name": ""}
```
'''

DEFAULT_COLUMN_DESC_GEN_CHINESE_PROMPT = PromptTemplate(
    DEFAULT_COLUMN_DESC_GEN_CHINESE_TMPL,
    prompt_type=PromptType.CUSTOM,
)

DEFAULT_COLUMN_DESC_GEN_ENGLISH_TMPL = '''You are a data analyst. Given the following field information and sample data for a table:

{table_mschema}

[SQL]
{sql}
[Examples]
{sql_res}

Below is detailed information for the field "{field_name}":
{field_info_str}

Reference information:
{supp_info}

Please carefully review the above and provide a concise and accurate English description for the field "{field_name}" that reflects its business meaning. Do not deviate from the original description. The description should not exceed 20 words. Output in JSON format:
```json
{"english_desc": ""}
```
'''

DEFAULT_COLUMN_DESC_GEN_ENGLISH_PROMPT = PromptTemplate(
    DEFAULT_COLUMN_DESC_GEN_ENGLISH_TMPL,
    prompt_type=PromptType.CUSTOM,
)


DEFAULT_UNDERSTAND_DATABASE_TMPL = '''You are a data analyst. Given the following database schema:

{db_mschema}

Carefully review the information and summarize, at the database level, what domain and type of data this database mainly stores. Do not analyze each table individually.
'''

DEFAULT_UNDERSTAND_DATABASE_PROMPT = PromptTemplate(
    DEFAULT_UNDERSTAND_DATABASE_TMPL,
    prompt_type=PromptType.CUSTOM,
)

DEFAULT_GET_DOMAIN_KNOWLEDGE_TMPL = '''Given a database with the following basic information:
{db_info}

Based on your knowledge, what dimensions and metrics are commonly of interest in this domain?
'''

DEFAULT_GET_DOMAIN_KNOWLEDGE_PROMPT = PromptTemplate(
    DEFAULT_GET_DOMAIN_KNOWLEDGE_TMPL,
    prompt_type=PromptType.CUSTOM,
)

# Understand the differences and relationships between fields by category
DEFAULT_UNDERSTAND_FIELDS_BY_CATEGORY_TMPL = '''You are a data analyst. Given the following basic information:

[Database Info]
{db_info}

The table "{table_name}" has the following field information and sample data:
{table_mschema}

[SQL]
{sql}
[Examples]
{sql_res}

Carefully review the table. The fields {fields} are all of category {category}. Analyze the relationships and differences among these fields.
'''

DEFAULT_UNDERSTAND_FIELDS_BY_CATEGORY_PROMPT = PromptTemplate(
    DEFAULT_UNDERSTAND_FIELDS_BY_CATEGORY_TMPL,
    prompt_type=PromptType.CUSTOM,
)

DEFAULT_TABLE_DESC_GEN_CHINESE_TMPL = '''You are a data analyst. Given the following field information for a table:

{table_mschema}

Sample data:
[SQL]
{sql}
[Examples]
{sql_res}

Carefully review the above and generate a concise description for the table, specifying what metrics are stored and on which dimensions (including time and other dimensions). Limit your answer to 200 characters. Output in JSON format.

```json
{"table_desc": ""}
```
'''

DEFAULT_TABLE_DESC_GEN_CHINESE_PROMPT = PromptTemplate(
    DEFAULT_TABLE_DESC_GEN_CHINESE_TMPL,
    prompt_type=PromptType.CUSTOM,
)

DEFAULT_TABLE_DESC_GEN_ENGLISH_TMPL = '''You are a data analyst. Given the following field information for a table:

{table_mschema}

Sample data:
[SQL]
{sql}
[Examples]
{sql_res}

Carefully review the above and generate a concise description for the table, specifying what metrics are stored and on which dimensions (including time and other dimensions). Limit your answer to 100 words. Output in JSON format.

```json
{"table_desc": ""}
```
'''

DEFAULT_TABLE_DESC_GEN_ENGLISH_PROMPT = PromptTemplate(
    DEFAULT_TABLE_DESC_GEN_ENGLISH_TMPL,
    prompt_type=PromptType.CUSTOM,
)

DEFAULT_SQL_GEN_TMPL = '''You are a {dialect} data analyst. Given the following database schema:

[Database Schema]
{db_mschema}

[User Question]
{question}
[Reference Information]
{evidence}

Carefully review the database and, based on the user question and reference information, generate an executable SQL statement to answer the question. Enclose the SQL in ```sql and ```.
'''

DEFAULT_SQL_GEN_PROMPT = PromptTemplate(
    DEFAULT_SQL_GEN_TMPL,
    prompt_type=PromptType.CUSTOM,
)

