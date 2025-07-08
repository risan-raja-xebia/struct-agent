# from abc import ABC, abstractmethod
# from typing import Union
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class DimensionType(Enum):
    STRING = "string"
    NUMBER = "number"
    TIME = "time"
    BOOLEAN = "boolean"

class MeasureType(Enum):
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    COUNT_DISTINCT_APPROX = "count_distinct_approx"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    NUMBER = "number"
    BOOLEAN = "boolean"
    STRING = "string"

class JoinType(Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"

class TimeGranularity(Enum):
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"
    HOUR = "hour"
    MINUTE = "minute"
    SECOND = "second"

@dataclass
class Dimension:
    name: str
    sql: str
    type: DimensionType
    primary_key: bool = False
    description: Optional[str] = None
    format: Optional[str] = None
    granularities: List[TimeGranularity] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'name': self.name,
            'sql': self.sql,
            'type': self.type.value,
            'primary_key': self.primary_key
        }
        if self.description:
            result['description'] = self.description
        if self.format:
            result['format'] = self.format
        if self.granularities:
            result['granularities'] = [g.value for g in self.granularities]
        return result

@dataclass
class Measure:
    name: str
    type: MeasureType
    sql: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None
    rolling_window: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'name': self.name,
            'type': self.type.value
        }
        if self.sql:
            result['sql'] = self.sql
        if self.description:
            result['description'] = self.description
        if self.format:
            result['format'] = self.format
        if self.rolling_window:
            result['rolling_window'] = self.rolling_window # type: ignore
        return result

@dataclass
class Segment:
    name: str
    sql: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'name': self.name,
            'sql': self.sql
        }
        if self.description:
            result['description'] = self.description
        return result

@dataclass
class Join:
    name: str
    sql: str
    relationship: JoinType
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'name': self.name,
            'sql': self.sql,
            'relationship': self.relationship.value
        }
        if self.description:
            result['description'] = self.description
        return result

@dataclass
class PreAggregation:
    name: str
    measures: List[str]
    dimensions: List[str]
    time_dimension: Optional[str] = None
    granularity: Optional[TimeGranularity] = None
    refresh_key: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'name': self.name,
            'measures': self.measures,
            'dimensions': self.dimensions
        }
        if self.time_dimension:
            result['time_dimension'] = self.time_dimension
        if self.granularity:
            result['granularity'] = self.granularity.value
        if self.refresh_key:
            result['refresh_key'] = self.refresh_key
        return result

@dataclass
class Cube:
    name: str
    sql_table: Optional[str] = None
    sql: Optional[str] = None
    description: Optional[str] = None
    dimensions: List[Dimension] = field(default_factory=list)
    measures: List[Measure] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)
    joins: List[Join] = field(default_factory=list)
    pre_aggregations: List[PreAggregation] = field(default_factory=list)
    extends: Optional[str] = None  # For cube inheritance

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'name': self.name
        }
        if self.sql_table:
            result['sql_table'] = self.sql_table
        if self.sql:
            result['sql'] = self.sql
        if self.description:
            result['description'] = self.description
        if self.extends:
            result['extends'] = self.extends
        if self.dimensions:
            result['dimensions'] = [d.to_dict() for d in self.dimensions]  # type: ignore
        if self.measures:
            result['measures'] = [m.to_dict() for m in self.measures]  # type: ignore
        if self.segments:
            result['segments'] = [s.to_dict() for s in self.segments]  # type: ignore
        if self.joins:
            result['joins'] = [j.to_dict() for j in self.joins]  # type: ignore
        if self.pre_aggregations:
            result['pre_aggregations'] = [p.to_dict() for p in self.pre_aggregations]  # type: ignore
        return result

@dataclass
class ViewCube:
    join_path: str
    includes: List[str] = field(default_factory=list)
    excludes: List[str] = field(default_factory=list)
    prefix: bool = False
    alias: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'join_path': self.join_path
        }
        if self.includes:
            result['includes'] = self.includes  # type: ignore
        if self.excludes:
            result['excludes'] = self.excludes  # type: ignore
        if self.prefix:
            result['prefix'] = self.prefix  # type: ignore
        if self.alias:
            result['alias'] = self.alias
        return result

@dataclass
class View:
    name: str
    cubes: List[ViewCube] = field(default_factory=list)
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'name': self.name,
            'cubes': [c.to_dict() for c in self.cubes]
        }
        if self.description:
            result['description'] = self.description
        return result
