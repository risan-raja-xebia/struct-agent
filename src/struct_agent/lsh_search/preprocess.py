import pickle
from datasketch import MinHash, MinHashLSH
from pathlib import Path
from tqdm import tqdm
import logging
from typing import Dict, List, Any, Tuple

from .execution import execute_sql, DatabaseType, detect_database_type

def _get_table_names(db_connection_string: str, db_type: DatabaseType = None) -> List[str]:
    """
    Gets table names from the database.

    Args:
        db_connection_string (str): Database connection string
        db_type (DatabaseType, optional): Database type

    Returns:
        List[str]: List of table names
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    if db_type == DatabaseType.SQLITE:
        query = "SELECT name FROM sqlite_master WHERE type='table';"
    elif db_type == DatabaseType.POSTGRESQL:
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    result = execute_sql(db_connection_string, query, fetch="all", db_type=db_type)
    return [table[0] for table in result]

def _get_table_columns(db_connection_string: str, table_name: str,
                      db_type: DatabaseType = None) -> List[Tuple]:
    """
    Gets column information for a specific table.

    Args:
        db_connection_string (str): Database connection string
        table_name (str): Name of the table
        db_type (DatabaseType, optional): Database type

    Returns:
        List[Tuple]: List of column information tuples
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    if db_type == DatabaseType.SQLITE:
        query = f"PRAGMA table_info('{table_name}')"
    elif db_type == DatabaseType.POSTGRESQL:
        query = f"""
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            ordinal_position,
            CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 1 ELSE 0 END as is_primary_key
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu
            ON c.table_name = kcu.table_name AND c.column_name = kcu.column_name
        LEFT JOIN information_schema.table_constraints tc
            ON kcu.constraint_name = tc.constraint_name AND tc.constraint_type = 'PRIMARY KEY'
        WHERE c.table_name = '{table_name}' AND c.table_schema = 'public'
        ORDER BY c.ordinal_position;
        """
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    return execute_sql(db_connection_string, query, fetch="all", db_type=db_type)

def _get_primary_keys(db_connection_string: str, db_type: DatabaseType = None) -> List[str]:
    """
    Gets primary key column names from all tables.

    Args:
        db_connection_string (str): Database connection string
        db_type (DatabaseType, optional): Database type

    Returns:
        List[str]: List of primary key column names
    """
    table_names = _get_table_names(db_connection_string, db_type)
    primary_keys = []

    for table_name in table_names:
        if db_type == DatabaseType.SQLITE and table_name == "sqlite_sequence":
            continue

        columns = _get_table_columns(db_connection_string, table_name, db_type)

        for column in columns:
            if db_type == DatabaseType.SQLITE:
                # SQLite: column format is (cid, name, type, notnull, dflt_value, pk)
                if len(column) > 5 and column[5] > 0:  # Check if it's a primary key
                    column_name = column[1]
                    if column_name.lower() not in [c.lower() for c in primary_keys]:
                        primary_keys.append(column_name)
            elif db_type == DatabaseType.POSTGRESQL:
                # PostgreSQL: last column is is_primary_key
                if len(column) > 5 and column[5] == 1:  # is_primary_key = 1
                    column_name = column[0]  # column_name is first
                    if column_name.lower() not in [c.lower() for c in primary_keys]:
                        primary_keys.append(column_name)

    return primary_keys

def _is_text_column(column_info: Tuple, db_type: DatabaseType) -> bool:
    """
    Determines if a column contains text data.

    Args:
        column_info (Tuple): Column information tuple
        db_type (DatabaseType): Database type

    Returns:
        bool: True if column contains text data
    """
    if db_type == DatabaseType.SQLITE:
        # SQLite: column format is (cid, name, type, notnull, dflt_value, pk)
        return "TEXT" in column_info[2].upper()
    elif db_type == DatabaseType.POSTGRESQL:
        # PostgreSQL: column format includes data_type at index 1
        data_type = column_info[1].lower()
        return data_type in ['text', 'varchar', 'character varying', 'char', 'character']
    return False

