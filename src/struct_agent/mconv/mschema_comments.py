# from dotenv import load_dotenv, find_dotenv
# import os
# from sqlalchemy import create_engine, text
# from sqlalchemy.engine import Engine

# class DatabaseConnector:
#     def __init__(self):
#         """
#         Initializes the DatabaseConnector by loading environment variables
#         and attempting to connect to the database.
#         """
#         load_dotenv(find_dotenv())

#         try:
#             self.engine = create_engine(
#                 f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
#                 f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
#             )
#         except KeyError as e:
#             print(f"Missing environment variable: {e}")
#             self.engine = None
#             print("Engine not created. Skipping connection test.")
#             return

#         try:
#             with self.engine.connect() as connection:
#                 connection.execute(text("SELECT 1"))
#                 print("Database connection successful!")
#         except Exception as e:
#             print(f"Failed to connect to the database: {str(e)}")

#     def get_engine(self) -> Engine | None:
#         return self.engine



# import os
# from sqlalchemy import create_engine, text
# from sqlalchemy.engine import Engine
# from llama_index.llms.openai import OpenAI
import logging
from typing import Optional
# TODO: Add Logging to the File

from ..mschema.schema_engine import SchemaEngine
logger = logging.getLogger(__name__)

class MSchemaGenerator:
    """
    A class that handles database connection and schema generation
    using SchemaEngine with LLM-powered analysis.
    """

    def __init__(self, llm,db_engine,comment_mode: str = 'generation', language: str = "EN",):
        """
        Initializes the MSchemaGenerator.

        Args:
            env_file (str): Path to environment file. Defaults to '.env'.
            comment_mode (str): Mode for comment generation. Defaults to 'generation'.
            language (str): Language for schema descriptions. Defaults to "EN".

        """
        self.comment_mode = comment_mode
        self.language = language
        self.db_engine = None
        self.llm = None
        self.schema_engine_instance = None
        self.mschema = None
        self.db_name = None

        logger.info("Initializing MSchemaGenerator")
        logger.debug(f"Parameters: comment_mode={comment_mode}, language={language}")

        # Load environment variables
        # load_dotenv(self.env_file)

        # Initialize components
        # self._setup_database_connection()
        # self._setup_llm()



    def generate_schema(self) -> Optional[str]:
        """
        Generates the database schema with descriptions using SchemaEngine.

        Returns:
            Optional[str]: The generated schema string, or None if generation fails.
        """

        if not self.db_engine:
            raise ValueError("Database engine not available. Cannot generate schema.")

        if not self.llm:
            raise ValueError("LLM not available. Cannot generate schema.")

        if not self.db_name:
            raise ValueError("Database name not available. Cannot generate schema.")

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

            # Convert to string format
            mschema_str = self.mschema.to_mschema()
            # print(mschema_str)
            logger.info("Schema generation completed successfully")
            return mschema_str

        except Exception as e:
            print(f"Failed to generate schema: {str(e)}")
            return None

    def save_schema(self, filename: str):
        """
        Saves the generated schema to a JSON file.

        Args:
            filename (str): Custom filename. If None, uses database name.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        if not self.mschema:
            raise ValueError("No schema available to save. Run generate_schema() first.")
        if not filename:
            raise ValueError("Filename cannot be None or empty.")
        self.mschema.save(filename)


    def get_engine(self):
        """
        Returns the database engine instance.

        Returns:
            Optional[Engine]: The SQLAlchemy engine or None if not connected.
        """
        return self.db_engine

    def get_schema_string(self) -> Optional[str]:
        """
        Returns the schema as a string without regenerating it.

        Returns:
            Optional[str]: The schema string or None if not generated.
        """
        if self.mschema:
            return self.mschema.to_mschema()
        return None

    # def is_connected(self) -> bool:
    #     """
    #     Checks if the database connection is available.

    #     Returns:
    #         bool: True if connected, False otherwise.
    #     """
    #     return self.db_engine is not None

    def run_complete_process(self) -> bool:
        """
        Runs the complete schema generation and saving process.

        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.is_connected():
            raise ValueError("Database connection is not established. Please connect to the database first.")


        # Generate schema
        schema_string = self.generate_schema()
        if not schema_string:
            raise ValueError("Schema generation failed. Please check the database connection and LLM configuration.")

        # Save schema
        return self.save_schema()
