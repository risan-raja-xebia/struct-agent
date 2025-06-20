import pickle
from datasketch import MinHash, MinHashLSH
from pathlib import Path
from tqdm import tqdm
import logging
from typing import Dict, List, Any, Tuple

from sqlalchemy import text, inspect, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.types import String, Text

def _get_unique_values(engine: Engine, schema: str = None) -> Dict[str, Dict[str, List[str]]]:
    """
    Retrieves unique text values from the database excluding primary keys.
    Works with any database supported by SQLAlchemy.

    Args:
        engine: SQLAlchemy Engine object
        schema: The schema to use (optional)

    Returns:
        Dict[str, Dict[str, List[str]]]: A dictionary containing unique values for each table and column.
    """
    inspector = inspect(engine)
    metadata = MetaData(schema=schema) if schema else MetaData()
    metadata.reflect(bind=engine)
    # Get all table names in the specified schema
    table_names = inspector.get_table_names(schema=schema)
    # Get primary keys across all tables
    primary_keys = []
    for table_name in table_names:
        pk_constraint = inspector.get_pk_constraint(table_name, schema=schema)
        if pk_constraint and 'constrained_columns' in pk_constraint:
            primary_keys.extend(pk_constraint['constrained_columns'])
    unique_values: Dict[str, Dict[str, List[str]]] = {}
    with engine.connect() as connection:
        for table_name in table_names:
            # Skip system tables based on database type
            if table_name.lower() in ['sqlite_sequence', 'information_schema', 'pg_catalog']:
                continue
            logging.info(f"Processing {table_name}")
            # Get columns that are text-based and not primary keys
            columns_info = inspector.get_columns(table_name, schema=schema)
            text_columns = []
            for col in columns_info:
                col_name = col['name']
                col_type = col['type']
                # Check if column is text-based (works across different databases)
                if (isinstance(col_type, (String, Text)) or
                    str(col_type).upper() in ['TEXT', 'VARCHAR', 'CHAR', 'NVARCHAR', 'NCHAR', 'CLOB']):
                    if col_name.lower() not in [pk.lower() for pk in primary_keys]:
                        text_columns.append(col_name)
            table_values: Dict[str, List[str]] = {}
            for column in text_columns:
                # Skip columns with certain patterns
                if any(keyword in column.lower() for keyword in
                      ["_id", " id", "url", "email", "web", "time", "phone", "date", "address"]) or column.endswith("Id"):
                    continue
                try:
                    # Database-agnostic query for getting sum of lengths and count
                    # Handle different length functions for different databases
                    dialect_name = engine.dialect.name

                    if dialect_name == 'mssql':
                        length_func = 'LEN'
                    elif dialect_name == 'oracle':
                        length_func = 'LENGTH'
                    else:
                        length_func = 'LENGTH'

                    # Use proper identifier quoting for the specific database
                    if dialect_name == 'mysql':
                        quote_char = '`'
                    elif dialect_name == 'mssql':
                        quote_char = '['
                    else:
                        quote_char = '"'

                    # Compose fully qualified table name if schema is provided
                    if schema:
                        qualified_table = f'{quote_char}{schema}{quote_char}.{quote_char}{table_name}{quote_char}'
                    else:
                        qualified_table = f'{quote_char}{table_name}{quote_char}'

                    if dialect_name == 'mssql':
                        query = text(f"""
                            SELECT SUM({length_func}(unique_values)), COUNT(unique_values)
                            FROM (
                                SELECT DISTINCT [{column}] AS unique_values
                                FROM [{table_name}]
                                WHERE [{column}] IS NOT NULL
                            ) AS subquery
                        """)
                    else:
                        query = text(f"""
                            SELECT SUM({length_func}(unique_values)), COUNT(unique_values)
                            FROM (
                                SELECT DISTINCT {quote_char}{column}{quote_char} AS unique_values
                                FROM {qualified_table}
                                WHERE {quote_char}{column}{quote_char} IS NOT NULL
                            ) AS subquery
                        """)

                    result = connection.execute(query).fetchone()
                    sum_of_lengths, count_distinct = result
                except Exception as e:
                    logging.error(f"Error processing {table_name}.{column}: {e}")
                    sum_of_lengths, count_distinct = 0, 0

                if sum_of_lengths is None or count_distinct == 0:
                    continue

                average_length = sum_of_lengths / count_distinct
                logging.info(f"Column: {column}, sum_of_lengths: {sum_of_lengths}, "
                           f"count_distinct: {count_distinct}, average_length: {average_length}")

                # Decide whether to fetch values based on size
                if (("name" in column.lower() and sum_of_lengths < 5000000) or
                    (sum_of_lengths < 2000000 and average_length < 25) or
                    count_distinct < 100):

                    logging.info(f"Fetching distinct values for {column}")
                    try:
                        if dialect_name == 'mssql':
                            query = text(f"""
                                SELECT DISTINCT [{column}]
                                FROM [{table_name}]
                                WHERE [{column}] IS NOT NULL
                            """)
                        else:
                            query = text(f"""
                                SELECT DISTINCT {quote_char}{column}{quote_char}
                                FROM {qualified_table}
                                WHERE {quote_char}{column}{quote_char} IS NOT NULL
                            """)
                        result = connection.execute(query)
                        values = [str(row[0]) for row in result]
                        logging.info(f"Number of different values: {len(values)}")
                        table_values[column] = values
                    except Exception as e:
                        logging.error(f"Error fetching values for {table_name}.{column}: {e}")
                        values = []

            unique_values[table_name] = table_values

    return unique_values

