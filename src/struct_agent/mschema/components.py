from llama_index.core.llms import LLM
from typing import List, Optional
from .utils import extract_sql_from_llm_response, extract_simple_json_from_llm
from .default_prompts import (
    DEFAULT_IS_DATE_TIME_FIELD_PROMPT,
    DEFAULT_NUMBER_CATEGORY_FIELD_PROMPT,
    DEFAULT_STRING_CATEGORY_FIELD_PROMPT,
    DEFAULT_UNKNOWN_FIELD_PROMPT,
    # DEFAULT_COLUMN_DESC_GEN_CHINESE_PROMPT,
    DEFAULT_COLUMN_DESC_GEN_ENGLISH_PROMPT,
    # DEFAULT_TABLE_DESC_GEN_CHINESE_PROMPT,
    DEFAULT_TABLE_DESC_GEN_ENGLISH_PROMPT,
    DEFAULT_UNDERSTAND_FIELDS_BY_CATEGORY_PROMPT,
    DEFAULT_UNDERSTAND_DATABASE_PROMPT,
    DEFAULT_GET_DOMAIN_KNOWLEDGE_PROMPT,
    DEFAULT_DATE_TIME_MIN_GRAN_PROMPT,
    DEFAULT_SQL_GEN_PROMPT
)
from .call_llamaindex_llm import call_llm
from .type_engine import TypeEngine


def understand_date_time_min_gran(field_info_str: str = '', llm: Optional[LLM] = None):
    """
     Determine the minimum granularity of date and time fields.
     """
    res = call_llm(
        prompt=DEFAULT_DATE_TIME_MIN_GRAN_PROMPT,
        llm=llm,
        field_info_str=field_info_str
    )
    return res.upper().strip()


def understand_database(db_mschema: str = '', llm: Optional[LLM] = None):
    """
    Database understanding.
    """
    db_info1 = call_llm(DEFAULT_UNDERSTAND_DATABASE_PROMPT, llm, db_mschema=db_mschema)
    db_info2 = call_llm(DEFAULT_GET_DOMAIN_KNOWLEDGE_PROMPT, llm, db_info=db_info1)
    return (db_info1 + '\n' + db_info2).strip()


def generate_column_desc(field_name: str, field_info_str: str = '', table_mschema: str = '',
        llm: Optional[LLM] = None, sql: Optional[str] = None, sql_res: Optional[str] = None,
        supp_info: Optional[str] = None, language: Optional[str] = 'EN'):

    # if language == 'CN':
    #     prompt = DEFAULT_COLUMN_DESC_GEN_CHINESE_PROMPT
    if language == 'EN':
        prompt = DEFAULT_COLUMN_DESC_GEN_ENGLISH_PROMPT
    else:
        raise NotImplementedError(f'Unsupported language {language}.')

    column_desc = call_llm(
        prompt,
        llm,
        table_mschema=table_mschema,
        sql=sql,
        sql_res=sql_res,
        field_name=field_name,
        field_info_str=field_info_str,
        supp_info=supp_info
    ).strip()

    # if language == 'CN':
    #     column_desc = extract_simple_json_from_llm(column_desc).get('chinese_name', '')
    #     column_desc = column_desc.replace('"', '').replace('"', '').replace('"', '').replace('**', '')
    #     if column_desc.endswith('。'):
    #         column_desc = column_desc[:-1].strip()
    # if language == 'EN':
    # else:
    #     raise NotImplementedError(f'Unsupported language {language}.')
    column_desc = extract_simple_json_from_llm(column_desc).get('english_desc', '')
    column_desc = column_desc.strip()
    if column_desc.startswith(':') or column_desc.startswith('：'):
        column_desc = column_desc[1:].strip()
    column_desc = column_desc.split('\n')[0]

    return column_desc.strip()

