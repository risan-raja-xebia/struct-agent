import pytest
from sqlalchemy import create_engine, text, Table, Column, Integer, String, MetaData
from struct_agent.lsh_search import execution, preprocess, search
from datasketch import MinHash, MinHashLSH
import tempfile
import os
import pickle

@pytest.fixture(scope="module")
def sqlite_engine():
    # Use a file-based SQLite DB to allow sharing between threads
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    engine = create_engine(f'sqlite:///{db_path}')
    metadata = MetaData()
    Table('users', metadata,
          Column('id', Integer, primary_key=True),
          Column('name', String),
          Column('email', String))
    metadata.create_all(engine)
    # Use a transaction that commits so data is visible to all connections
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')"))
        conn.execute(text("INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')"))
    yield engine
    engine.dispose()
    os.close(db_fd)
    os.remove(db_path)

def test_execute_sql_all(sqlite_engine):
    result = execution.execute_sql(sqlite_engine, "SELECT * FROM users", fetch="all")
    assert len(result) == 2

def test_execute_sql_one(sqlite_engine):
    result = execution.execute_sql(sqlite_engine, "SELECT * FROM users", fetch="one")
    assert result is not None

def test_execute_sql_int(sqlite_engine):
    result = execution.execute_sql(sqlite_engine, "SELECT * FROM users", fetch=1)
    assert len(result) == 1

def test_execute_sql_invalid(sqlite_engine):
    with pytest.raises(Exception):
        execution.execute_sql(sqlite_engine, "SELECT * FROM non_existing_table")

def test_get_table_info(sqlite_engine):
    tables = execution.get_table_info(sqlite_engine)
    assert 'users' in tables

def test_get_column_info(sqlite_engine):
    columns = execution.get_column_info(sqlite_engine, 'users')
    col_names = [col['name'] for col in columns]
    assert 'name' in col_names

def test_validate_sql_query_ok(sqlite_engine):
    res = execution.validate_sql_query(sqlite_engine, "SELECT * FROM users")
    assert res['STATUS'] == 'OK'

def test_validate_sql_query_error(sqlite_engine):
    res = execution.validate_sql_query(sqlite_engine, "SELECT * FROM non_existing_table")
    assert res['STATUS'] == 'ERROR'

def test_get_execution_status_correct(sqlite_engine):
    status = execution.get_execution_status(sqlite_engine, "SELECT * FROM users")
    assert status == execution.ExecutionStatus.SYNTACTICALLY_CORRECT

def test_get_execution_status_incorrect(sqlite_engine):
    status = execution.get_execution_status(sqlite_engine, "SELECT * FROM non_existing_table")
    assert status == execution.ExecutionStatus.SYNTACTICALLY_INCORRECT

def test_compare_sqls_equal(sqlite_engine):
    sql = "SELECT * FROM users ORDER BY id"
    res = execution.compare_sqls(sqlite_engine, sql, sql)
    assert res['exec_res'] == 1

def test_compare_sqls_unequal(sqlite_engine):
    sql1 = "SELECT * FROM users WHERE name='Alice'"
    sql2 = "SELECT * FROM users WHERE name='Bob'"
    res = execution.compare_sqls(sqlite_engine, sql1, sql2)
    assert res['exec_res'] == 0

def test__create_minhash():
    m = preprocess._create_minhash(64, "hello world", 3)
    assert isinstance(m, MinHash)

def test_skip_column():
    # Should be False for short id values, True for long values (sum > 50000)
    long_values = ["1" * 20000, "2" * 20000, "3" * 20000]  # sum = 60000
    assert preprocess.skip_column("id", long_values) is True
    assert preprocess.skip_column("name", ["a", "b"]) is False

def test_make_lsh():
    unique_values = {"users": {"name": ["Alice", "Bob"]}}
    lsh, minhashes = preprocess.make_lsh(unique_values, 16, 2, 0.5, verbose=False)
    assert hasattr(lsh, 'query')
    assert isinstance(minhashes, dict)

def test__jaccard_similarity():
    m1 = preprocess._create_minhash(16, "abc", 2)
    m2 = preprocess._create_minhash(16, "abc", 2)
    sim = search._jaccard_similarity(m1, m2)
    assert sim == pytest.approx(1.0, abs=0.01)

def test_query_lsh():
    unique_values = {"users": {"name": ["Alice", "Bob"]}}
    lsh, minhashes = preprocess.make_lsh(unique_values, 16, 2, 0.5, verbose=False)
    result = search.query_lsh(lsh, minhashes, "Alice", signature_size=16, n_gram=2, top_n=1)
    assert 'users' in result
    assert 'name' in result['users']
    assert 'Alice' in result['users']['name']

def test_load_db_lsh(tmp_path):
    # Setup: create fake lsh/minhashes files with correct names and picklable objects
    db_id = tmp_path.name
    pre_dir = tmp_path / "preprocessed"
    pre_dir.mkdir()
    lsh = MinHashLSH(threshold=0.5, num_perm=16)
    minhashes = {"k": (MinHash(num_perm=16), "users", "name", "Alice")}
    with open(pre_dir / f"{db_id}_lsh.pkl", "wb") as f:
        pickle.dump(lsh, f)
    with open(pre_dir / f"{db_id}_minhashes.pkl", "wb") as f:
        pickle.dump(minhashes, f)
    lsh_loaded, minhashes_loaded = search.load_db_lsh(str(tmp_path))
    assert minhashes_loaded["k"][3] == "Alice"

def test_load_db_lsh_missing(tmp_path):
    with pytest.raises(Exception):
        search.load_db_lsh(str(tmp_path))
