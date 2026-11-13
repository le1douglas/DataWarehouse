-- the staged plants batches. the file is not ours yet, so only what is unambiguous is mapped: empty to null, dates
-- from dd/mm/yyyy to ISO, pp_number to PP- and six digits. anything else is an upstream fault and fails a data test.
-- the output is typed, see cast_select
with
    mapped as (
        select
            -- the key, assigned by bronze. it is carried through every step unchanged
            row_id,
            nullif(room, '') as room,
            nullif(strain, '') as strain,
            -- PP000366 and PP-000366 both become PP-000366. any other shape stays as it is and fails its format test
            regexp_replace(nullif(pp_number, ''), '^PP-?(\d{6})$', 'PP-\1') as pp_number,
            -- the file sends dates as dd/mm/yyyy, which the server's DateStyle (ISO, YMD) cannot read: reordered to ISO
            -- yyyy-mm-dd, which every DateStyle reads one way only. any other shape stays as it is, and fails the cast
            -- if it cannot be read.
            -- TODO a macro or a library instead of a regex per column (docs/REMINDERS.md)
            regexp_replace(nullif(date_veg_start, ''), '^(\d{2})/(\d{2})/(\d{4})$', '\3-\2-\1') as date_veg_start,
            regexp_replace(nullif(date_flower_start, ''), '^(\d{2})/(\d{2})/(\d{4})$', '\3-\2-\1') as date_flower_start,
            regexp_replace(nullif(date_flower_end, ''), '^(\d{2})/(\d{2})/(\d{4})$', '\3-\2-\1') as date_flower_end,
            nullif(plants_number, '') as plants_number
        from {{ source("dw_bronze", "brnz_plants_batches") }}
        -- one load only, the load_id var, so every data test judges that load alone. without the var, compilation fails
        where load_id = '{{ var("load_id") }}'::uuid
    )

    {{ cast_select("mapped") }}
