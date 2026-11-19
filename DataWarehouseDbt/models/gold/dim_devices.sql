select device, manufacturer, is_working
from {{ ref("ref_devices") }}
