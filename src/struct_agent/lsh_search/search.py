import pickle
from datasketch import MinHash, MinHashLSH
from pathlib import Path
import logging
from typing import Dict, Tuple, List

from .preprocess import _create_minhash
from .execution import DatabaseType, detect_database_type

### Database value similarity ###

def _jaccard_similarity(m1: MinHash, m2: MinHash) -> float:
    """
    Computes the Jaccard similarity between two MinHash objects.

    Args:
        m1 (MinHash): The first MinHash object.
        m2 (MinHash): The second MinHash object.

    Returns:
        float: The Jaccard similarity between the two MinHash objects.
    """
    return m1.jaccard(m2)

def _get_db_directory_path(db_connection_string: str, db_type: DatabaseType = None) -> Path:
    """
    Gets the directory path for storing preprocessed files based on database type.

    Args:
        db_connection_string (str): Database connection string
        db_type (DatabaseType, optional): Database type

    Returns:
        Path: Directory path for preprocessed files
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    if db_type == DatabaseType.SQLITE:
        return Path(db_connection_string).parent
    else:
        # For PostgreSQL, use the same logic as in preprocess.py
        if 'dbname=' in db_connection_string:
            db_id = db_connection_string.split('dbname=')[1].split()[0].split('&')[0]
        elif '/' in db_connection_string and db_connection_string.count('/') >= 3:
            db_id = db_connection_string.split('/')[-1].split('?')[0]
        else:
            db_id = "postgresql_db"

        return Path(f"./postgresql_dbs/{db_id}")

def _get_db_id(db_connection_string: str, db_type: DatabaseType = None) -> str:
    """
    Gets the database ID for file naming based on database type.

    Args:
        db_connection_string (str): Database connection string
        db_type (DatabaseType, optional): Database type

    Returns:
        str: Database ID for file naming
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    if db_type == DatabaseType.SQLITE:
        return Path(db_connection_string).stem
    else:
        # For PostgreSQL, extract database name
        if 'dbname=' in db_connection_string:
            return db_connection_string.split('dbname=')[1].split()[0].split('&')[0]
        elif '/' in db_connection_string and db_connection_string.count('/') >= 3:
            return db_connection_string.split('/')[-1].split('?')[0]
        else:
            return "postgresql_db"

