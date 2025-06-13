DROP SCHEMA IF EXISTS ecommerce CASCADE;

CREATE SCHEMA ecommerce;

--This table has information Brazilian zip codes and its lat/lng coordinates. Use it to plot maps and find distances between sellers and customers.
CREATE TABLE
    ecommerce.geolocation (
        geolocation_zip_code_prefix TEXT PRIMARY KEY, --first 5 digits of zip code
        geolocation_lat DOUBLE PRECISION, --latitude
        geolocation_lng DOUBLE PRECISION, --longitude
        geolocation_city TEXT, --city name
        geolocation_state TEXT --state
    );

--This table has information about the customer and its location. Use it to identify unique customers in the orders table and to find the orders delivery location.
--At our system each order is assigned to a unique customer_id.
--This means that the same customer will get different ids for different orders.
--The purpose of having a customer_unique_id on the table is to allow you to identify customers that made repurchases at the store.
--Otherwise you would find that each order had a different customer associated with.
CREATE TABLE
    ecommerce.customers (
        customer_id TEXT PRIMARY KEY, --key to the orders table. Each order has a unique customer_id.
        customer_unique_id TEXT, --unique identifier of a customer.
        customer_zip_code_prefix TEXT, --first five digits of customer zip code
        customer_city TEXT, --customer city name
        customer_state TEXT --customer state
    );

--This table includes data about the sellers that fulfilled orders made at Olist. Use it to find the seller location and to identify which seller fulfilled each product.
CREATE TABLE
    ecommerce.sellers (
        seller_id TEXT PRIMARY KEY, --seller unique identifier
        seller_zip_code_prefix TEXT, --first 5 digits of seller zip code
        seller_city TEXT, --seller city name
        seller_state TEXT --seller state
        -- FOREIGN KEY (seller_zip_code_prefix) REFERENCES ecommerce.geolocation (geolocation_zip_code_prefix)
    );

--This is the core table. From each order you might find all other information.
CREATE TABLE
    ecommerce.orders (
        order_id TEXT PRIMARY KEY, --unique identifier of the order.
        customer_id TEXT, --key to the customer table. Each order has a unique customer_id.
        order_status TEXT, --Reference to the order status (delivered, shipped, etc).
        order_purchase_timestamp TIMESTAMP, --Shows the purchase timestamp.
        order_approved_at TIMESTAMP
        WITH
            TIME ZONE, --Shows the payment approval timestamp.
            order_delivered_carrier_date TIMESTAMP
        WITH
            TIME ZONE, --Shows the order posting timestamp. When it was handled to the logistic partner.
            order_delivered_customer_date TIMESTAMP
        WITH
            TIME ZONE, --Shows the actual order delivery date to the customer.
            order_estimated_delivery_date TIMESTAMP
        WITH
            TIME ZONE, --Shows the estimated delivery date that was informed to customer at the purchase moment.
            FOREIGN KEY (customer_id) REFERENCES ecommerce.customers (customer_id)
    );

--Translates the product_category_name to english.
CREATE TABLE
    ecommerce.product_category_name_translations (
        product_category_name TEXT PRIMARY KEY, --category name in Portuguese
        product_category_name_english TEXT --category name in English
    );

--This table includes data about the products sold by Olist.
CREATE TABLE
    ecommerce.products (
        product_id TEXT PRIMARY KEY, --unique product identifier
        product_category_name TEXT, --root category of product, in Portuguese.
        product_name_length INTEGER, --number of characters extracted from the product name.
        description_length INTEGER, --number of characters extracted from the product description.
        product_photos_qty INTEGER, --number of product published photos
        product_weight_g INTEGER, --product weight measured in grams.
        product_lenght_cm INTEGER, --product length measured in centimeters.
        product_height_cm INTEGER, --product height measured in centimeters.
        product_width_cm INTEGER --product width measured in centimeters.
    );

