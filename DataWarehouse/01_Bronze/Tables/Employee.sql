--IF NOT EXISTS is handled by the publish script
CREATE TABLE Bronze.Employees (
    EmployeeID INT IDENTITY(1,1) PRIMARY KEY,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    Department NVARCHAR(50),
    HireDate DATE,
    Salary DECIMAL(10,2)
);