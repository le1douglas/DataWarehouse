-- the plants batches, typed. the file is not ours yet, so only what is unambiguous is mapped:
-- - empty to null
-- - pp_number to PP- and six digits
-- - dates from dd/mm/yyyy to yyyy-mm-dd
-- anything else fails a data test
with
    -- the open load only (landed or accepted): there is at most one, so every data test judges it alone
    select_open_load as (
        select *
        from {{ source("dw_bronze", "brnz_plants_batches") }}
        where load_id in ({{ loads_in_state(["landed", "accepted"]) }})
    ),

    -- empty means null
    nullify_empty as (
        select
            row_id,
            nullif(room, '') as room,
            nullif(strain, '') as strain,
            nullif(pp_number, '') as pp_number,
            nullif(date_veg_start, '') as date_veg_start,
            nullif(date_flower_start, '') as date_flower_start,
            nullif(date_flower_end, '') as date_flower_end,
            nullif(plants_number, '') as plants_number
        from select_open_load
    ),

    -- PP000366 and PP-000366 both become PP-000366. any other shape fails its format test
    normalize_pp_number as (
        select
            row_id,
            room,
            strain,
            regexp_replace(pp_number, '^PP-?(\d{6})$', 'PP-\1') as pp_number,
            date_veg_start,
            date_flower_start,
            date_flower_end,
            plants_number
        from nullify_empty
    ),

    -- the server's DateStyle (ISO, YMD) cannot read dd/mm/yyyy. any other shape is left to the cast
    -- TODO a macro or a library instead of a regex per column (docs/REMINDERS.md)
    reorder_dates as (
        select
            row_id,
            room,
            strain,
            pp_number,
            regexp_replace(date_veg_start, '^(\d{2})/(\d{2})/(\d{4})$', '\3-\2-\1') as date_veg_start,
            regexp_replace(date_flower_start, '^(\d{2})/(\d{2})/(\d{4})$', '\3-\2-\1') as date_flower_start,
            regexp_replace(date_flower_end, '^(\d{2})/(\d{2})/(\d{4})$', '\3-\2-\1') as date_flower_end,
            plants_number
        from normalize_pp_number
    )

    {{ cast_select("reorder_dates") }}
