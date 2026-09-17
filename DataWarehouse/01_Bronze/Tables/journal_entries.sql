
CREATE TABLE Bronze.journal_entries(
	date_time NVARCHAR(50),
	subject NVARCHAR(50),
	notes NVARCHAR(400), --Free range comment can get long
	type NVARCHAR(50),
	ec NVARCHAR(50),
	ec_pore NVARCHAR(50),
	ec_bulk NVARCHAR(50),
	ph NVARCHAR(50),
	mc NVARCHAR(50),
	temp NVARCHAR(50),
	device NVARCHAR(50),
	media NVARCHAR(50),
	tags NVARCHAR(50),
	_load_date_time DATETIME2 NOT NULL,
	_source_file NVARCHAR(400) NOT NULL
);
