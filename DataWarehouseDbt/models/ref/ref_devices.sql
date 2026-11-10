-- the measuring devices, from seed_devices. dbt infers the types (dbt_project.yml)
select device, manufacturer, is_working
from {{ ref("seed_devices") }}
