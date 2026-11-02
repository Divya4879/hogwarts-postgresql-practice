# Hogwarts SQL Practice

A personal PostgreSQL practice repository built around a fictional Hogwarts exam database.

It contains a relational dataset, 30 SQL challenges, and a separate file of reference solutions. The goal is simple: practise writing SQL, understand PostgreSQL features, and improve problem-solving through hands-on queries.

## Repository Structure

| File | Description |
|---|---|
| [`init/01_schema.sql`](init/01_schema.sql) | Creates the database tables and constraints |
| [`init/02_seed.sql`](init/02_seed.sql) | Inserts the sample Hogwarts data |
| [`workspace/03_challenges.sql`](workspace/03_challenges.sql) | 30 SQL questions to solve |
| [`solutions/04_solutions.sql`](solutions/04_solutions.sql) | Reference solutions |

## Database Schema

The database consists of four tables:

- **houses** - Hogwarts houses and their heads.
- **students** - Student details, Hogwarts year, and house.
- **courses** - Course names and professors.
- **exams** - Student exam records, dates, and grades.

The grade values used in the dataset are:

`o++`, `o+`, `o`, `ee`, `a`, `p`, `troll`

The schema includes primary keys, foreign keys, uniqueness constraints, and check constraints.

## Getting Started

You need PostgreSQL installed and a SQL client such as `psql`, pgAdmin, or DBeaver.

### 1. Create a database

```sql
CREATE DATABASE hogwarts;
```

### 2. Create the tables

Run:

```bash
psql -d hogwarts -f init/01_schema.sql
```

### 3. Insert the sample data

Run:

```bash
psql -d hogwarts -f init/02_seed.sql
```

### 4. Connect to the database

```bash
psql -d hogwarts
```

You can now start solving the challenges.

**Note:** `01_schema.sql` contains `DROP TABLE IF EXISTS` statements. Running it again will drop and recreate the tables, deleting existing data. Run the seed file only after creating a fresh schema; running it repeatedly will attempt to insert duplicate records.

## SQL Challenges

The repository contains 30 questions arranged progressively:

| Level | Questions | Topics |
|---|---|---|
| Basic | Q1-Q6 | Filtering, sorting, joins, and basic aggregations |
| Intermediate | Q7-Q13 | Conditional logic, subqueries, grouping, and GPA calculations |
| Advanced | Q14-Q20 | Window functions, CTEs, JSONB, relational division, and conditional aggregation |
| Expert | Q21-Q25 | ROLLUP, statistical functions, arrays, gap analysis, and moving averages |
| PostgreSQL Mastery | Q26-Q30 | Data auditing, UPSERT, recursive CTEs, materialized views, and query optimization |

## Practice Workflow

1. Open `workspace/03_challenges.sql`.
2. Choose a question and write your query below its description.
3. Execute it against your PostgreSQL database.
4. Verify the output and consider edge cases.
5. Refer to `solutions/04_solutions.sql` after attempting the question.

The solutions are reference implementations, not the only possible ways to solve the problems. Focus on understanding why a query works and whether it handles the requirements correctly.

## Topics Practised

- SQL filtering, joins, and aggregations
- GROUP BY and HAVING
- CASE expressions and subqueries
- Common Table Expressions (CTEs)
- Window functions and window frames
- Ranking and cumulative calculations
- JSONB construction and aggregation
- Relational division using EXCEPT ALL
- PostgreSQL arrays and containment operators
- ROLLUP and statistical functions
- Date generation and gap analysis
- Moving averages
- INSERT ... ON CONFLICT
- Recursive CTEs
- Materialized views
- EXPLAIN ANALYZE and query performance

---

**The purpose of this repository is to practise PostgreSQL through actual SQL problems.** The focus is on writing queries, understanding database behaviour, and building confidence with increasingly advanced SQL concepts.