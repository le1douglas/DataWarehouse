-- publishes ref_devices, with a contract so gold presents checked types; its data tests are in ref_devices.yml
select device, manufacturer, is_working
from {{ ref("ref_devices") }}