def load_db_lsh(db_connection_string: str, db_type: DatabaseType = None) -> Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]:
    """
    Loads the LSH and MinHashes from the preprocessed files.

    Args:
        db_connection_string (str): Database connection string
        db_type (DatabaseType, optional): Database type

    Returns:
        Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]: The LSH object and the dictionary of MinHashes.

    Raises:
        Exception: If there is an error loading the LSH or MinHashes.
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    db_directory_path = _get_db_directory_path(db_connection_string, db_type)
    db_id = _get_db_id(db_connection_string, db_type)

    try:
        lsh_file_path = db_directory_path / "preprocessed" / f"{db_id}_lsh.pkl"
        minhashes_file_path = db_directory_path / "preprocessed" / f"{db_id}_minhashes.pkl"

        if not lsh_file_path.exists():
            raise FileNotFoundError(f"LSH file not found: {lsh_file_path}")
        if not minhashes_file_path.exists():
            raise FileNotFoundError(f"MinHashes file not found: {minhashes_file_path}")

        with open(lsh_file_path, "rb") as file:
            lsh = pickle.load(file)
        with open(minhashes_file_path, "rb") as file:
            minhashes = pickle.load(file)

        logging.info(f"Successfully loaded LSH for {db_type.value} database: {db_id}")
        return lsh, minhashes

    except Exception as e:
        logging.error(f"Error loading LSH for {db_type.value} database {db_id}: {e}")
        raise e

def load_db_lsh_legacy(db_directory_path: str) -> Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]:
    """
    Legacy function to load LSH from directory path (backwards compatibility).

    Args:
        db_directory_path (str): The path to the database directory.

    Returns:
        Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]: The LSH object and the dictionary of MinHashes.

    Raises:
        Exception: If there is an error loading the LSH or MinHashes.
    """
    db_id = Path(db_directory_path).name
    try:
        with open(Path(db_directory_path) / "preprocessed" / f"{db_id}_lsh.pkl", "rb") as file:
            lsh = pickle.load(file)
        with open(Path(db_directory_path) / "preprocessed" / f"{db_id}_minhashes.pkl", "rb") as file:
            minhashes = pickle.load(file)
        return lsh, minhashes
    except Exception as e:
        logging.error(f"Error loading LSH for {db_id}: {e}")
        raise e

def query_lsh(lsh: MinHashLSH, minhashes: Dict[str, Tuple[MinHash, str, str, str]], keyword: str,
              signature_size: int = 100, n_gram: int = 3, top_n: int = 10) -> Dict[str, Dict[str, List[str]]]:
    """
    Queries the LSH for similar values to the given keyword and returns the top results.

    Args:
        lsh (MinHashLSH): The LSH object.
        minhashes (Dict[str, Tuple[MinHash, str, str, str]]): The dictionary of MinHashes.
        keyword (str): The keyword to search for.
        signature_size (int, optional): The size of the MinHash signature.
        n_gram (int, optional): The n-gram size for the MinHash.
        top_n (int, optional): The number of top results to return.

    Returns:
        Dict[str, Dict[str, List[str]]]: A dictionary containing the top similar values.
    """
    query_minhash = _create_minhash(signature_size, keyword, n_gram)
    results = lsh.query(query_minhash)
    similarities = [(result, _jaccard_similarity(query_minhash, minhashes[result][0])) for result in results]
    similarities = sorted(similarities, key=lambda x: x[1], reverse=True)[:top_n]

    similar_values_trimmed: Dict[str, Dict[str, List[str]]] = {}
    for result, similarity in similarities:
        table_name, column_name, value = minhashes[result][1:]
        if table_name not in similar_values_trimmed:
            similar_values_trimmed[table_name] = {}
        if column_name not in similar_values_trimmed[table_name]:
            similar_values_trimmed[table_name][column_name] = []
        similar_values_trimmed[table_name][column_name].append(value)

    return similar_values_trimmed

def search_database_values(db_connection_string: str, keyword: str,
                          signature_size: int = 100, n_gram: int = 3, top_n: int = 10,
                          db_type: DatabaseType = None) -> Dict[str, Dict[str, List[str]]]:
    """
    High-level function to search for similar values in a database.

    Args:
        db_connection_string (str): Database connection string
        keyword (str): The keyword to search for
        signature_size (int, optional): The size of the MinHash signature
        n_gram (int, optional): The n-gram size for the MinHash
        top_n (int, optional): The number of top results to return
        db_type (DatabaseType, optional): Database type

    Returns:
        Dict[str, Dict[str, List[str]]]: A dictionary containing the top similar values
    """
    try:
        lsh, minhashes = load_db_lsh(db_connection_string, db_type)
        return query_lsh(lsh, minhashes, keyword, signature_size, n_gram, top_n)
    except Exception as e:
        logging.error(f"Error searching database values: {e}")
        raise e

def get_unique_values_from_file(db_connection_string: str, db_type: DatabaseType = None) -> Dict[str, Dict[str, List[str]]]:
    """
    Loads unique values from preprocessed file.

    Args:
        db_connection_string (str): Database connection string
        db_type (DatabaseType, optional): Database type

    Returns:
        Dict[str, Dict[str, List[str]]]: Dictionary of unique values
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    db_directory_path = _get_db_directory_path(db_connection_string, db_type)
    db_id = _get_db_id(db_connection_string, db_type)

    try:
        unique_values_file = db_directory_path / "preprocessed" / f"{db_id}_unique_values.pkl"

        if not unique_values_file.exists():
            raise FileNotFoundError(f"Unique values file not found: {unique_values_file}")

        with open(unique_values_file, "rb") as file:
            unique_values = pickle.load(file)

        logging.info(f"Successfully loaded unique values for {db_type.value} database: {db_id}")
        return unique_values

    except Exception as e:
        logging.error(f"Error loading unique values for {db_type.value} database {db_id}: {e}")
        raise e
