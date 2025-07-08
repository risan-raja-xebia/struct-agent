"""
Usage examples for the semantic modeling package
"""

import os
from ..core.generator import SemanticModelGenerator
from ..core.base import (
    Dimension, DimensionType, TimeGranularity,
    Measure, MeasureType, Segment, Join, JoinType,
    PreAggregation, Cube
    # View, ViewCube
)

def example_basic_usage():
    """Basic usage example"""
    # Initialize generator
    generator = SemanticModelGenerator(
        database_url='postgresql+psycopg2://admin:admin123@172.19.215.172:5432/ecommerce_db',
        default_schema='ecommerce'
    )

    # Generate a cube for a specific table
    cube = generator.generate_cube_from_table('orders')

    # Generate YAML
    yaml_content = generator.generate_yaml(cube)
    print("Generated YAML:")
    print(yaml_content)

    # Save to file
    os.makedirs('output', exist_ok=True)
    with open('output/orders.yaml', 'w') as f:
        f.write(yaml_content)

def example_multi_stage_calculation():
    """Multi-stage calculation example"""
    generator = SemanticModelGenerator(
        database_url='postgresql+psycopg2://admin:admin123@172.19.215.172:5432/ecommerce_db',
        default_schema='ecommerce'
    )

    # Define custom stage calculations
    stage_definitions = [
        {
            'name': 'orders_daily_agg',
            'measures': ['count', 'total_amount'],
            'description': 'Daily order aggregation'
        },
        {
            'name': 'orders_monthly_summary',
            'measures': ['monthly_total', 'avg_daily_orders'],
            'description': 'Monthly summary with calculated measures'
        }
    ]

    # Generate multi-stage cubes
    cubes = generator.generate_multi_stage_cube('orders', stage_definitions=stage_definitions)

    # Generate YAML for each stage
    for cube in cubes:
        yaml_content = generator.generate_yaml(cube)
        print(f"\n--- {cube.name} ---")
        print(yaml_content)

def example_custom_cube_with_advanced_features():
    """Example of creating a custom cube with advanced features"""

    # Create custom dimensions
    dimensions = [
        Dimension(
            name='order_id',
            sql='id',
            type=DimensionType.NUMBER,
            primary_key=True,
            description='Unique order identifier'
        ),
        Dimension(
            name='order_date',
            sql='created_at',
            type=DimensionType.TIME,
            granularities=[TimeGranularity.DAY, TimeGranularity.MONTH, TimeGranularity.YEAR],
            description='Order creation date'
        ),
        Dimension(
            name='customer_tier',
            sql="CASE WHEN total_amount > 1000 THEN 'premium' ELSE 'standard' END",
            type=DimensionType.STRING,
            description='Customer tier based on order value'
        )
    ]

    # Create custom measures
    measures = [
        Measure(
            name='order_count',
            type=MeasureType.COUNT,
            description='Total number of orders'
        ),
        Measure(
            name='total_revenue',
            type=MeasureType.SUM,
            sql='amount',
            description='Total revenue from orders',
            format='currency'
        ),
        Measure(
            name='avg_order_value',
            type=MeasureType.AVG,
            sql='amount',
            description='Average order value',
            format='currency'
        ),
        Measure(
            name='revenue_growth',
            type=MeasureType.NUMBER,
            sql='({total_revenue} - LAG({total_revenue}) OVER (ORDER BY {order_date})) / LAG({total_revenue}) OVER (ORDER BY {order_date}) * 100',
            description='Revenue growth percentage',
            format='percent'
        )
    ]

    # Create segments
    segments = [
        Segment(
            name='high_value_orders',
            sql='{CUBE}.amount > 500',
            description='Orders with amount greater than $500'
        ),
        Segment(
            name='recent_orders',
            sql='{CUBE}.created_at >= CURRENT_DATE - INTERVAL \'30 days\'',
            description='Orders from the last 30 days'
        )
    ]

    # Create joins
    joins = [
        Join(
            name='customers',
            sql='{CUBE}.customer_id = {customers.id}',
            relationship=JoinType.MANY_TO_ONE,
            description='Join to customer information'
        ),
        Join(
            name='order_items',
            sql='{CUBE}.id = {order_items.order_id}',
            relationship=JoinType.ONE_TO_MANY,
            description='Join to order line items'
        )
    ]

    # Create pre-aggregations
    pre_aggregations = [
        PreAggregation(
            name='orders_by_date',
            measures=['order_count', 'total_revenue'],
            dimensions=['order_date'],
            time_dimension='order_date',
            granularity=TimeGranularity.DAY,
            refresh_key={'every': '1 hour'}
        )
    ]

    # Create the cube
    advanced_cube = Cube(
        name='advanced_orders',
        sql_table='ecommerce.orders',
        description='Advanced orders cube with custom calculations',
        dimensions=dimensions,
        measures=measures,
        segments=segments,
        joins=joins,
        pre_aggregations=pre_aggregations
    )

    # Generate YAML
    generator = SemanticModelGenerator(
        database_url='postgresql+psycopg2://admin:admin123@172.19.215.172:5432/ecommerce_db',
        default_schema='ecommerce'
    )

    yaml_content = generator.generate_yaml(advanced_cube)
    print("Advanced Cube YAML:")
    print(yaml_content)