def _get_unique_values(db_connection_string: str, db_type: DatabaseType = None) -> Dict[str, Dict[str, List[str]]]:
    """
    Retrieves unique text values from the database excluding primary keys.

    Args:
        db_connection_string (str): Database connection string
        db_type (DatabaseType, optional): Database type

    Returns:
        Dict[str, Dict[str, List[str]]]: A dictionary containing unique values for each table and column.
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    table_names = _get_table_names(db_connection_string, db_type)
    primary_keys = _get_primary_keys(db_connection_string, db_type)

    unique_values: Dict[str, Dict[str, List[str]]] = {}

    for table_name in table_names:
        if db_type == DatabaseType.SQLITE and table_name == "sqlite_sequence":
            continue

        logging.info(f"Processing {table_name}")
        columns_info = _get_table_columns(db_connection_string, table_name, db_type)

        # Filter text columns that are not primary keys
        text_columns = []
        for col_info in columns_info:
            if db_type == DatabaseType.SQLITE:
                column_name = col_info[1]
            else:  # PostgreSQL
                column_name = col_info[0]

            if (_is_text_column(col_info, db_type) and
                column_name.lower() not in [c.lower() for c in primary_keys]):
                text_columns.append(column_name)

        table_values: Dict[str, List[str]] = {}

        for column in text_columns:
            # Skip columns that likely contain IDs or system data
            if any(keyword in column.lower() for keyword in ["_id", " id", "url", "email", "web", "time", "phone", "date", "address"]) or column.endswith("Id"):
                continue

            try:
                # Use proper SQL identifier quoting for each database type
                if db_type == DatabaseType.SQLITE:
                    column_ref = f"`{column}`"
                    table_ref = f"`{table_name}`"
                else:  # PostgreSQL
                    column_ref = f'"{column}"'
                    table_ref = f'"{table_name}"'

                result = execute_sql(db_connection_string, f"""
                    SELECT SUM(LENGTH(unique_values)), COUNT(unique_values)
                    FROM (
                        SELECT DISTINCT {column_ref} AS unique_values
                        FROM {table_ref}
                        WHERE {column_ref} IS NOT NULL
                    ) AS subquery
                """, fetch="one", timeout=480, db_type=db_type)
            except Exception as e:
                logging.warning(f"Error calculating statistics for {table_name}.{column}: {e}")
                result = (0, 0)

            sum_of_lengths, count_distinct = result
            if sum_of_lengths is None or count_distinct == 0:
                continue

            average_length = sum_of_lengths / count_distinct
            logging.info(f"Column: {column}, sum_of_lengths: {sum_of_lengths}, count_distinct: {count_distinct}, average_length: {average_length}")

            # Determine if we should fetch distinct values
            should_fetch = (
                ("name" in column.lower() and sum_of_lengths < 5000000) or
                (sum_of_lengths < 2000000 and average_length < 25) or
                count_distinct < 100
            )

            if should_fetch:
                logging.info(f"Fetching distinct values for {column}")
                try:
                    if db_type == DatabaseType.SQLITE:
                        column_ref = f"`{column}`"
                        table_ref = f"`{table_name}`"
                    else:  # PostgreSQL
                        column_ref = f'"{column}"'
                        table_ref = f'"{table_name}"'

                    values_result = execute_sql(db_connection_string,
                        f"SELECT DISTINCT {column_ref} FROM {table_ref} WHERE {column_ref} IS NOT NULL",
                        fetch="all", timeout=480, db_type=db_type)

                    values = [str(value[0]) for value in values_result]
                except Exception as e:
                    logging.warning(f"Error fetching distinct values for {table_name}.{column}: {e}")
                    values = []

                logging.info(f"Number of different values: {len(values)}")
                table_values[column] = values

        unique_values[table_name] = table_values

    return unique_values

def _create_minhash(signature_size: int, string: str, n_gram: int) -> MinHash:
    """
    Creates a MinHash object for a given string.

    Args:
        signature_size (int): The size of the MinHash signature.
        string (str): The input string to create the MinHash for.
        n_gram (int): The n-gram size for the MinHash.

    Returns:
        MinHash: The MinHash object for the input string.
    """
    m = MinHash(num_perm=signature_size)
    for d in [string[i:i + n_gram] for i in range(len(string) - n_gram + 1)]:
        m.update(d.encode('utf8'))
    return m

def skip_column(column_name: str, column_values: List[str]) -> bool:
    """
    Determines whether to skip processing a column based on its values.

    Args:
        column_name (str): The name of the column.
        column_values (List[str]): The list of values in the column.

    Returns:
        bool: True if the column should be skipped, False otherwise.
    """
    if "name" in column_name.lower():
        return False
    sum_of_lengths = sum(len(value) for value in column_values)
    average_length = sum_of_lengths / len(column_values) if column_values else 0
    return (sum_of_lengths > 50000) and (average_length > 20)

def make_lsh(unique_values: Dict[str, Dict[str, List[str]]], signature_size: int, n_gram: int,
            threshold: float, verbose: bool = True) -> Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]:
    """
    Creates a MinHash LSH from unique values.

    Args:
        unique_values (Dict[str, Dict[str, List[str]]]): The dictionary of unique values.
        signature_size (int): The size of the MinHash signature.
        n_gram (int): The n-gram size for the MinHash.
        threshold (float): The threshold for the MinHash LSH.
        verbose (bool): Whether to display progress information.

    Returns:
        Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]: The MinHash LSH object and the dictionary of MinHashes.
    """
    lsh = MinHashLSH(threshold=threshold, num_perm=signature_size)
    minhashes: Dict[str, Tuple[MinHash, str, str, str]] = {}
    try:
        total_unique_values = sum(len(column_values) for table_values in unique_values.values() for column_values in table_values.values())
        logging.info(f"Total unique values: {total_unique_values}")

        progress_bar = tqdm(total=total_unique_values, desc="Creating LSH") if verbose else None

        for table_name, table_values in unique_values.items():
            for column_name, column_values in table_values.items():
                if column_name.lower() == "doctype":
                    print("="*20)
                    print("Doctype found")
                    print("="*20)
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

def make_db_lsh(db_connection_string: str, db_type: DatabaseType = None, **kwargs: Any) -> None:
    """
    Creates a MinHash LSH for the database and saves the results.

    Args:
        db_connection_string (str): Database connection string
        db_type (DatabaseType, optional): Database type
        **kwargs (Any): Additional arguments for the LSH creation.
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    # For file-based databases like SQLite, use the file path structure
    if db_type == DatabaseType.SQLITE:
        db_directory_path = Path(db_connection_string).parent
        db_id = Path(db_connection_string).stem
    else:
        # For PostgreSQL, create a directory structure based on connection details
        # Extract database name from connection string for directory naming
        if 'dbname=' in db_connection_string:
            db_id = db_connection_string.split('dbname=')[1].split()[0].split('&')[0]
        elif '/' in db_connection_string and db_connection_string.count('/') >= 3:
            db_id = db_connection_string.split('/')[-1].split('?')[0]
        else:
            db_id = "postgresql_db"

        # Create a base directory for PostgreSQL databases
        db_directory_path = Path(f"./postgresql_dbs/{db_id}")

    preprocessed_path = db_directory_path / "preprocessed"
    preprocessed_path.mkdir(parents=True, exist_ok=True)

    unique_values = _get_unique_values(db_connection_string, db_type)
    logging.info("Unique values obtained")

    with open(preprocessed_path / f"{db_id}_unique_values.pkl", "wb") as file:
        pickle.dump(unique_values, file)
    logging.info("Saved unique values")

    lsh, minhashes = make_lsh(unique_values, **kwargs)

    with open(preprocessed_path / f"{db_id}_lsh.pkl", "wb") as file:
        pickle.dump(lsh, file)
    with open(preprocessed_path / f"{db_id}_minhashes.pkl", "wb") as file:
        pickle.dump(minhashes, file)

    logging.info(f"LSH and MinHashes saved for {db_type.value} database: {db_id}")
