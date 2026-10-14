{{ config(severity="error", store_failures=true) }}

-- silver casts the measurements without a guard, so a value that cannot be cast must stop it here.
-- an empty value is null and passes: pg_input_is_valid of null is null
select *
from {{ ref("cand_journal_entries") }}
where
    {%- for col in var("journal_entries_numeric_columns") %}
        not pg_input_is_valid({{ col }}, 'numeric') {{- " or" if not loop.last }}
    {%- endfor %}
