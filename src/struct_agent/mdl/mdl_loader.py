import json
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.exc import IntegrityError

# Import from the models file
from .schema import (
    Project, Model, ModelColumn,
    Relation, TableReference
)

def load_mdl_file(file_path: str) -> Dict[str, Any]:
    """Load and parse the MDL JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"MDL file '{file_path}' not found")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in MDL file: {e}")

def update_mdl_to_db(mdl_file: str, project_display_name: str = "MDL Project", engine=None):
    """Update the database with the MDL data."""
    if engine is None:
        raise ValueError("An SQLAlchemy engine must be provided.")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Load MDL data
        mdl_data = load_mdl_file(mdl_file)

        # Extract catalog and schema
        catalog = mdl_data.get("catalog", "mdl")
        schema = mdl_data.get("schema", "public")

        # Step 1: Create or get Project
        project = session.query(Project).filter_by(catalog=catalog, schema=schema).first()
        if not project:
            project = Project(
                type="ecommerce",
                display_name=project_display_name,
                catalog=catalog,
                schema=schema,
                language="en",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(project)
            session.flush()  # Ensure project ID is available

        # Step 2: Create Models and TableReferences
        model_map = {}  # Map model names to Model objects
        for mdl_model in mdl_data.get("models", []):
            model_name = mdl_model["name"]
            table_name = mdl_model["tableReference"]["table"]
            properties = mdl_model.get("properties", {})

            # Create TableReference
            table_ref = TableReference(
                schema=schema,
                table=table_name
            )
            session.add(table_ref)
            session.flush()

            # Create Model
            model = Model(
                project_id=project.id,
                display_name=model_name,
                source_table_name=table_name,
                reference_name=model_name.lower(),
                table_reference_id=table_ref.id,
                cached=0,  # Changed from False to 0 (integer)
                properties=json.dumps(properties) if properties else None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(model)
            session.flush()
            model_map[model_name] = model

            # Step 3: Create ModelColumns
            for column in mdl_model.get("columns", []):
                column_name = column["name"]
                is_relationship = "relationship" in column
                is_pk = column_name == mdl_model.get("primaryKey")

                model_column = ModelColumn(
                    model_id=model.id,
                    is_calculated=False,
                    display_name=column_name,
                    source_column_name=column.get("expression", column_name),
                    reference_name=column_name.lower(),
                    type=column["type"],
                    not_null=column.get("notNull", False),
                    is_pk=is_pk,
                    properties=json.dumps(column.get("properties", {})) if column.get("properties") else None,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(model_column)
                if is_relationship:
                    # Store relationship columns for later processing
                    model_column.relationship_name = column.get("relationship")
                session.flush()

        # Step 4: Create Relations
        for relationship in mdl_data.get("relationships", []):
            rel_name = relationship["name"]
            from_model_name, to_model_name = relationship["models"]
            condition = relationship["condition"]  # e.g., "Payments.orderId = Orders.orderId"
            join_type = relationship["joinType"]

            # Parse condition to extract column names
            from_part, to_part = condition.split(" = ")
            from_model, from_column = from_part.split(".")
            to_model, to_column = to_part.split(".")

            # Find from and to ModelColumns
            from_model_obj = model_map.get(from_model)
            to_model_obj = model_map.get(to_model)
            if not from_model_obj or not to_model_obj:
                print(f"Warning: Model {from_model} or {to_model} not found for relationship {rel_name}")
                continue

            from_column_obj = session.query(ModelColumn).filter_by(
                model_id=from_model_obj.id,
                reference_name=from_column.lower()
            ).first()
            to_column_obj = session.query(ModelColumn).filter_by(
                model_id=to_model_obj.id,
                reference_name=to_column.lower()
            ).first()

            if not from_column_obj or not to_column_obj:
                print(f"Warning: Column {from_column} or {to_column} not found for relationship {rel_name}")
                continue

            # Create Relation
            relation = Relation(
                project_id=project.id,
                name=rel_name,
                join_type=join_type,
                from_column_id=from_column_obj.id,
                to_column_id=to_column_obj.id,
                properties=None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(relation)

        # Commit the transaction
        session.commit()
        print("MDL data successfully updated to the database.")

    except IntegrityError as e:
        session.rollback()
        print(f"Database integrity error: {e}")
    except Exception as e:
        session.rollback()
        print(f"Error updating MDL to database: {e}")
    finally:
        session.close()

#Usage example:
#     mdl_file_path = "mdl.json"
#     update_mdl_to_db(mdl_file_path, project_display_name="MDL Ecommerce Project")
