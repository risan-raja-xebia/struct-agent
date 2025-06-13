#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
echo "Script Directory: $SCRIPT_DIR"

# Help message
# Usage: ./load_db.sh [commented]
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: $0 [commented]"
    echo "If 'commented' is provided, it will load the schema and data from ecommerce_commented.sql."
    echo "Otherwise, it will load from ecommerce.sql."
    exit 0
fi

# Configurations
DB_NAME="ecommerce_db"
DB_USER="admin"
DB_PASSWORD="admin123"
DB_HOST="localhost"
DB_PORT="5432"

# Create the Database if it doesn't exist or Drop and Recreate it
PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q 1 &&
    PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "DROP DATABASE $DB_NAME;"
if [ $? -ne 0 ]; then
    echo "Failed to drop database $DB_NAME or it does not exist"
fi
PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q 1 ||
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"
if [ $? -ne 0 ]; then
    echo "Failed to create database $DB_NAME"
    exit 1
fi

# Load the Schema and Data into PostgreSQL
# Check for argument commented or not
if [ "$1" = "commented" ]; then
    PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -f "$SCRIPT_DIR/ecommerce_commented.sql";
else
    PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -f "$SCRIPT_DIR/ecommerce.sql";
fi

# Load the csv data files
CSV_DIR="$SCRIPT_DIR/csv_data"


CSV_FILES=(
    "olist_geolocation_dataset_deduped.csv"
    "olist_customers_dataset.csv"
    "olist_sellers_dataset.csv"
    "olist_orders_dataset.csv"
    "product_category_name_translation.csv"
    "olist_products_dataset.csv"
    "olist_order_items_dataset.csv"
    "olist_order_payments_dataset.csv"
    "olist_order_reviews_dataset.csv"
    "olist_marketing_qualified_leads_dataset.csv"
    "olist_closed_deals_dataset.csv"
)

TABLE_NAMES=(
    "ecommerce.geolocation"
    "ecommerce.customers"
    "ecommerce.sellers"
    "ecommerce.orders"
    "ecommerce.product_category_name_translations"
    "ecommerce.products"
    "ecommerce.order_items"
    "ecommerce.order_payments"
    "ecommerce.order_reviews"
    "marketing.marketing_qualified_leads"
    "marketing.closed_deals"
)

# Loop through the CSV files and load them into the database
for i in "${!CSV_FILES[@]}"; do
    CSV_FILE="$CSV_DIR/${CSV_FILES[$i]}"
    TABLE_NAME="${TABLE_NAMES[$i]}"
    
    if [ -f "$CSV_FILE" ]; then
        # echo "Loading $CSV_FILE into $TABLE_NAME"
        PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -c "\COPY $TABLE_NAME FROM '$CSV_FILE' WITH (FORMAT csv, HEADER true)"
        if [ $? -ne 0 ]; then
            echo "Failed to load $CSV_FILE into $TABLE_NAME"
            # echo PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -c "\COPY $TABLE_NAME FROM '$CSV_FILE' WITH (FORMAT csv, HEADER true)"
            # exit 1
        fi
    else
        echo "File $CSV_FILE does not exist."
    fi
done