--This table includes data about the items purchased within each order.
CREATE TABLE
    ecommerce.order_items (
        order_id TEXT, --order unique identifier
        order_item_id INTEGER, --sequential number identifying number of items included in the same order.
        product_id TEXT, --product unique identifier
        seller_id TEXT, --seller unique identifier
        shipping_limit_date TIMESTAMP
        WITH
            TIME ZONE, --Shows the seller shipping limit date for handling the order over to the logistic partner.
            price DOUBLE PRECISION, --item price
            freight_value DOUBLE PRECISION, --item freight value item (if an order has more than one item the freight value is splitted between items)
            PRIMARY KEY (order_id, order_item_id),
            FOREIGN KEY (order_id) REFERENCES ecommerce.orders (order_id),
            FOREIGN KEY (product_id) REFERENCES ecommerce.products (product_id),
            FOREIGN KEY (seller_id) REFERENCES ecommerce.sellers (seller_id)
    );

--This table includes data about the orders payment options.
CREATE TABLE
    ecommerce.order_payments (
        order_id TEXT, --unique identifier of an order.
        payment_sequential INTEGER, --a customer may pay an order with more than one payment method. If he does so, a sequence will be created to
        payment_type TEXT, --method of payment chosen by the customer.
        payment_installments INTEGER, --number of installments chosen by the customer.
        payment_value DOUBLE PRECISION, --transaction value.
        PRIMARY KEY (order_id, payment_sequential),
        FOREIGN KEY (order_id) REFERENCES ecommerce.orders (order_id)
    );

--This table includes data about the reviews made by the customers.
--After a customer purchases the product from Olist Store a seller gets notified to fulfill that order.
--Once the customer receives the product, or the estimated delivery date is due,
--the customer gets a satisfaction survey by email where he can give a note for the purchase experience and write down some comments.
CREATE TABLE
    ecommerce.order_reviews (
        review_id TEXT, --unique review identifier
        order_id TEXT, --unique order identifier
        review_score INTEGER, --Note ranging from 1 to 5 given by the customer on a satisfaction survey.
        review_comment_title TEXT, --Comment title from the review left by the customer, in Portuguese.
        review_comment_message TEXT, --Comment message from the review left by the customer, in Portuguese.
        review_creation_date TIMESTAMP
        WITH
            TIME ZONE, --Shows the date in which the satisfaction survey was sent to the customer.
            review_answer_timestamp TIMESTAMP
        WITH
            TIME ZONE, --Shows satisfaction survey answer timestamp.
            PRIMARY KEY (review_id, order_id),
            FOREIGN KEY (order_id) REFERENCES ecommerce.orders (order_id)
    );


CREATE SCHEMA marketing;

--After a lead fills in a form at a landing page, a filter is made to select the ones that are qualified to sell their products at Olist.
--They are the Marketing Qualified Leads (MQLs).
CREATE TABLE
    marketing.marketing_qualified_leads (
        mql_id TEXT PRIMARY KEY, --Marketing Qualified Lead id
        first_contact_date DATE, --Date of the first contact solicitation.
        landing_page_id TEXT, --Landing page id where the lead was acquired
        origin TEXT --Type of media where the lead was acquired
    );

--After a qualified lead fills in a form at a landing page he is contacted by a Sales Development Representative.
--At this step some information is checked and more information about the lead is gathered.
CREATE TABLE
    marketing.closed_deals (
        mql_id TEXT, --Marketing Qualified Lead id
        seller_id TEXT, --Seller id
        sdr_id TEXT, --Sales Development Representative id
        sr_id TEXT, --Sales Representative
        won_date TIMESTAMP
        WITH
            TIME ZONE, --Date the deal was closed.
            business_segment TEXT, --Lead business segment. Informed on contact.
            lead_type TEXT, --Lead type. Informed on contact.
            lead_behaviour_profile TEXT, --Lead behaviour profile. SDR identify it on contact
            has_company TEXT, --Does the lead have a company (formal documentation)?
            has_gtin TEXT, --Does the lead have Global Trade Item Number (barcode) for his products?
            average_stock TEXT, --Lead declared average stock. Informed on contact.
            business_type TEXT, --Type of business (reseller/manufacturer etc.)
            declared_product_catalog_size DOUBLE PRECISION, --Lead declared catalog size. Informed on contact.
            declared_monthly_revenue DOUBLE PRECISION, --Lead declared estimated monthly revenue. Informed on contact.
            FOREIGN KEY (mql_id) REFERENCES marketing.marketing_qualified_leads (mql_id)
    );
