# Hogwarts PostgreSQL Practice

A PostgreSQL practice repository built around a fictional Hogwarts academic database.

The repository contains a relational schema, sample data, 30 SQL challenges, and reference solutions covering foundational SQL and advanced PostgreSQL features.

---

## Repository Structure

| Path | Description |
|---|---|
| [`init/01_schema.sql`](init/01_schema.sql) | Database tables, relationships, and constraints |
| [`init/02_seed.sql`](init/02_seed.sql) | Sample data for the database |
| [`workspace/03_challenges.sql`](workspace/03_challenges.sql) | 30 SQL practice questions |
| [`solutions/04_solutions.sql`](solutions/04_solutions.sql) | Reference query solutions |

---

## Database Schema

The database models Hogwarts students, houses, courses, and examination records.

| Table | Description |
|---|---|
| `houses` | Houses and their heads |
| `students` | Student records and house associations |
| `courses` | Courses and assigned professors |
| `exams` | Examination records, dates, and grades |

The schema uses:

- Primary and foreign keys
- Unique constraints
- Check constraints
- Referential integrity

The sample dataset uses the following grade values:

`o++`, `o+`, `o`, `ee`, `a`, `p`, `troll`

---

## Setting Up PostgreSQL with VS Code (Ubuntu/WSL)

This project uses PostgreSQL as its database and VS Code with SQLTools as the SQL editor.

Follow the steps below to set up the project from scratch.

### 1. Install PostgreSQL

**Where:** Ubuntu (WSL) terminal.

Open your Ubuntu terminal and run:

```bash
sudo apt update
sudo apt install -y git postgresql
sudo systemctl enable --now postgresql
```

Verify that PostgreSQL is running:

```bash
sudo systemctl is-active postgresql
```

Expected output:

```text
active
```

### 2. Install VS Code and SQLTools

**Where:** VS Code application.

