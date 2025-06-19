from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from datetime import UTC as UTC_TZ
from sqlalchemy import Integer, String, ForeignKey, DateTime, Boolean, JSON, text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, Any
from datetime import datetime

load_dotenv('.env')

Base = declarative_base()

def get_engine():
    return create_engine(f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}")

def check_connection():
    engine = get_engine()
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(result.fetchone())
            print("Connection successful!")
    except Exception as e:
        print(f"Connection failed: {e}")

class Model(Base):
    __tablename__ = "model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ref_sql: Mapped[str] = mapped_column(String(255), nullable=True)
    table_reference_id: Mapped[int] = mapped_column(Integer, ForeignKey("table_reference.id"), nullable=True, unique=True)
    cached: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refresh_time: Mapped[int] = mapped_column(String(255), nullable=True)
    properties: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

    project: Mapped["Project"] = relationship("Project", back_populates="models")
    columns: Mapped[list["ModelColumn"]] = relationship(
        "ModelColumn", back_populates="model"
    )
    table_reference: Mapped["TableReference"] = relationship("TableReference", back_populates="model")

class ModelColumn(Base):
    __tablename__ = "model_column"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(Integer, ForeignKey("model.id"))
    is_calculated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aggregation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lineage: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    not_null: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    properties: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

    model: Mapped["Model"] = relationship("Model", back_populates="columns")

class Project(Base):
    __tablename__ = "project"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    catalog: Mapped[str] = mapped_column(String(255), nullable=False)
    schema: Mapped[str] = mapped_column(String(255), nullable=False)
    sample_dataset: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))
    connection_info: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    language: Mapped[str] = mapped_column(String(255), nullable=False, default="en")
    questions: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    query_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    questions_status: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    questions_error: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    version: Mapped[str] = mapped_column(String(255), nullable=True)

    models: Mapped[list[Model]] = relationship("Model", back_populates="project")

class Relation(Base):
    __tablename__ = "relation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    join_type: Mapped[str] = mapped_column(String(255), nullable=False)
    from_column_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_column.id"), nullable=False)
    to_column_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_column.id"), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    properties: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

class SchemaChange(Base):
    __tablename__ = "schema_change"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    change: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    resolve: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class SqlPair(Base):
    __tablename__ = "sql_pair"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sql: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class SqliteSeq(Base):
    __tablename__ = "sqlite_sequence"
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

class Thread(Base):
    __tablename__ = "thread"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))
    questions: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    query_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    questions_status: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

class AskingTask(Base):
    __tablename__ = "asking_task"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("thread.id"), nullable=True)
    thread_response_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("thread_response.id"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class ThreadResponse(Base):
    __tablename__ = "thread_response"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("thread.id"))
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    breakdown: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))
    sql: Mapped[str] = mapped_column(String(255), nullable=False)
    answer_detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    view_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chart_detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    asking_task_id: Mapped[int] = mapped_column(Integer, ForeignKey("asking_task.id"), nullable=True)

class View(Base):
    __tablename__ = "view"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    statement: Mapped[str] = mapped_column(String(255), nullable=False)
    cached: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    refresh_time: Mapped[int] = mapped_column(String(255), nullable=True)
    properties: Mapped[Optional[Any]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class ModelNestedColumn(Base):
    __tablename__ = "model_nested_column"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(Integer, ForeignKey("model.id"))
    column_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_column.id"))
    column_path: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    properties: Mapped[Optional[Any]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class MetricMeasure(Base):
    __tablename__ = "metric_measure"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_id: Mapped[int] = mapped_column(Integer, ForeignKey("metric.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    expression: Mapped[str] = mapped_column(String(255), nullable=False)
    granularity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class Metric(Base):
    __tablename__ = "metric"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    cached: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    refresh_time: Mapped[int] = mapped_column(String(255), nullable=True)
    model_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("model.id"), nullable=True)
    metric_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("metric.id"), nullable=True)
    properties: Mapped[Optional[Any]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class Learning(Base):
    __tablename__ = "learning"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=True)
    paths: Mapped[str] = mapped_column(String(255), nullable=False)

class KnexMigrationsLock(Base):
    __tablename__ = "knex_migrations_lock"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_locked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class KnexMigrations(Base):
    __tablename__ = "knex_migrations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    batch: Mapped[int] = mapped_column(Integer, nullable=False)
    migration_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))

class Instruction(Base):
    __tablename__ = "instruction"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    instruction: Mapped[str] = mapped_column(String(255), nullable=False)
    questions: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class DeployLog(Base):
    __tablename__ = "deploy_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    manifest: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    error: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class Dashboard(Base):
    __tablename__ = "dashboard"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))
    cache_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schedule_frequency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    schedule_timezone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    next_scheduled_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)

class DashboardItem(Base):
    __tablename__ = "dashboard_item"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dashboard_id: Mapped[int] = mapped_column(Integer, ForeignKey("dashboard.id"))
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    layout: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

class DashboardItemRefreshJob(Base):
    __tablename__ = "dashboard_item_refresh_job"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hash: Mapped[str] = mapped_column(String(255), nullable=False)
    dashboard_id: Mapped[int] = mapped_column(Integer, ForeignKey("dashboard.id"))
    dashboard_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("dashboard.id"))
    started_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    finished_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class ApiHistroy(Base):
    __tablename__ = "api_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id"))
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("thread.id"))
    api_type: Mapped[str] = mapped_column(String(255), nullable=False)
    header: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    request_payload: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    response_payload: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC_TZ), onupdate=datetime.now(UTC_TZ))

class TableReference(Base):
    __tablename__ = "table_reference"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schema: Mapped[str] = mapped_column(String(255), nullable=False)
    table: Mapped[str] = mapped_column(String(255), nullable=False)
    model = relationship("Model", back_populates="table_reference")

# Usage Example:
#     check_connection()
#     Base.metadata.create_all(get_engine(), checkfirst=True)
