# Hogwarts SQL Practice

A PostgreSQL practice repository built around a fictional Hogwarts academic database.

The repository contains a relational schema, sample data, 30 SQL challenges, and reference solutions covering foundational SQL and advanced PostgreSQL features.

## Repository Structure

| Path | Description |
|---|---|
| [`init/01_schema.sql`](init/01_schema.sql) | Database tables, relationships, and constraints |
| [`init/02_seed.sql`](init/02_seed.sql) | Sample data for the database |
| [`workspace/03_challenges.sql`](workspace/03_challenges.sql) | 30 SQL practice questions |
| [`solutions/04_solutions.sql`](solutions/04_solutions.sql) | Reference query solutions |

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

## Setup

**Requirements:** PostgreSQL and a SQL client (`psql`, pgAdmin, or DBeaver).

### 1. Create the database

```sql
CREATE DATABASE hogwarts;
````

### 2. Create the schema

Run from the repository root:

```
psql -d hogwarts -f init/01_schema.sql
```

### 3. Load sample data

```
psql -d hogwarts -f init/02_seed.sql
```

### 4. Connect to the database

```
psql -d hogwarts
```

Important: The schema script contains `DROP TABLE IF EXISTS` statements. Re-running it drops and recreates the tables, deleting existing data. Run the seed script only once after creating the schema to avoid duplicate records.

## SQL Challenges

The 30 challenges cover the following areas:

| Questions | Topics                                                                                      |
| --------- | ------------------------------------------------------------------------------------------- |
| Q1-Q6     | Filtering, sorting, joins, and basic aggregations                                           |
| Q7-Q13    | Conditional expressions, subqueries, grouping, and GPA calculations                         |
| Q14-Q20   | Window functions, CTEs, JSONB, relational division, and conditional aggregation             |
| Q21-Q25   | ROLLUP, statistical functions, arrays, gap analysis, and moving averages                    |
| Q26-Q30   | Data integrity auditing, UPSERT, recursive CTEs, materialized views, and query optimization |

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

## Practice Workflow

1. Select a question from `workspace/03_challenges.sql`.
2. Write and execute the query against the PostgreSQL database.
3. Verify the result against the question requirements.
4. Test relevant edge cases.
5. Compare the implementation with `solutions/04_solutions.sql`.

The solutions are reference implementations; alternative queries may also satisfy the requirements.