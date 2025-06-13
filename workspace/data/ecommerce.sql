DROP SCHEMA IF EXISTS ecommerce CASCADE;

CREATE SCHEMA ecommerce;

-- DROP TABLE IF EXISTS ecommerce.geolocation CASCADE;

CREATE TABLE
    ecommerce.geolocation (
        geolocation_zip_code_prefix TEXT PRIMARY KEY,
        geolocation_lat DOUBLE PRECISION,
        geolocation_lng DOUBLE PRECISION,
        geolocation_city TEXT,
        geolocation_state TEXT
    );

-- DROP TABLE IF EXISTS ecommerce.customers CASCADE;

CREATE TABLE
    ecommerce.customers (
        customer_id TEXT PRIMARY KEY,
        customer_unique_id TEXT,
        customer_zip_code_prefix TEXT,
        customer_city TEXT,
        customer_state TEXT
    );

-- DROP TABLE IF EXISTS ecommerce.sellers CASCADE;

CREATE TABLE
    ecommerce.sellers (
        seller_id TEXT PRIMARY KEY,
        seller_zip_code_prefix TEXT,
        seller_city TEXT,
        seller_state TEXT
        -- FOREIGN KEY (seller_zip_code_prefix) REFERENCES ecommerce.geolocation (geolocation_zip_code_prefix)
    );

-- DROP TABLE IF EXISTS ecommerce.orders CASCADE;

CREATE TABLE
    ecommerce.orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT,
        order_status TEXT,
        order_purchase_timestamp TIMESTAMP,
        order_approved_at TIMESTAMP
        WITH
            TIME ZONE,
            order_delivered_carrier_date TIMESTAMP
        WITH
            TIME ZONE,
            order_delivered_customer_date TIMESTAMP
        WITH
            TIME ZONE,
            order_estimated_delivery_date TIMESTAMP
        WITH
            TIME ZONE,
            FOREIGN KEY (customer_id) REFERENCES ecommerce.customers (customer_id)
    );

-- DROP TABLE IF EXISTS ecommerce.product_category_name_translations CASCADE;

CREATE TABLE
    ecommerce.product_category_name_translations (
        product_category_name TEXT PRIMARY KEY,
        product_category_name_english TEXT
    );

-- DROP TABLE IF EXISTS ecommerce.products CASCADE;

CREATE TABLE
    ecommerce.products (
        product_id TEXT PRIMARY KEY,
        product_category_name TEXT,
        product_name_length INTEGER,
        description_length INTEGER,
        product_photos_qty INTEGER,
        product_weight_g INTEGER,
        product_lenght_cm INTEGER,
        product_height_cm INTEGER,
        product_width_cm INTEGER
    );

-- DROP TABLE IF EXISTS ecommerce.order_items CASCADE;

CREATE TABLE
    ecommerce.order_items (
        order_id TEXT,
        order_item_id INTEGER,
        product_id TEXT,
        seller_id TEXT,
        shipping_limit_date TIMESTAMP
        WITH
            TIME ZONE,
            price DOUBLE PRECISION,
            freight_value DOUBLE PRECISION,
            PRIMARY KEY (order_id, order_item_id),
            FOREIGN KEY (order_id) REFERENCES ecommerce.orders (order_id),
            FOREIGN KEY (product_id) REFERENCES ecommerce.products (product_id),
            FOREIGN KEY (seller_id) REFERENCES ecommerce.sellers (seller_id)
    );

-- DROP TABLE IF EXISTS ecommerce.order_payments CASCADE;

CREATE TABLE
    ecommerce.order_payments (
        order_id TEXT,
        payment_sequential INTEGER,
        payment_type TEXT,
        payment_installments INTEGER,
        payment_value DOUBLE PRECISION,
        PRIMARY KEY (order_id, payment_sequential),
        FOREIGN KEY (order_id) REFERENCES ecommerce.orders (order_id)
    );

-- DROP TABLE IF EXISTS ecommerce.order_reviews CASCADE;

CREATE TABLE
    ecommerce.order_reviews (
        review_id TEXT,
        order_id TEXT,
        review_score INTEGER,
        review_comment_title TEXT,
        review_comment_message TEXT,
        review_creation_date TIMESTAMP
        WITH
            TIME ZONE,
            review_answer_timestamp TIMESTAMP
        WITH
            TIME ZONE,
            PRIMARY KEY (review_id, order_id),
            FOREIGN KEY (order_id) REFERENCES ecommerce.orders (order_id)
        );

-- DROP SCHEMA IF EXISTS marketing CASCADE;

CREATE SCHEMA marketing;

-- DROP TABLE IF EXISTS marketing.marketing_qualified_leads CASCADE;

CREATE TABLE
    marketing.marketing_qualified_leads (
        mql_id TEXT PRIMARY KEY,
        first_contact_date DATE,
        landing_page_id TEXT,
        origin TEXT
    );

-- DROP TABLE IF EXISTS marketing.closed_deals CASCADE;

CREATE TABLE
    marketing.closed_deals (
        mql_id TEXT,
        seller_id TEXT,
        sdr_id TEXT,
        sr_id TEXT,
        won_date TIMESTAMP
        WITH
            TIME ZONE,
            business_segment TEXT,
            lead_type TEXT,
            lead_behaviour_profile TEXT,
            has_company TEXT,
            has_gtin TEXT,
            average_stock TEXT,
            business_type TEXT,
            declared_product_catalog_size DOUBLE PRECISION,
            declared_monthly_revenue DOUBLE PRECISION,
            FOREIGN KEY (mql_id) REFERENCES marketing.marketing_qualified_leads (mql_id)
    );