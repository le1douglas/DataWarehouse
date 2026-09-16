/*
Post-Deployment Script Template
--------------------------------------------------------------------------------------
 This file contains SQL statements that will be appended to the build script.
 Use SQLCMD syntax to include a file in the post-deployment script.
 Example:      :r .\myfile.sql
 Use SQLCMD syntax to reference a variable in the post-deployment script.
 Example:      :setvar TableName MyTable
               SELECT * FROM [$(TableName)]
--------------------------------------------------------------------------------------
*/


IF NOT EXISTS (SELECT 1 FROM Employees)
BEGIN
    INSERT INTO Employees (FirstName, LastName, Department, HireDate, Salary)
    VALUES 
        ('Anna', 'de Vries', 'Engineering', '2022-03-15', 65000.00),
        ('Bram', 'Jansen', 'Sales', '2021-07-01', 52000.00),
        ('Chloe', 'Bakker', 'Engineering', '2023-01-10', 71000.00),
        ('Daan', 'Visser', 'Marketing', '2020-11-20', 48000.00);
END