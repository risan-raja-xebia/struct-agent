from vanna import Vanna

# import pandas as pd

# Initialize Vanna
vn = Vanna(
    config={
        'api_key': 'your-openai-api-key',
        'model': 'gpt-4',
        'dialect': 'PostgreSQL',
    }
)

# Connect to PostgreSQL
vn.connect_to_postgres(
    host='localhost',
    dbname='sales_db',
    user='postgres',
    password='password',
    port=5432
)

# Train with a question-SQL pair
vn.train(
    question="What are the top 5 products by revenue?",
    sql="SELECT product_name, SUM(revenue) FROM sales GROUP BY product_name ORDER BY SUM(revenue) DESC LIMIT 5"
)
print("Added question-SQL pair.")

# Train with a DDL statement
vn.train(
    ddl="CREATE TABLE sales (product_name VARCHAR(100), revenue DECIMAL(10,2), sale_date DATE)"
)
print("Added DDL statement.")

# Train with documentation
vn.train(
    documentation="The sales table contains product sales data, with revenue in USD and sale_date in YYYY-MM-DD format."
)
print("Added documentation.")

# Generate and apply a generic training plan
df_columns = vn.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS")
plan = vn.get_training_plan_generic(df_columns)
vn.train(plan=plan)
print("Applied generic training plan.")

# Inspect training data
training_data = vn.get_training_data()
print("Training Data:")
print(training_data)

# Remove a training data item (example)
if not training_data.empty:
    training_id = training_data.iloc[0]['id']
    success = vn.remove_training_data(id=training_id)
    print(f"Removed training data with ID {training_id}: {success}")
