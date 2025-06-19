import random
import logging
from typing import Any, Union, List, Dict
from func_timeout import func_timeout, FunctionTimedOut
from multiprocessing import Process, Queue
import threading
from queue import Empty
from enum import Enum
# from contextlib import contextmanager

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.pool import NullPool
# from sqlglot import parse_one, exp

class TimeoutException(Exception):
    pass

def execute_sql(engine: Engine, sql: str, fetch: Union[str, int] = "all",
                timeout: int = 60) -> Any:
    """
    Execute SQL query on any database using SQLAlchemy Engine

    Args:
        engine: SQLAlchemy Engine object
        sql: SQL query to execute
        fetch: How to fetch results ('all', 'one', 'random', or an integer)
        timeout: Query timeout in seconds

    Returns:
        Query results based on fetch parameter
    """
    class QueryThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = None
            self.exception = None

        def run(self):
            try:
                with engine.connect() as conn:
                    # Set query timeout based on database dialect
                    dialect_name = engine.dialect.name

                    if dialect_name == 'postgresql':
                        conn.execute(text(f"SET statement_timeout = {timeout * 1000}"))
                    elif dialect_name == 'mysql':
                        conn.execute(text(f"SET SESSION max_execution_time = {timeout * 1000}"))
                    elif dialect_name == 'oracle':
                        # Oracle doesn't have a simple statement timeout
                        pass
                    elif dialect_name == 'mssql':
                        conn.execute(text(f"SET LOCK_TIMEOUT {timeout * 1000}"))

                    result = conn.execute(text(sql))

                    if fetch == "all":
                        self.result = result.fetchall()
                    elif fetch == "one":
                        self.result = result.fetchone()
                    elif fetch == "random":
                        samples = result.fetchmany(10)
                        self.result = random.choice(samples) if samples else []
                    elif isinstance(fetch, int):
                        self.result = result.fetchmany(fetch)
                    else:
                        raise ValueError("Invalid fetch argument. Must be 'all', 'one', 'random', or an integer.")
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

def _clean_sql(sql: str) -> str:
    """Clean SQL query by removing unwanted characters and whitespace"""
    return sql.replace('\n', ' ').replace('"', "'").strip("`.")

def get_table_info(engine: Engine) -> List[str]:
    """
    Get list of tables in the database

    Args:
        engine: SQLAlchemy Engine object

    Returns:
        List of table names
    """
    inspector = inspect(engine)
    return inspector.get_table_names()

def get_column_info(engine: Engine, table_name: str) -> List[Dict]:
    """
    Get column information for a table

    Args:
        engine: SQLAlchemy Engine object
        table_name: Name of the table

    Returns:
        List of column information dictionaries
    """
    inspector = inspect(engine)
    return inspector.get_columns(table_name)

def create_smaller_db(source_engine: Engine, target_engine: Engine,
                     max_rows: int = 100000):
    """
    Create a smaller version of the database

    Args:
        source_engine: Source database SQLAlchemy Engine
        target_engine: Target database SQLAlchemy Engine
        max_rows: Maximum rows per table
    """
    # Get all tables from source
    inspector = inspect(source_engine)
    tables = inspector.get_table_names()

    with source_engine.connect() as source_conn, target_engine.connect():
        for table_name in tables:
            # Skip system tables
            if table_name.lower() in ['sqlite_sequence', 'information_schema']:
                continue

            # Get dialect-specific random sampling query
            dialect_name = source_engine.dialect.name

            if dialect_name == 'postgresql':
                query = f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {max_rows}"
            elif dialect_name == 'mysql':
                query = f"SELECT * FROM {table_name} ORDER BY RAND() LIMIT {max_rows}"
            elif dialect_name == 'mssql':
                query = f"SELECT TOP {max_rows} * FROM {table_name} ORDER BY NEWID()"
            elif dialect_name == 'oracle':
                query = f"SELECT * FROM (SELECT * FROM {table_name} ORDER BY DBMS_RANDOM.VALUE) WHERE ROWNUM <= {max_rows}"
            else:  # SQLite and others
                query = f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {max_rows}"

            result = source_conn.execute(text(query))
            rows = result.fetchall()

            if rows:
                # You would need to handle table creation and data insertion here
                # This is simplified - actual implementation would need proper table copying
                pass

def task(queue, engine_url, sql, fetch):
    """Task function for multiprocessing"""
    try:
        # Recreate engine in the new process
        engine = create_engine(engine_url)
        result = execute_sql(engine, sql, fetch)
        queue.put(result)
    except Exception as e:
        queue.put(e)