def example_create_view():
    """Example of creating a view that combines multiple cubes"""
    generator = SemanticModelGenerator(
        database_url='postgresql+psycopg2://admin:admin123@172.19.215.172:5432/ecommerce_db',
        default_schema='ecommerce'
    )

    # Define how to combine cubes in a view
    cube_joins = [
        {
            'join_path': 'orders',
            'includes': ['order_id', 'order_date', 'order_count', 'total_revenue'],
            'excludes': []
        },
        {
            'join_path': 'orders.customers',
            'includes': ['customer_name', 'customer_tier'],
            'prefix': True  # This will prefix customer fields with 'customer_'
        },
        {
            'join_path': 'orders.order_items.products',
            'includes': ['product_name', 'category'],
            'alias': 'product'
        }
    ]

    # Generate the view
    view = generator.generate_view('comprehensive_orders', cube_joins)

    # Generate YAML for the view
    yaml_content = generator.generate_yaml(view, template_name='view.yaml.j2')
    print("View YAML:")
    print(yaml_content)

def example_polymorphic_cube():
    """Example of polymorphic cube (cube inheritance)"""

    # Base cube
    base_cube = Cube(
        name='base_transactions',
        sql_table='transactions',
        description='Base transaction cube',
        dimensions=[
            Dimension('transaction_id', 'id', DimensionType.NUMBER, primary_key=True),
            Dimension('transaction_date', 'created_at', DimensionType.TIME),
            Dimension('amount', 'amount', DimensionType.NUMBER)
        ],
        measures=[
            Measure('transaction_count', MeasureType.COUNT),
            Measure('total_amount', MeasureType.SUM, sql='amount')
        ]
    )

    # Specialized cube that extends the base
    payment_cube = Cube(
        name='payment_transactions',
        extends='base_transactions',
        description='Payment-specific transactions',
        segments=[
            Segment('payment_only', "{CUBE}.type = 'payment'", 'Only payment transactions')
        ],
        measures=[
            Measure('avg_payment_amount', MeasureType.AVG, sql='amount'),
            Measure('successful_payments', MeasureType.COUNT, sql='CASE WHEN status = \'success\' THEN 1 END')
        ]
    )

    generator = SemanticModelGenerator(
        database_url='postgresql+psycopg2://admin:admin123@172.19.215.172:5432/ecommerce_db',
        default_schema='ecommerce'
    )

    # Generate YAML for both cubes
    print("Base Cube:")
    print(generator.generate_yaml(base_cube))

    print("\nExtended Cube:")
    print(generator.generate_yaml(payment_cube))

def example_dynamic_configuration():
    """Example of dynamic configuration generation using Jinja"""

    # Create a custom template with dynamic logic
    dynamic_template = '''
{% set table_name = cube.name %}
{% set has_date_column = cube.dimensions | selectattr('type', 'equalto', 'time') | list | length > 0 %}

cubes:
  - name: {{ cube.name }}
    sql_table: {{ cube.sql_table }}

    dimensions:
      {% for dimension in cube.dimensions %}
      - name: {{ dimension.name }}
        sql: {{ dimension.sql }}
        type: {{ dimension.type }}
        {% if dimension.primary_key %}primary_key: true{% endif %}
        {% if dimension.type == 'time' %}
        granularities:
          {% for granularity in dimension.granularities %}
          - {{ granularity }}
          {% endfor %}
        {% endif %}
      {% endfor %}

    measures:
      {% for measure in cube.measures %}
      - name: {{ measure.name }}
        type: {{ measure.type }}
        {% if measure.sql %}sql: {{ measure.sql }}{% endif %}
      {% endfor %}

      {% if has_date_column %}
      # Auto-generated time-based measures
      - name: records_last_7_days
        type: count
        filters:
          - sql: "{{ cube.dimensions | selectattr('type', 'equalto', 'time') | first | attr('sql') }} >= CURRENT_DATE - INTERVAL '7 days'"

      - name: records_last_30_days
        type: count
        filters:
          - sql: "{{ cube.dimensions | selectattr('type', 'equalto', 'time') | first | attr('sql') }} >= CURRENT_DATE - INTERVAL '30 days'"
      {% endif %}

    {% if has_date_column %}
    # Auto-generated pre-aggregations for time-based data
    pre_aggregations:
      - name: by_day
        measures:
          - count
          {% for measure in cube.measures %}
          {% if measure.type in ['sum', 'count'] %}
          - {{ measure.name }}
          {% endif %}
          {% endfor %}
        time_dimension: {{ cube.dimensions | selectattr('type', 'equalto', 'time') | first | attr('name') }}
        granularity: day
        refresh_key:
          every: 1 hour
    {% endif %}
'''

    # Use the dynamic template
    from jinja2 import Template
    template = Template(dynamic_template)

    # Create a sample cube
    cube = Cube(
        name='dynamic_orders',
        sql_table='orders',
        dimensions=[
            Dimension('id', 'id', DimensionType.NUMBER, primary_key=True),
            Dimension('created_at', 'created_at', DimensionType.TIME,
                     granularities=[TimeGranularity.DAY, TimeGranularity.MONTH]),
            Dimension('status', 'status', DimensionType.STRING)
        ],
        measures=[
            Measure('count', MeasureType.COUNT),
            Measure('total_amount', MeasureType.SUM, sql='amount')
        ]
    )

    # Render with dynamic logic
    yaml_content = template.render(cube=cube.to_dict())
    print("Dynamic Configuration:")
    print(yaml_content)

# Run examples
if __name__ == '__main__':
    print("=== Basic Usage ===")
    example_basic_usage()

    # print("\n=== Multi-Stage Calculation ===")
    # example_multi_stage_calculation()

    # print("\n=== Advanced Custom Cube ===")
    # example_custom_cube_with_advanced_features()

    # print("\n=== View Creation ===")
    # example_create_view()

    # print("\n=== Polymorphic Cube ===")
    # example_polymorphic_cube()

    # print("\n=== Dynamic Configuration ===")
    # example_dynamic_configuration()
