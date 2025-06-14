import os
from pathlib import Path
from dotenv import load_dotenv
from struct_agent.mconv.mschema_comments import MSchemaGenerator
from struct_agent.mconv.mschema_to_mdl import MSchemaToMDLConverter


def get_database_info(env_file: str = '.env'):
    """Get database information from .env file"""
    load_dotenv(env_file)
    
    postgres_db = os.getenv('POSTGRES_DB')
    if not postgres_db:
        raise ValueError(f"POSTGRES_DB not found in {env_file}")
    
    return {
        'database': postgres_db,
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'schema': os.getenv('POSTGRES_SCHEMA', 'public')
    }


def main():
    """Main function that runs schema generation and MDL conversion"""
    try:
        # Get database configuration
        db_info = get_database_info('.env')
        postgres_db = db_info['database']
        postgres_schema = db_info['schema']
        
        print(f"🔧 Using database: {postgres_db}, schema: {postgres_schema}")
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False
    # Step 1: Generate schema with comments
    print("📊 Step 1: Generating database schema with comments...")
    generator = MSchemaGenerator(
        env_file='.env',
        comment_mode='generation', 
        language="EN"
    )
    
    success = generator.run_complete_process()
    
    if not success:
        print("❌ Schema generation failed.")
        return False
    
    print("✅ Schema generation and saving completed successfully!")
    
    # Step 2: Convert mschema to Wren.ai MDL format
    print("\n🔄 Step 2: Converting mschema to Wren.ai MDL format...")
    
    try:
        # Create converter using .env configuration
        converter = MSchemaToMDLConverter.from_env('.env', schema=postgres_schema)
        
        # Dynamic filenames based on POSTGRES_DB from .env
        input_file = f"{postgres_db}_mschema.json"
        output_file = f"{postgres_db}_wren_mdl.json"
        
        # Check if input file exists
        if not Path(input_file).exists():
            print(f"❌ Input file not found: {input_file}")
            print("   Available files in current directory:")
            for file in Path('.').glob('*_mschema.json'):
                print(f"   - {file}")
            return False
        
        # Convert and save
        print(f"   📄 Input: {input_file}")
        print(f"   📄 Output: {output_file}")
        
        mdl_data = converter.convert_and_save(
            input_file=input_file,
            output_file=output_file,
            pretty=True
        )
        
        # Show conversion statistics
        stats = converter.get_conversion_stats(mdl_data)
        print(f"✅ Successfully converted to Wren.ai MDL: {output_file}")
        print(f"   📊 Conversion Statistics:")
        print(f"      - Database: {postgres_db}")
        print(f"      - Schema: {postgres_schema}")
        print(f"      - Models: {stats['models']}")
        print(f"      - Relationships: {stats['relationships']}")
        
        return True
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        print(f"   Expected file: {input_file}")
        print("   Make sure MSchemaGenerator output file exists")
        return False
    except ValueError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False
    except IOError as e:
        print(f"❌ File I/O error: {e}")
        return False
    except Exception as e:
        print(f"❌ Conversion error: {e}")
        return False


def convert_existing_mschema(input_file: str = None, output_file: str = None, 
                           catalog: str = None, schema: str = None, env_file: str = '.env'):
    """
    Utility function to convert an existing mschema file to MDL format
    without running the schema generation process.
    If parameters are None, they will be derived from .env file.
    """
    try:
        # Get database info from .env if needed
        if not input_file or not catalog or not schema:
            db_info = get_database_info(env_file)
            postgres_db = db_info['database']
            postgres_schema = db_info['schema']
            
            # Set defaults based on .env
            if not input_file:
                input_file = f"{postgres_db}_mschema.json"
            if not output_file:
                output_file = f"{postgres_db}_wren_mdl.json"
            if not catalog:
                catalog = postgres_db
            if not schema:
                schema = postgres_schema
        
        print(f"🔄 Converting existing mschema file: {input_file}")
        print(f"   📄 Output: {output_file}")
        print(f"   🏛️  Catalog: {catalog}, Schema: {schema}")
        
        # Check if input file exists
        if not Path(input_file).exists():
            print(f"❌ Input file not found: {input_file}")
            print("   Available mschema files:")
            for file in Path('.').glob('*_mschema.json'):
                print(f"   - {file}")
            return False
        
        converter = MSchemaToMDLConverter(
            catalog=catalog,
            schema=schema
        )
        
        mdl_data = converter.convert_and_save(
            input_file=input_file,
            output_file=output_file,
            pretty=True
        )
        
        stats = converter.get_conversion_stats(mdl_data)
        print(f"✅ Successfully converted to Wren.ai MDL: {output_file}")
        print(f"   📊 Statistics:")
        print(f"      - Models: {stats['models']}")
        print(f"      - Relationships: {stats['relationships']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting Database Schema to Wren.ai MDL Conversion Process")
    print("=" * 60)
    
    # Run the complete process: schema generation + MDL conversion
    success = main()
    
    print("=" * 60)
    if success:
        print("🎉 Complete process finished successfully!")
        print("\nFiles generated:")
        try:
            db_info = get_database_info('.env')
            postgres_db = db_info['database']
            print(f"   📄 Schema file: {postgres_db}_mschema.json")
            print(f"   📄 MDL file: {postgres_db}_wren_mdl.json")
        except:
            print("   📄 Check current directory for generated files")
    else:
        print("💥 Process failed. Check the error messages above.")
        print("\nTroubleshooting:")
        print("   1. Check your .env file contains POSTGRES_DB")
        print("   2. Ensure database connection is working")
        print("   3. Verify mschema file was generated")
        
    print("\n💡 To convert existing mschema files only:")
    print("   convert_existing_mschema('your_file_mschema.json')")
    print("   or call convert_existing_mschema() with no params to use .env defaults")