def subprocess_sql_executor(engine: Engine, sql: str, timeout: int = 60):
    """
    Execute SQL in a subprocess with timeout

    Args:
        engine: SQLAlchemy Engine object
        sql: SQL query to execute
        timeout: Timeout in seconds

    Returns:
        Query results
    """
    # Get the engine URL to recreate it in subprocess
    engine_url = str(engine.url)

    queue = Queue()
    process = Process(target=task, args=(queue, engine_url, sql, "all"))
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

def _compare_sqls_outcomes(engine: Engine, predicted_sql: str,
                          ground_truth_sql: str) -> int:
    """
    Compare the outcomes of two SQL queries

    Args:
        engine: SQLAlchemy Engine object
        predicted_sql: Predicted SQL query
        ground_truth_sql: Ground truth SQL query

    Returns:
        1 if results are equal, 0 otherwise
    """
    try:
        predicted_res = execute_sql(engine, predicted_sql)
        ground_truth_res = execute_sql(engine, ground_truth_sql)
        return int(set(predicted_res) == set(ground_truth_res))
    except Exception as e:
        logging.critical(f"Error comparing SQL outcomes: {e}")
        raise e

def compare_sqls(engine: Engine, predicted_sql: str, ground_truth_sql: str,
                meta_time_out: int = 30) -> Dict[str, Union[int, str]]:
    """
    Compare two SQL queries results

    Args:
        engine: SQLAlchemy Engine object
        predicted_sql: Predicted SQL query
        ground_truth_sql: Ground truth SQL query
        meta_time_out: Timeout for comparison

    Returns:
        Dictionary with comparison results
    """
    predicted_sql = _clean_sql(predicted_sql)
    try:
        res = func_timeout(meta_time_out, _compare_sqls_outcomes,
                          args=(engine, predicted_sql, ground_truth_sql))
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

def validate_sql_query(engine: Engine, sql: str, max_returned_rows: int = 30) -> Dict[str, Union[str, Any]]:
    """
    Validates an SQL query by executing it and returning the result

    Args:
        engine: SQLAlchemy Engine object
        sql: The SQL query to validate
        max_returned_rows: The maximum number of rows to return

    Returns:
        Dictionary with the SQL query, result, and status
    """
    try:
        result = execute_sql(engine, sql, fetch=max_returned_rows)
        return {"SQL": sql, "RESULT": result, "STATUS": "OK"}
    except Exception as e:
        logging.error(f"Error in validate_sql_query: {e}")
        return {"SQL": sql, "RESULT": str(e), "STATUS": "ERROR"}

def aggregate_sqls(engine: Engine, sqls: List[str]) -> str:
    """
    Aggregates multiple SQL queries by validating them and clustering based on result sets

    Args:
        engine: SQLAlchemy Engine object
        sqls: A list of SQL queries to aggregate

    Returns:
        The shortest SQL query from the largest cluster of equivalent queries
    """
    results = [validate_sql_query(engine, sql) for sql in sqls]
    clusters = {}

    # Group queries by unique result sets
    for result in results:
        if result['STATUS'] == 'OK':
            # Using a frozenset as the key to handle unhashable types like lists
            key = frozenset(tuple(row) for row in result['RESULT'])
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

def get_execution_status(engine: Engine, sql: str,
                        execution_result: List = None) -> ExecutionStatus:
    """
    Get execution status of SQL query

    Args:
        engine: SQLAlchemy Engine object
        sql: SQL query
        execution_result: Pre-executed result (optional)

    Returns:
        ExecutionStatus enum value
    """
    if not execution_result:
        try:
            execution_result = execute_sql(engine, sql, fetch="all")
        except FunctionTimedOut:
            print("Timeout in get_execution_status")
            return ExecutionStatus.SYNTACTICALLY_INCORRECT
        except Exception:
            return ExecutionStatus.SYNTACTICALLY_INCORRECT

    if (execution_result is None) or (execution_result == []):
        return ExecutionStatus.EMPTY_RESULT

    return ExecutionStatus.SYNTACTICALLY_CORRECT

def run_with_timeout(func, *args, timeouts=[3, 5]):
    """Run function with multiple timeout attempts"""
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

'''
# Example usage:
if __name__ == "__main__":
    # User creates engine for their database

    # SQLite example
    sqlite_engine = create_engine('sqlite:///test.db')
    result = execute_sql(sqlite_engine, "SELECT * FROM users LIMIT 10")

    # PostgreSQL example
    pg_engine = create_engine('postgresql://user:password@localhost/dbname')
    result = execute_sql(pg_engine, "SELECT * FROM users LIMIT 10")

    # MySQL example
    mysql_engine = create_engine('mysql+pymysql://user:password@localhost/dbname')
    result = execute_sql(mysql_engine, "SELECT * FROM users LIMIT 10")
'''
