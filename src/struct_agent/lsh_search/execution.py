import sqlite3
import psycopg2
import psycopg2.extras
import random
import logging
from typing import Any, Union, List, Dict
from func_timeout import func_timeout, FunctionTimedOut
from multiprocessing import Process, Queue
import threading
from queue import Empty
from enum import Enum
import os
from urllib.parse import urlparse
# from sqlglot import parse_one, exp

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

class TimeoutException(Exception):
    pass

def detect_database_type(db_connection_string: str) -> DatabaseType:
    """
    Detects the database type from the connection string.

    Args:
        db_connection_string (str): Database connection string or file path

    Returns:
        DatabaseType: The detected database type
    """
    if db_connection_string.startswith(('postgresql://', 'postgres://')):
        return DatabaseType.POSTGRESQL
    elif db_connection_string.startswith('sqlite://'):
        return DatabaseType.SQLITE
    elif db_connection_string.endswith('.sqlite') or db_connection_string.endswith('.db') or os.path.isfile(db_connection_string):
        return DatabaseType.SQLITE
    elif '://' in db_connection_string:
        parsed = urlparse(db_connection_string)
        if parsed.scheme in ['postgresql', 'postgres']:
            return DatabaseType.POSTGRESQL
    else:
        # Default to SQLite if unclear
        return DatabaseType.SQLITE

def get_database_connection(db_connection_string: str, db_type: DatabaseType = None):
    """
    Creates a database connection based on the connection string and type.

    Args:
        db_connection_string (str): Database connection string or file path
        db_type (DatabaseType, optional): Database type. If None, will be auto-detected

    Returns:
        Database connection object
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    if db_type == DatabaseType.SQLITE:
        return sqlite3.connect(db_connection_string, timeout=60)
    elif db_type == DatabaseType.POSTGRESQL:
        return psycopg2.connect(db_connection_string)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

def execute_sql(db_connection_string: str, sql: str, fetch: Union[str, int] = "all",
                timeout: int = 60, db_type: DatabaseType = None) -> Any:
    """
    Executes an SQL query on a database and fetches results.

    Args:
        db_connection_string (str): Database connection string or file path
        sql (str): The SQL query to execute
        fetch (Union[str, int]): How to fetch the results. Options are "all", "one", "random", or an integer
        timeout (int): Timeout in seconds
        db_type (DatabaseType, optional): Database type. If None, will be auto-detected

    Returns:
        Any: The fetched results based on the fetch argument
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    class QueryThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = None
            self.exception = None

        def run(self):
            try:
                with get_database_connection(db_connection_string, db_type) as conn:
                    if db_type == DatabaseType.POSTGRESQL:
                        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    else:
                        cursor = conn.cursor()

                    cursor.execute(sql)

                    if fetch == "all":
                        self.result = cursor.fetchall()
                    elif fetch == "one":
                        self.result = cursor.fetchone()
                    elif fetch == "random":
                        samples = cursor.fetchmany(10)
                        self.result = random.choice(samples) if samples else []
                    elif isinstance(fetch, int):
                        self.result = cursor.fetchmany(fetch)
                    else:
                        raise ValueError("Invalid fetch argument. Must be 'all', 'one', 'random', or an integer.")

                    # Convert PostgreSQL results to list of tuples for consistency
                    if db_type == DatabaseType.POSTGRESQL and self.result:
                        if isinstance(self.result, list):
                            self.result = [tuple(row.values()) if hasattr(row, 'values') else row for row in self.result]
                        elif hasattr(self.result, 'values'):
                            self.result = tuple(self.result.values())

            except Exception as e:
                self.exception = e

    query_thread = QueryThread()
    query_thread.start()
    query_thread.join(timeout)

    if query_thread.is_alive():
        raise TimeoutError(f"SQL query execution exceeded the timeout of {timeout} seconds.")
    if query_thread.exception:
        raise query_thread.exception
    return query_thread.result

def _clean_sql(sql: str, db_type: DatabaseType = DatabaseType.SQLITE) -> str:
    """
    Cleans the SQL query by removing unwanted characters and whitespace.
    Also converts SQLite-specific syntax to PostgreSQL if needed.

    Args:
        sql (str): The SQL query string
        db_type (DatabaseType): The target database type

    Returns:
        str: The cleaned SQL query string
    """
    cleaned_sql = sql.replace('\n', ' ').strip("`.")

    if db_type == DatabaseType.POSTGRESQL:
        # Convert SQLite double quotes to single quotes for string literals
        # This is a basic conversion - more sophisticated parsing might be needed
        cleaned_sql = cleaned_sql.replace('"', "'")
        # Convert SQLite backticks to double quotes for identifiers
        cleaned_sql = cleaned_sql.replace('`', '"')
    else:
        cleaned_sql = cleaned_sql.replace('"', "'")

    return cleaned_sql

