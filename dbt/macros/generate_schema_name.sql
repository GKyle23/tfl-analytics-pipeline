{#
    Dev: every model goes into the single target dataset (dbt_dev), so
    experiments never touch real datasets.
    Cloud: a model's +schema is used as-is (staging / core / marts), matching
    the datasets that already exist in each environment's project.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.name == 'cloud' and custom_schema_name is not none -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}
    {%- endif -%}
{%- endmacro %}