If you do not have VS Code installed, download it from the [official Visual Studio Code website](https://code.visualstudio.com/).

Open VS Code and install these extensions from the Extensions Marketplace:

- **SQLTools** — SQL client for VS Code.
- **SQLTools PostgreSQL/Cockroach Driver** — PostgreSQL database driver for SQLTools.

### 3. Clone the Repository

**Where:** Ubuntu (WSL) terminal.

Navigate to the directory where you want to store the project and run:

```bash
git clone https://github.com/Divya4879/hogwarts-postgresql-practice.git
cd hogwarts-postgresql-practice
```

Open the project in VS Code:

```bash
code .
```

### 4. Create the PostgreSQL User and Database

**Where:** Ubuntu (WSL) terminal.

Create a PostgreSQL role matching your Ubuntu username:

```bash
sudo -u postgres createuser "$USER"
```

If the role already exists, skip this command.

Create the project database:

```bash
sudo -u postgres createdb --owner="$USER" hogwarts_sandbox
```

Grant your Ubuntu user permission to create tables in the `public` schema:

```bash
sudo -u postgres psql -d hogwarts_sandbox -c "GRANT ALL ON SCHEMA public TO \"$USER\";"
```

### 5. Set a Password for Your PostgreSQL User

**Where:** Ubuntu (WSL) terminal.

SQLTools uses a TCP connection to communicate with PostgreSQL, so configure a password for your database role.

Open the PostgreSQL shell:

```bash
sudo -u postgres psql
```

Inside the PostgreSQL shell, run:

```sql
\password your_ubuntu_username
```

Replace `your_ubuntu_username` with the username returned by:

```bash
whoami
```

Enter and confirm a password when prompted.

Exit the PostgreSQL shell:

```sql
\q
```

### 6. Initialize the Project Database

**Where:** VS Code integrated terminal (Ubuntu/WSL).

Make sure the terminal is in the repository root directory:

```text
hogwarts-postgresql-practice/
```

Run the schema script first:

```bash
psql -d hogwarts_sandbox -f init/01_schema.sql
```

Then load the sample data:

```bash
psql -d hogwarts_sandbox -f init/02_seed.sql
```

The first script creates the database tables, and the second inserts the sample Hogwarts records.

### 7. Connect PostgreSQL to VS Code

**Where:** VS Code application.

1. Open the SQLTools sidebar.
2. Select **Add New Connection**.
3. Choose **PostgreSQL**.
4. Enter the following connection details:

| Setting | Value |
|---|---|
| Connection name | Hogwarts PostgreSQL |
| Server/Host | `localhost` |
| Port | `5432` |
| Database | `hogwarts_sandbox` |
| Username | Your Ubuntu username |
| Password | The password configured in Step 5 |

5. Save the connection and select **Connect**.

You should now be connected to your Hogwarts database through VS Code.

### 8. Verify the Database Connection

**Where:** VS Code SQL editor.

Open a new SQL file or use the SQL editor and execute:

```sql
SELECT *
FROM students
LIMIT 10;
```

If student records appear in the results, your database connection and sample data are working.

You can also verify the tables from the VS Code integrated terminal:

```bash
psql -d hogwarts_sandbox
```

Inside the PostgreSQL shell:

```sql
\dt
```

Exit using:

```sql
\q
```

---

## SQL Challenges

The 30 challenges cover the following areas:

| Questions | Topics |
|---|---|
| Q1-Q6 | Filtering, sorting, joins, and basic aggregations |
| Q7-Q13 | Conditional expressions, subqueries, grouping, and GPA calculations |
| Q14-Q20 | Window functions, CTEs, JSONB, relational division, and conditional aggregation |
| Q21-Q25 | ROLLUP, statistical functions, arrays, gap analysis, and moving averages |
| Q26-Q30 | Data integrity auditing, UPSERT, recursive CTEs, materialized views, and query optimization |

---

## PostgreSQL Concepts

The exercises include:

- Filtering and sorting
- INNER JOIN and other join operations
- GROUP BY and HAVING
- CASE expressions and subqueries
- Common Table Expressions (CTEs)
- Window functions and window frames
- Ranking and cumulative calculations
- JSONB construction and aggregation
- Relational division using `EXCEPT ALL`
- Array operations and containment operators
- ROLLUP and statistical functions
- `generate_series()` and date gap analysis
- Moving averages
- `INSERT ... ON CONFLICT`
- Recursive CTEs
- Materialized views
- `EXPLAIN ANALYZE`

---

## Practice Workflow

All 30 questions can be practised directly in VS Code using SQLTools.

### Where to Practise

Open the following file in VS Code:

```text
workspace/03_challenges.sql
```

This is your main practice workbook.

### How to Solve and Execute Questions

1. Open `workspace/03_challenges.sql` in VS Code.
2. Connect SQLTools to the `hogwarts_sandbox` database.
3. Read a question and write your SQL solution below it.
4. Select the query you want to execute.
5. Right-click and select **Run Query**, or use the SQLTools execute command.
6. Check the query results in the VS Code results panel.
7. Modify and execute your query again if the output is incorrect.

You can also create a separate `.sql` file inside the `workspace/` directory if you prefer keeping your attempts separate.

### Checking Your Solutions

Reference solutions are available in:

```text
solutions/04_solutions.sql
```

Attempt each question independently before referring to the solutions.

The solutions are reference implementations; alternative queries may also satisfy the requirements.

---

## Important Notes

- Run `init/01_schema.sql` before `init/02_seed.sql`.
- Run the seed script only once on a fresh database.
- The schema script contains `DROP TABLE IF EXISTS` statements. Re-running it drops and recreates the tables, deleting existing data.
- Keep the PostgreSQL service running while using SQLTools in VS Code.
- The database name used throughout this setup is `hogwarts_sandbox`.
- You do not need pgAdmin or DBeaver for this setup.

---

Happy querying!