def create_smaller_db(original_db_connection_string: str, max_rows: int = 100000,
                     db_type: DatabaseType = None) -> str:
    """
    Creates a smaller version of the database with limited rows.
    Note: This function currently only works with SQLite databases.

    Args:
        original_db_connection_string (str): Original database connection string
        max_rows (int): Maximum number of rows to copy
        db_type (DatabaseType, optional): Database type

    Returns:
        str: Path to the new smaller database
    """
    if db_type is None:
        db_type = detect_database_type(original_db_connection_string)

    if db_type != DatabaseType.SQLITE:
        raise NotImplementedError("create_smaller_db is currently only implemented for SQLite databases")

    if not os.path.exists(original_db_connection_string):
        raise FileNotFoundError("The specified database does not exist.")

    base, ext = os.path.splitext(original_db_connection_string)
    new_db_path = f"{base}_small{ext}"

    conn_orig = sqlite3.connect(original_db_connection_string)
    conn_new = sqlite3.connect(new_db_path)
    cursor_orig = conn_orig.cursor()
    cursor_orig.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor_orig.fetchall()
    cursor_new = conn_new.cursor()

    for table in tables:
        if table[0] == "sqlite_sequence":
            continue
        table_name = table[0]
        cursor_orig.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        ddl = cursor_orig.fetchone()[0]
        cursor_new.execute(ddl)
        cursor_orig.execute(f"SELECT * FROM `{table_name}` ORDER BY RANDOM() LIMIT {max_rows}")
        rows = cursor_orig.fetchall()
        if rows:
            cursor_new.executemany(f"INSERT INTO `{table_name}` VALUES ({','.join(['?' for _ in range(len(rows[0]))])})", rows)
        conn_new.commit()

    conn_orig.close()
    conn_new.close()
    return new_db_path

def task(queue, db_connection_string, sql, fetch, db_type):
    try:
        result = execute_sql(db_connection_string, sql, fetch, db_type=db_type)
        queue.put(result)
    except Exception as e:
        queue.put(e)