def _create_minhash(signature_size: int, string: str, n_gram: int) -> MinHash:
    """
    Creates a MinHash object for a given string.

    Args:
        signature_size: The size of the MinHash signature
        string: The input string to create the MinHash for
        n_gram: The n-gram size for the MinHash

    Returns:
        MinHash: The MinHash object for the input string
    """
    m = MinHash(num_perm=signature_size)
    for d in [string[i:i + n_gram] for i in range(len(string) - n_gram + 1)]:
        m.update(d.encode('utf8'))
    return m

def skip_column(column_name: str, column_values: List[str]) -> bool:
    """
    Determines whether to skip processing a column based on its values.

    Args:
        column_name: The name of the column
        column_values: The list of values in the column

    Returns:
        bool: True if the column should be skipped, False otherwise
    """
    if "name" in column_name.lower():
        return False
    sum_of_lengths = sum(len(value) for value in column_values)
    average_length = sum_of_lengths / len(column_values)
    return (sum_of_lengths > 50000) and (average_length > 20)

def make_lsh(unique_values: Dict[str, Dict[str, List[str]]],
             signature_size: int, n_gram: int, threshold: float,
             verbose: bool = True) -> Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]:
    """
    Creates a MinHash LSH from unique values.

    Args:
        unique_values: The dictionary of unique values
        signature_size: The size of the MinHash signature
        n_gram: The n-gram size for the MinHash
        threshold: The threshold for the MinHash LSH
        verbose: Whether to display progress information

    Returns:
        Tuple[MinHashLSH, Dict]: The MinHash LSH object and the dictionary of MinHashes
    """
    lsh = MinHashLSH(threshold=threshold, num_perm=signature_size)
    minhashes: Dict[str, Tuple[MinHash, str, str, str]] = {}

    try:
        total_unique_values = sum(len(column_values)
                                 for table_values in unique_values.values()
                                 for column_values in table_values.values())
        logging.info(f"Total unique values: {total_unique_values}")

        progress_bar = tqdm(total=total_unique_values, desc="Creating LSH") if verbose else None

        for table_name, table_values in unique_values.items():
            for column_name, column_values in table_values.items():
                logging.info(f"Processing {table_name} - {column_name} - {len(column_values)}")

                for id, value in enumerate(column_values):
                    minhash = _create_minhash(signature_size, value, n_gram)
                    minhash_key = f"{table_name}_{column_name}_{id}"
                    minhashes[minhash_key] = (minhash, table_name, column_name, value)
                    lsh.insert(minhash_key, minhash)

                    if verbose:
                        progress_bar.update(1)

        if verbose:
            progress_bar.close()

    except Exception as e:
        logging.error(f"Error creating LSH: {e}")

    return lsh, minhashes

def make_db_lsh(engine: Engine, output_directory: str, db_name: str, schema: str = None, **lsh_kwargs: Any) -> None:
    """
    Creates a MinHash LSH for the database and saves the results.
    Works with any database supported by SQLAlchemy.

    Args:
        engine: SQLAlchemy Engine object
        output_directory: Directory to save the preprocessed files
        db_name: Name identifier for the database
        schema: The schema to use (optional)
        **lsh_kwargs: Additional arguments for LSH creation
    """
    preprocessed_path = Path(output_directory) / "preprocessed"
    preprocessed_path.mkdir(exist_ok=True, parents=True)

    # Get unique values from database
    unique_values = _get_unique_values(engine, schema=schema)
    logging.info("Unique values obtained")

    # Save unique values
    with open(preprocessed_path / f"{db_name}_unique_values.pkl", "wb") as file:
        pickle.dump(unique_values, file)
    logging.info("Saved unique values")

    # Create LSH
    lsh, minhashes = make_lsh(unique_values, **lsh_kwargs)

    # Save LSH and minhashes
    with open(preprocessed_path / f"{db_name}_lsh.pkl", "wb") as file:
        pickle.dump(lsh, file)
    with open(preprocessed_path / f"{db_name}_minhashes.pkl", "wb") as file:
        pickle.dump(minhashes, file)

    logging.info(f"LSH preprocessing completed for {db_name}")



'''

# Example usage
if __name__ == "__main__":
    from sqlalchemy import create_engine

    # User creates their own engine
    # For SQLite
    sqlite_engine = create_engine('sqlite:///path/to/database.db')
    make_db_lsh(sqlite_engine, "./output", "my_sqlite_db",
                signature_size=100, n_gram=3, threshold=0.8)

    # For PostgreSQL
    pg_engine = create_engine('postgresql://user:password@localhost/dbname')
    make_db_lsh(pg_engine, "./output", "my_postgres_db",
                signature_size=100, n_gram=3, threshold=0.8)

    # For MySQL
    mysql_engine = create_engine('mysql+pymysql://user:password@localhost/dbname')
    make_db_lsh(mysql_engine, "./output", "my_mysql_db",
                signature_size=100, n_gram=3, threshold=0.8)

'''
