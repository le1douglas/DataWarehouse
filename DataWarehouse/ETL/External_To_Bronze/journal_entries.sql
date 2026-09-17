
DECLARE @FilePath NVARCHAR(400) = 'C:\Users\leone\Desktop\DataWarehouseSolution\SampleData\drip_drain_csv\journal-entries.csv';
DECLARE @RowCount INT;

BEGIN TRY
    BEGIN TRANSACTION;

    -- temporary table, doesn't get saved.
    CREATE TABLE #Staging (
        date_time NVARCHAR(50),
        subject   NVARCHAR(50),
        notes     NVARCHAR(400),
        type      NVARCHAR(50),
        ec        NVARCHAR(50),
        ec_pore   NVARCHAR(50),
        ec_bulk   NVARCHAR(50),
        ph        NVARCHAR(50),
        mc        NVARCHAR(50),
        temp      NVARCHAR(50),
        device    NVARCHAR(50),
        media     NVARCHAR(50),
        tags      NVARCHAR(50)
    );

    -- BULK INSERT does not support variables
    DECLARE @sql NVARCHAR(1000) = N'
        BULK INSERT #Staging
        FROM ''' + @FilePath + N'''
        WITH (
            FIRSTROW = 2,
            FIELDTERMINATOR = '','',
            ROWTERMINATOR = ''0x0a'',
            CODEPAGE = ''65001'',
            TABLOCK
        );';
    EXEC sp_executesql @sql;

    SELECT @RowCount = COUNT(*) FROM #Staging;


    --Copy from staging to Bronze
    INSERT INTO Bronze.journal_entries
        (date_time, subject, notes, type, ec, ec_pore, ec_bulk, ph, mc, temp, device, media, tags,
            _load_date_time, _source_file)
    SELECT
        date_time, subject, notes, type, ec, ec_pore, ec_bulk, ph, mc, temp, device, media, tags,
        SYSUTCDATETIME(), @FilePath
    FROM #Staging;


    DROP TABLE #Staging;
    COMMIT TRANSACTION;

    PRINT CONCAT('Loaded ', @RowCount, ' rows from ', @FilePath);


END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH
