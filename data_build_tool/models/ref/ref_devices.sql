select device, manufacturer, is_working
from {{ ref("seed_devices") }}
