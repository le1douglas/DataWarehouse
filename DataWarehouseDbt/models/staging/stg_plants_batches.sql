-- the plants batches, typed. the file is not ours yet, so only what is unambiguous is mapped:
-- - empty to null
-- - dates from dd/mm/yyyy to yyyy-mm-dd
-- - pp_number to PP- and six digits
-- anything else fails a data test
with
    mapped as (
        select
            row_id,
            nullif(room, '') as room,
            nullif(strain, '') as strain,
            -- PP000366 and PP-000366 both become PP-000366. any other shape fails its format test
            regexp_replace(nullif(pp_number, ''), '^PP-?(\d{6})$', 'PP-\1') as pp_number,
            -- the server's DateStyle (ISO, YMD) cannot read dd/mm/yyyy. any other shape is left to the cast
            -- TODO a macro or a library instead of a regex per column (docs/REMINDERS.md)
            regexp_replace(nullif(date_veg_start, ''), '^(\d{2})/(\d{2})/(\d{4})$', '\3-\2-\1') as date_veg_start,
            regexp_replace(nullif(date_flower_start, ''), '^(\d{2})/(\d{2})/(\d{4})$', '\3-\2-\1') as date_flower_start,
            regexp_replace(nullif(date_flower_end, ''), '^(\d{2})/(\d{2})/(\d{4})$', '\3-\2-\1') as date_flower_end,
            nullif(plants_number, '') as plants_number
        from {{ source("dw_bronze", "brnz_plants_batches") }}
        -- the open load only (landed or accepted): there is at most one, so every data test judges it alone
        where load_id in ({{ loads_in_state(["landed", "accepted"]) }})
    )

    {{ cast_select("mapped") }}