def generate_table_desc(table_name: str, table_mschema: str = '',
        llm: Optional[LLM] = None, sql: Optional[str] = None, sql_res: Optional[str] = None,
        language: Optional[str] = 'EN'):
    # if language == 'CN':
    #     prompt = DEFAULT_TABLE_DESC_GEN_CHINESE_PROMPT
    if language == 'EN':
        prompt = DEFAULT_TABLE_DESC_GEN_ENGLISH_PROMPT
    else:
        raise NotImplementedError(f'Unsupported language {language}.')

    table_desc = call_llm(
        prompt,
        llm,
        table_name=table_name,
        table_mschema=table_mschema,
        sql=sql,
        sql_res=sql_res
    )
    table_desc = extract_simple_json_from_llm(table_desc).get('table_desc', '')
    table_desc = table_desc.strip()

    return table_desc.strip()


def understand_fields_by_category(db_info: str, table_name: str, table_mschema: str = '',
        llm: Optional[LLM] = None, sql: Optional[str] = None, sql_res: Optional[str] = None,
        fields: Optional[List] = [], dim_or_meas: str = ''):
    text = call_llm(
        DEFAULT_UNDERSTAND_FIELDS_BY_CATEGORY_PROMPT,
        llm,
        db_info=db_info,
        table_name=table_name,
        table_mschema=table_mschema,
        sql=sql,
        sql_res=sql_res,
        fields='、'.join([f"{field}" for field in fields]),
        category=dim_or_meas
    )
    return text


def field_category(field_type_cate: str, type_engine: TypeEngine, llm: Optional[LLM] = None,
                   field_info_str: str = ''):
    """
    Distinguish field category and whether dimension or measure.
    is_unique_pk_cons: Whether it is a primary key, foreign key, or unique key (including those that form a composite primary key with other fields)
    """
    code_res = {"category": type_engine.field_category_code_label,
                "dim_or_meas": type_engine.dimension_label}
    enum_res = {"category": type_engine.field_category_enum_label,
                'dim_or_meas': type_engine.dimension_label}
    date_res = {"category": type_engine.field_category_date_label,
                'dim_or_meas': type_engine.dimension_label}
    measure_res = {"category": type_engine.field_category_measure_label,
                   'dim_or_meas': type_engine.measure_label}
    text_res = {"category": type_engine.field_category_text_label,
                'dim_or_meas': type_engine.dimension_label}

    if field_type_cate == type_engine.field_type_date_label:
        return date_res
    elif field_type_cate == type_engine.field_type_bool_label:
        return enum_res
    else:
        kwargs = {"llm": llm, "field_info_str": field_info_str}
        is_date_time = call_llm(
            DEFAULT_IS_DATE_TIME_FIELD_PROMPT, **kwargs
        ).strip()
        if is_date_time == '是':
            return date_res
        else:
            if field_type_cate == type_engine.field_type_string_label:
                # Non-date/time string, determine if it is code, text, or enum
                res = call_llm(
                    DEFAULT_STRING_CATEGORY_FIELD_PROMPT, **kwargs
                ).strip().lower()
                if res == 'enum':
                    return enum_res
                elif res == 'text':
                    return text_res
                else:
                    return code_res
            elif field_type_cate == type_engine.field_type_number_label:
                # Non-date/time number, determine if it is code, measure, or enum
                res = call_llm(DEFAULT_NUMBER_CATEGORY_FIELD_PROMPT, **kwargs).strip().lower()
                if res == 'enum':
                    return enum_res
                elif res == 'measure':
                    return measure_res
                else:
                    return code_res
            else:
                res = call_llm(DEFAULT_UNKNOWN_FIELD_PROMPT, **kwargs).strip().lower()
                if res == 'enum':
                    return enum_res
                elif res == 'measure':
                    return measure_res
                elif res == 'text':
                    return text_res
                else:
                    return code_res


def dummy_sql_generator(dialect: str, db_mschema: str, question: str, evidence: str = '',
                  llm: Optional[LLM] = None) -> None | str:
    """
    SQL Generator
    """
    kwargs = {"dialect": dialect, "db_mschema": db_mschema,
              "question": question, "evidence": evidence}
    llm_response = call_llm(DEFAULT_SQL_GEN_PROMPT, llm, **kwargs)
    sql = extract_sql_from_llm_response(llm_response)
    return sql
