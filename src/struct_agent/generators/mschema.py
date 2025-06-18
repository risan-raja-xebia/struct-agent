import logging
from typing import Optional
from ..mschema.schema_engine import SchemaEngine
logger = logging.getLogger(__name__)

class MSchemaGenerator:
    """
    A class that handles database connection and schema generation
    using SchemaEngine with LLM-powered analysis.
    """

    def __init__(self, llm, db_engine, comment_mode: str = 'generation', language: str = "EN"):
        """
        Initializes the MSchemaGenerator.

        Args:
            llm: Language model instance for schema analysis
            db_engine: Database engine instance
            comment_mode (str): Mode for comment generation. Defaults to 'generation'.
            language (str): Language for schema descriptions. Defaults to "EN".
        """
        self.comment_mode = comment_mode
        self.language = language
        self.db_engine = db_engine
        self.llm = llm
        self.schema_engine_instance = None
        self.mschema = None
        self.db_name = None
        self.mschema_str = None

        logger.info("Initializing MSchemaGenerator")
        logger.debug(f"Parameters: comment_mode={comment_mode}, language={language}")

    def generate_schema(self, db_name: str = None, filename: Optional[str] = None):
        """
        Generates the database schema with descriptions using SchemaEngine.

        Args:
            db_name (str): Name of the database. If not provided, uses self.db_name.
            filename (str, optional): Filename to save the schema. If not provided,
                                    uses the database name with .json extension.
        """

        if db_name:
            self.db_name = db_name

        if not self.db_engine:
            raise ConnectionError("Database engine is not initialized")

        if not self.llm:
            raise RuntimeError("Language model not loaded. Ensure the LLM is properly configured and initialized.")

        if not self.db_name:
            raise ValueError("Database name is not specified")

        try:
            # Create SchemaEngine instance
            self.schema_engine_instance = SchemaEngine(
                self.db_engine,
                llm=self.llm,
                db_name=self.db_name,
                comment_mode=self.comment_mode
            )
            logger.debug("SchemaEngine instance created successfully")

            # Generate field categories and descriptions
            self.schema_engine_instance.fields_category()
            self.schema_engine_instance.table_and_column_desc_generation(language=self.language)

            # Get the generated schema
            self.mschema = self.schema_engine_instance.mschema

            # Determine the filename to save
            if filename:
                save_filename = filename
                # Add .json extension if not present
                if not save_filename.endswith('.json'):
                    save_filename += '.json'
            else:
                save_filename = f'./{self.db_name}.json'

            self.mschema.save(save_filename)
            logger.info(f"Schema saved to: {save_filename}")

            # Convert to string format
            self.mschema_str = self.mschema.to_mschema()

            logger.info("Schema generation completed successfully")

        except Exception as e:
            logger.error(f"Failed to generate schema: {str(e)}")
            print(f"Failed to generate schema: {str(e)}")
            return None


'''Usage Examples:

# Example 1: Using default filename (database name)
schema_generator.generate_schema()  # Saves as './my_database.json'

# Example 2: Custom filename with extension
schema_generator.generate_schema(filename='custom_schema.json')

# Example 3: Custom filename without extension (will add .json automatically)
schema_generator.generate_schema(filename='my_custom_schema')

# Example 4: Full path with custom filename
schema_generator.generate_schema(filename='./schemas/production_schema.json')

# Example 5: With both db_name and filename
schema_generator.generate_schema(db_name='new_db', filename='new_db_schema.json')

# Complete usage example:
from dotenv import load_dotenv,find_dotenv
import os
from sqlalchemy import create_engine,text
from llama_index.llms.openai import OpenAI
from struct_agent.mconv.mschema_comments import MSchemaGenerator

load_dotenv(find_dotenv())

# Create database engine
db_engine = create_engine(f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}")

llm = OpenAI(
    model="gpt-4o-mini",
    api_key=os.environ['OPENAI_API_KEY'],
)

# Create and use MSchemaGenerator
schema_generator = MSchemaGenerator(
    llm=llm,
    db_engine=db_engine,
    comment_mode='generation',
    language='EN'
)

schema_generator.db_name = os.environ['POSTGRES_DB']

# Generate schema with custom filename
result = schema_generator.generate_schema(filename='production_schema.json')
'''