def subprocess_sql_executor(db_connection_string: str, sql: str, timeout: int = 60,
                           db_type: DatabaseType = None):
    """
    Executes SQL in a subprocess with timeout.

    Args:
        db_connection_string (str): Database connection string
        sql (str): SQL query to execute
        timeout (int): Timeout in seconds
        db_type (DatabaseType, optional): Database type

    Returns:
        Query results
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    queue = Queue()
    process = Process(target=task, args=(queue, db_connection_string, sql, "all", db_type))
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()
        print("Time out in subprocess_sql_executor")
        raise TimeoutError("Execution timed out.")
    else:
        try:
            result = queue.get_nowait()
        except Empty:
            raise Exception("No data returned from the process.")

        if isinstance(result, Exception):
            raise result
        return result

def _compare_sqls_outcomes(db_connection_string: str, predicted_sql: str,
                          ground_truth_sql: str, db_type: DatabaseType = None) -> int:
    """
    Compares the outcomes of two SQL queries to check for equivalence.

    Args:
        db_connection_string (str): Database connection string
        predicted_sql (str): The predicted SQL query
        ground_truth_sql (str): The ground truth SQL query
        db_type (DatabaseType, optional): Database type

    Returns:
        int: 1 if the outcomes are equivalent, 0 otherwise
    """
    try:
        predicted_res = execute_sql(db_connection_string, predicted_sql, db_type=db_type)
        ground_truth_res = execute_sql(db_connection_string, ground_truth_sql, db_type=db_type)
        return int(set(predicted_res) == set(ground_truth_res))
    except Exception as e:
        logging.critical(f"Error comparing SQL outcomes: {e}")
        raise e

def compare_sqls(db_connection_string: str, predicted_sql: str, ground_truth_sql: str,
                meta_time_out: int = 30, db_type: DatabaseType = None) -> Dict[str, Union[int, str]]:
    """
    Compares predicted SQL with ground truth SQL within a timeout.

    Args:
        db_connection_string (str): Database connection string
        predicted_sql (str): The predicted SQL query
        ground_truth_sql (str): The ground truth SQL query
        meta_time_out (int): The timeout for the comparison
        db_type (DatabaseType, optional): Database type

    Returns:
        dict: A dictionary with the comparison result and any error message
    """
    if db_type is None:
        db_type = detect_database_type(db_connection_string)

    predicted_sql = _clean_sql(predicted_sql, db_type)
    try:
        res = func_timeout(meta_time_out, _compare_sqls_outcomes,
                          args=(db_connection_string, predicted_sql, ground_truth_sql, db_type))
        error = "incorrect answer" if res == 0 else "--"
    except FunctionTimedOut:
        logging.warning("Comparison timed out.")
        error = "timeout"
        res = 0
    except Exception as e:
        logging.error(f"Error in compare_sqls: {e}")
        error = str(e)
        res = 0
    return {'exec_res': res, 'exec_err': error}

def validate_sql_query(db_connection_string: str, sql: str, max_returned_rows: int = 30,
                      db_type: DatabaseType = None) -> Dict[str, Union[str, Any]]:
    """
    Validates an SQL query by executing it and returning the result.

    Args:
        db_connection_string (str): Database connection string
        sql (str): The SQL query to validate
        max_returned_rows (int): The maximum number of rows to return
        db_type (DatabaseType, optional): Database type

    Returns:
        dict: A dictionary with the SQL query, result, and status
    """
    try:
        result = execute_sql(db_connection_string, sql, fetch=max_returned_rows, db_type=db_type)
        return {"SQL": sql, "RESULT": result, "STATUS": "OK"}
    except Exception as e:
        logging.error(f"Error in validate_sql_query: {e}")
        return {"SQL": sql, "RESULT": str(e), "STATUS": "ERROR"}

def aggregate_sqls(db_connection_string: str, sqls: List[str],
                  db_type: DatabaseType = None) -> str:
    """
    Aggregates multiple SQL queries by validating them and clustering based on result sets.

    Args:
        db_connection_string (str): Database connection string
        sqls (List[str]): A list of SQL queries to aggregate
        db_type (DatabaseType, optional): Database type

    Returns:
        str: The shortest SQL query from the largest cluster of equivalent queries
    """
    results = [validate_sql_query(db_connection_string, sql, db_type=db_type) for sql in sqls]
    clusters = {}

    # Group queries by unique result sets
    for result in results:
        if result['STATUS'] == 'OK':
            # Using a frozenset as the key to handle unhashable types like lists
            try:
                key = frozenset(tuple(row) for row in result['RESULT'])
                if key in clusters:
                    clusters[key].append(result['SQL'])
                else:
                    clusters[key] = [result['SQL']]
            except (TypeError, ValueError):
                # Handle unhashable types by converting to string representation
                key = str(result['RESULT'])
                if key in clusters:
                    clusters[key].append(result['SQL'])
                else:
                    clusters[key] = [result['SQL']]

    if clusters:
        # Find the largest cluster
        largest_cluster = max(clusters.values(), key=len, default=[])
        # Select the shortest SQL query from the largest cluster
        if largest_cluster:
            return min(largest_cluster, key=len)

    logging.warning("No valid SQL clusters found. Returning the first SQL query.")
    return sqls[0]

class ExecutionStatus(Enum):
    SYNTACTICALLY_CORRECT = "SYNTACTICALLY_CORRECT"
    EMPTY_RESULT = "EMPTY_RESULT"
    NONE_RESULT = "NONE_RESULT"
    ZERO_COUNT_RESULT = "ZERO_COUNT_RESULT"
    ALL_NONE_RESULT = "ALL_NONE_RESULT"
    SYNTACTICALLY_INCORRECT = "SYNTACTICALLY_INCORRECT"

def get_execution_status(db_connection_string: str, sql: str, execution_result: List = None,
                        db_type: DatabaseType = None) -> ExecutionStatus:
    """
    Determines the status of an SQL query execution result.

    Args:
        db_connection_string (str): Database connection string
        sql (str): The SQL query
        execution_result (List): The result of executing an SQL query
        db_type (DatabaseType, optional): Database type

    Returns:
        ExecutionStatus: The status of the execution result
    """
    if not execution_result:
        try:
            execution_result = execute_sql(db_connection_string, sql, fetch="all", db_type=db_type)
        except FunctionTimedOut:
            print("Timeout in get_execution_status")
            return ExecutionStatus.SYNTACTICALLY_INCORRECT
        except Exception:
            return ExecutionStatus.SYNTACTICALLY_INCORRECT

    if (execution_result is None) or (execution_result == []):
        return ExecutionStatus.EMPTY_RESULT

    return ExecutionStatus.SYNTACTICALLY_CORRECT

def run_with_timeout(func, *args, timeouts=[3, 5]):
    """
    Runs a function with multiple timeout attempts.

    Args:
        func: Function to execute
        *args: Arguments for the function
        timeouts: List of timeout values to try

    Returns:
        Function result
    """
    def wrapper(stop_event, *args):
        try:
            if not stop_event.is_set():
                result[0] = func(*args)
        except Exception as e:
            result[1] = e

    for attempt, timeout in enumerate(timeouts):
        result = [None, None]
        stop_event = threading.Event()
        thread = threading.Thread(target=wrapper, args=(stop_event, *args))
        thread.start()

        # Wait for the thread to complete or timeout
        thread.join(timeout)

        if thread.is_alive():
            logging.error(f"Function {func.__name__} timed out after {timeout} seconds on attempt {attempt + 1}/{len(timeouts)}")
            stop_event.set()  # Signal the thread to stop
            thread.join()  # Wait for the thread to recognize the stop event
            if attempt == len(timeouts) - 1:
                raise TimeoutException(
                    f"Function {func.__name__} timed out after {timeout} seconds on attempt {attempt + 1}/{len(timeouts)}"
                )
        else:
            if result[1] is not None:
                raise result[1]
            return result[0]

    raise TimeoutException(f"Function {func.__name__} failed to complete after {len(timeouts)} attempts")
