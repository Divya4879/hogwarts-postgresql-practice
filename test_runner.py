
"""
Pytest runner for the Hogwarts PostgreSQL SQL Sandbox.

Run the complete suite:
    python test_runner.py

Run one exact question:
    python test_runner.py --question 1
    python test_runner.py --question 29
    python test_runner.py --question 30

Database configuration can be overridden using:
    DB_NAME
    DB_USER
    DB_PASSWORD
    DB_HOST
    DB_PORT

The current solutions/04_solutions.sql contains three legacy exploratory
question markers (Q11, Q24, Q25) before its canonical Q1-Q30 section.
The loader recognizes and excludes those markers.
"""

import argparse
import os
import re
from collections import Counter
from pprint import pformat

import psycopg2
import pytest


# ============================================================================
# CONFIGURATION
# ============================================================================

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

SOLUTION_FILE = os.path.join(
    ROOT_DIR, "solutions", "04_solutions.sql"
)

WORKSPACE_FILE = os.path.join(
    ROOT_DIR, "workspace", "03_challenges.sql"
)

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "hogwarts"),
    "user": os.getenv("DB_USER", "wizard"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": 5433,
}

QUESTION_IDS = tuple(range(1, 31))

COMPARABLE_IDS = tuple(range(1, 29))

LEGACY_SOLUTION_PREFIX_IDS = {11, 24, 25}

MARKER_PATTERN = re.compile(
    r"(?m)^\s*--\s*QUESTION\s+(\d+)\s*:\s*.*$",
    re.IGNORECASE,
)

Q29_COLUMNS = (
    "exam_date",
    "total_exams",
    "failed_exams",
    "failure_rate_percent",
)


# ============================================================================
# SQL COMMENT REMOVAL
# ============================================================================

def _is_escape_string_start(sql, index):
    """Check whether a quote begins a PostgreSQL E'...' string."""

    previous = sql[index - 1] if index > 0 else ""
    before_previous = sql[index - 2] if index > 1 else ""

    return (
        previous in ("e", "E")
        and (
            not before_previous
            or not (
                before_previous.isalnum()
                or before_previous in ("_", "$")
            )
        )
    )


def remove_comments(sql):
    """
    Remove SQL line and block comments.

    Preserve:
    - Single-quoted strings
    - Escaped strings
    - Double-quoted identifiers
    - Dollar-quoted strings
    - Newlines

    Nested PostgreSQL block comments are supported.
    """

    output = []

    i = 0
    length = len(sql)

    state = "normal"
    block_depth = 0
    dollar_delimiter = None
    escape_string = False

    while i < length:

        char = sql[i]
        next_char = sql[i + 1] if i + 1 < length else ""

        # ------------------------------------------------------------
        # Single-quoted strings
        # ------------------------------------------------------------

        if state == "single":

            output.append(char)

            if escape_string and char == "\\" and i + 1 < length:
                output.append(sql[i + 1])
                i += 2
                continue

            if char == "'":

                if next_char == "'":
                    output.append(next_char)
                    i += 2
                    continue

                state = "normal"
                escape_string = False

            i += 1
            continue

        # ------------------------------------------------------------
        # Double-quoted identifiers
        # ------------------------------------------------------------

        if state == "double":

            output.append(char)

            if char == '"':

                if next_char == '"':
                    output.append(next_char)
                    i += 2
                    continue

                state = "normal"

            i += 1
            continue

        # ------------------------------------------------------------
        # Dollar-quoted strings
        # ------------------------------------------------------------

        if state == "dollar":

            if sql.startswith(dollar_delimiter, i):

                output.append(dollar_delimiter)
                i += len(dollar_delimiter)

                state = "normal"
                dollar_delimiter = None

            else:

                output.append(char)
                i += 1

            continue

        # ------------------------------------------------------------
        # Line comments
        # ------------------------------------------------------------

        if state == "line":

            if char == "\n":

                output.append("\n")
                state = "normal"

            else:

                output.append(" ")

            i += 1
            continue

        # ------------------------------------------------------------
        # Block comments
        # ------------------------------------------------------------

        if state == "block":

            if char == "/" and next_char == "*":

                output.extend((" ", " "))
                block_depth += 1
                i += 2
                continue

            if char == "*" and next_char == "/":

                output.extend((" ", " "))
                block_depth -= 1
                i += 2

                if block_depth == 0:
                    state = "normal"

                continue

            output.append("\n" if char == "\n" else " ")
            i += 1
            continue

        # ------------------------------------------------------------
        # Normal SQL state
        # ------------------------------------------------------------

        if char == "'":

            escape_string = _is_escape_string_start(sql, i)

            output.append(char)
            state = "single"

            i += 1
            continue

        if char == '"':

            output.append(char)
            state = "double"

            i += 1
            continue

        if char == "-" and next_char == "-":

            output.extend((" ", " "))
            state = "line"

            i += 2
            continue

        if char == "/" and next_char == "*":

            output.extend((" ", " "))
            state = "block"
            block_depth = 1

            i += 2
            continue

        if char == "$":

            match = re.match(
                r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$",
                sql[i:],
            )

            if match:

                dollar_delimiter = match.group(0)

                output.append(dollar_delimiter)

                state = "dollar"
                i += len(dollar_delimiter)

                continue

        output.append(char)
        i += 1

    if state in {"single", "double", "dollar", "block"}:

        raise ValueError(
            f"Unterminated SQL construct: {state}"
        )

    return "".join(output).strip()


# ============================================================================
# SQL STATEMENT SPLITTING
# ============================================================================

def split_sql_statements(sql):
    """
    Split SQL statements at semicolons outside quoted text.

    Supports:
    - Single-quoted strings
    - Escaped strings
    - Double-quoted identifiers
    - Dollar-quoted strings
    - SQL comments
    """

    sql = remove_comments(sql)

    statements = []
    current = []

    i = 0
    length = len(sql)

    state = "normal"
    dollar_delimiter = None
    escape_string = False

    while i < length:

        char = sql[i]
        next_char = sql[i + 1] if i + 1 < length else ""

        if state == "single":

            current.append(char)

            if escape_string and char == "\\" and i + 1 < length:

                current.append(sql[i + 1])
                i += 2
                continue

            if char == "'":

                if next_char == "'":

                    current.append(next_char)
                    i += 2
                    continue

                state = "normal"
                escape_string = False

            i += 1
            continue

        if state == "double":

            current.append(char)

            if char == '"':

                if next_char == '"':

                    current.append(next_char)
                    i += 2
                    continue

                state = "normal"

            i += 1
            continue

        if state == "dollar":

            if sql.startswith(dollar_delimiter, i):

                current.append(dollar_delimiter)

                i += len(dollar_delimiter)

                state = "normal"
                dollar_delimiter = None

            else:

                current.append(char)
                i += 1

            continue

        if char == "'":

            escape_string = _is_escape_string_start(sql, i)

            current.append(char)
            state = "single"

            i += 1
            continue

        if char == '"':

            current.append(char)
            state = "double"

            i += 1
            continue

        if char == "$":

            match = re.match(
                r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$",
                sql[i:],
            )

            if match:

                dollar_delimiter = match.group(0)

                current.append(dollar_delimiter)

                state = "dollar"
                i += len(dollar_delimiter)

                continue

        if char == ";":

            statement = "".join(current).strip()

            if statement:
                statements.append(statement)

            current = []

            i += 1
            continue

        current.append(char)
        i += 1

    if state in {"single", "double", "dollar"}:

        raise ValueError(
            f"Unterminated SQL construct while splitting: {state}"
        )

    remaining = "".join(current).strip()

    if remaining:
        statements.append(remaining)

    return statements


# ============================================================================
# QUESTION MARKER EXTRACTION
# ============================================================================

def _read_sql_file(filepath):
    """Read a SQL file and locate its question markers."""

    if not os.path.isfile(filepath):

        raise FileNotFoundError(
            f"SQL file not found: {filepath}"
        )

    with open(filepath, "r", encoding="utf-8") as file:

        content = file.read()

    markers = list(
        MARKER_PATTERN.finditer(content)
    )

    return content, markers


def _canonical_markers(filepath):
    """
    Locate the single canonical Q1-Q30 section.

    The current reference file contains older exploratory Q11, Q24 and Q25
    blocks before the canonical section.

    Those known legacy markers are excluded.

    The function also permits those legacy markers to be removed later.
    Unexpected duplicate or misplaced markers raise an error.
    """

    _, markers = _read_sql_file(filepath)

    marker_ids = [
        int(marker.group(1))
        for marker in markers
    ]

    expected_ids = list(QUESTION_IDS)
    block_length = len(expected_ids)

    possible_starts = [

        index

        for index in range(
            len(marker_ids) - block_length + 1
        )

        if marker_ids[
            index:index + block_length
        ] == expected_ids
    ]

    if len(possible_starts) != 1:

        raise ValueError(
            f"{filepath}: expected exactly one complete ordered "
            f"Q1-Q30 section; found {len(possible_starts)}."
        )

    start = possible_starts[0]
    end = start + block_length

    prefix_ids = marker_ids[:start]
    suffix_ids = marker_ids[end:]

    if suffix_ids:

        raise ValueError(
            f"{filepath}: unexpected question markers after "
            f"the canonical section: {suffix_ids}"
        )

    filename = os.path.basename(
        os.fspath(filepath)
    )

    if filename == "04_solutions.sql":

        unexpected = [
            question_id
            for question_id in prefix_ids
            if question_id not in LEGACY_SOLUTION_PREFIX_IDS
        ]

        if unexpected:

            raise ValueError(
                f"{filepath}: unexpected markers before the "
                f"canonical section: {unexpected}"
            )

        if len(prefix_ids) != len(set(prefix_ids)):

            raise ValueError(
                f"{filepath}: duplicate legacy markers detected."
            )

    elif prefix_ids:

        raise ValueError(
            f"{filepath}: unexpected markers before Q1: "
            f"{prefix_ids}"
        )

    return markers[start:end]


def extract_question_markers(filepath):
    """Return canonical question numbers."""

    return [
        int(marker.group(1))
        for marker in _canonical_markers(filepath)
    ]


def load_numbered_queries(filepath):
    """
    Extract the SQL belonging to each canonical question.

    The SQL between one marker and the next belongs to that question.
    """

    content, _ = _read_sql_file(filepath)

    markers = _canonical_markers(filepath)

    queries = {}

    for index, marker in enumerate(markers):

        question_id = int(marker.group(1))

        start = marker.end()

        if index + 1 < len(markers):

            end = markers[index + 1].start()

        else:

            end = len(content)

        query_sql = remove_comments(
            content[start:end]
        )

        queries[question_id] = query_sql

    return queries


# ============================================================================
# DATABASE FIXTURE
# ============================================================================

@pytest.fixture(scope="module")
def db_cursor():
    """
    Create one PostgreSQL connection for the test module.

    Individual queries are isolated using savepoints.
    The complete test transaction is rolled back at teardown.
    """

    connection = psycopg2.connect(**DB_CONFIG)

    connection.autocommit = False

    cursor = connection.cursor()

    try:

        yield cursor

    finally:

        connection.rollback()

        cursor.close()

        connection.close()


# ============================================================================
# RESULT NORMALIZATION
# ============================================================================

def normalize_value(value):
    """
    Convert nested values into comparable, hashable structures.

    This supports PostgreSQL arrays and JSON/JSONB values.
    """

    if isinstance(value, dict):

        return tuple(
            sorted(
                (
                    key,
                    normalize_value(item),
                )
                for key, item in value.items()
            )
        )

    if isinstance(value, (list, tuple)):

        return tuple(
            normalize_value(item)
            for item in value
        )

    return value


def execute_and_capture(cursor, sql, ordered=False):
    """
    Execute SQL and capture its column names and rows.

    Default:
        Counter comparison preserves duplicates but ignores row ordering.

    ordered=True:
        Preserve the original row order.
    """

    cursor.execute(sql)

    if cursor.description is None:

        return None, None

    columns = tuple(
        description[0]
        for description in cursor.description
    )

    rows = [
        normalize_value(row)
        for row in cursor.fetchall()
    ]

    if ordered:

        return columns, rows

    return columns, Counter(rows)


def execute_in_savepoint(
    cursor,
    sql,
    savepoint_name,
    ordered=False,
):
    """
    Execute one query inside an isolated savepoint.

    Even if a query raises an exception, the transaction is restored
    before the exception is passed back to the test.
    """

    cursor.execute(
        f"SAVEPOINT {savepoint_name}"
    )

    try:

        return execute_and_capture(
            cursor,
            sql,
            ordered=ordered,
        )

    finally:

        cursor.execute(
            f"ROLLBACK TO SAVEPOINT {savepoint_name}"
        )

        cursor.execute(
            f"RELEASE SAVEPOINT {savepoint_name}"
        )


def format_rows(rows):
    """Format query results for readable pytest failure messages."""

    if rows is None:

        return "<no result set>"

    if not rows:

        return "<no rows>"

    if isinstance(rows, Counter):

        rows = [
            {
                "row": row,
                "count": count,
            }

            for row, count in sorted(
                rows.items(),
                key=lambda item: repr(item[0]),
            )
        ]

    return pformat(
        rows,
        width=100,
        sort_dicts=False,
    )


# ============================================================================
# QUESTION COMPARISON
# ============================================================================

def validate_q1_alphabetical_order(columns, rows):
    """
    Independently verify Q1's alphabetical last-name ordering.

    The reference orders only by last_name. Therefore, students sharing
    a last name do not have a specified relative order.

    This check validates the required last-name ordering without
    unnecessarily enforcing the reference's tie ordering.
    """

    if "student_name" not in columns:

        pytest.fail(
            "Q1: expected a student_name output column."
        )

    name_index = columns.index("student_name")

    last_names = []

    for row in rows:

        student_name = row[name_index]

        if student_name is None:

            pytest.fail(
                "Q1: student_name cannot be NULL."
            )

        last_name = str(student_name).rsplit(
            " ", 1
        )[-1].casefold()

        last_names.append(last_name)

    if last_names != sorted(last_names):

        pytest.fail(
            "Q1: students are not ordered alphabetically "
            "by last name.\n"
            f"Returned last names:\n{last_names}"
        )


def compare_queries(
    cursor,
    user_sql,
    reference_sql,
    question_id,
):
    """
    Compare user and reference queries.

    Q1:
        Compare contents without relying on tie ordering.
        Independently validate alphabetical last-name ordering.

    Q2-Q28:
        Compare duplicate-aware unordered results.
    """

    try:

        user_columns, user_rows = execute_in_savepoint(
            cursor,
            user_sql,
            f"user_q{question_id}",
            ordered=(question_id == 1),
        )

    except Exception as error:

        pytest.fail(
            f"Q{question_id}: your query raised an error:\n{error}"
        )

    try:

        reference_columns, reference_rows = execute_in_savepoint(
            cursor,
            reference_sql,
            f"reference_q{question_id}",
        )

    except Exception as error:

        pytest.fail(
            f"Q{question_id}: reference query raised an error:\n{error}"
        )

    if user_columns is None or reference_columns is None:

        pytest.fail(
            f"Q{question_id}: both queries must return result sets.\n"
            f"Your columns: {user_columns}\n"
            f"Reference columns: {reference_columns}"
        )

    if user_columns != reference_columns:

        pytest.fail(
            f"Q{question_id}: column names or column order differ.\n"
            f"Reference: {reference_columns}\n"
            f"Your query: {user_columns}\n\n"
            f"Reference rows:\n{format_rows(reference_rows)}\n\n"
            f"Your rows:\n{format_rows(user_rows)}"
        )

    if question_id == 1:

        user_counter = Counter(user_rows)

        if user_counter != reference_rows:

            pytest.fail(
                "Q1: returned student records differ from "
                "the reference.\n"
                f"Reference:\n{format_rows(reference_rows)}\n\n"
                f"Your rows:\n{format_rows(user_rows)}"
            )

        validate_q1_alphabetical_order(
            user_columns,
            user_rows,
        )

    elif user_rows != reference_rows:

        pytest.fail(
            f"Q{question_id}: query results differ.\n"
            f"Reference:\n{format_rows(reference_rows)}\n\n"
            f"Your rows:\n{format_rows(user_rows)}"
        )


# ============================================================================
# INDEPENDENT VALIDATION: Q11, Q24 AND Q25
# ============================================================================

def independent_query(question_id):
    """
    Return independently written expected-result SQL.

    These queries calculate the expected results directly from the
    underlying exams table rather than trusting the reference solution.
    """

    if question_id == 11:

        return """
            SELECT

                COUNT(*) FILTER (
                    WHERE grade_result = 'troll'
                ) AS total_troll_grades,

                COUNT(*) AS total_exams,

                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE grade_result = 'troll'
                    ) / NULLIF(COUNT(*), 0),
                    2
                ) AS troll_percentage

            FROM exams
        """

    if question_id == 24:

        return """
            WITH date_bounds AS (

                SELECT
                    MIN(exam_date)::date AS first_date,
                    MAX(exam_date)::date AS last_date

                FROM exams
            ),

            calendar AS (

                SELECT
                    generate_series(
                        first_date,
                        last_date,
                        INTERVAL '1 day'
                    )::date AS exam_date

                FROM date_bounds
            )

            SELECT
                calendar.exam_date

            FROM calendar

            LEFT JOIN exams
                ON exams.exam_date = calendar.exam_date

            GROUP BY calendar.exam_date

            HAVING COUNT(exams.exam_id) = 0

            ORDER BY calendar.exam_date
        """

    if question_id == 25:

        return """
            WITH date_bounds AS (

                SELECT
                    MIN(exam_date)::date AS first_date,
                    MAX(exam_date)::date AS last_date

                FROM exams
            ),

            calendar AS (

                SELECT
                    generate_series(
                        first_date,
                        last_date,
                        INTERVAL '1 day'
                    )::date AS exam_date

                FROM date_bounds
            ),

            daily_counts AS (

                SELECT
                    calendar.exam_date,

                    COUNT(exams.exam_id) FILTER (
                        WHERE exams.grade_result IN ('o', 'o++')
                    ) AS daily_count

                FROM calendar

                LEFT JOIN exams
                    ON exams.exam_date = calendar.exam_date

                GROUP BY calendar.exam_date
            )

            SELECT
                exam_date,
                daily_count,

                ROUND(
                    AVG(daily_count) OVER (
                        ORDER BY exam_date
                        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                    ),
                    2
                ) AS rolling_3day_avg

            FROM daily_counts

            ORDER BY exam_date
        """

    raise ValueError(
        f"No independent query defined for Q{question_id}."
    )


def validate_independently(
    cursor,
    question_id,
    user_sql,
    reference_sql,
):
    """
    Validate both the user's answer and reference answer independently.

    This is particularly important for Q11, Q24 and Q25 because an
    incorrect reference query must not be treated as ground truth.
    """

    expected_columns, expected_rows = execute_in_savepoint(
        cursor,
        independent_query(question_id),
        f"expected_q{question_id}",
    )

    for label, sql in (
        ("your answer", user_sql),
        ("reference answer", reference_sql),
    ):

        try:

            actual_columns, actual_rows = execute_in_savepoint(
                cursor,
                sql,
                f"validate_{label.replace(' ', '_')}_q{question_id}",
            )

        except Exception as error:

            pytest.fail(
                f"Q{question_id}: {label} failed independent "
                f"validation:\n{error}"
            )

        if (
            actual_columns != expected_columns
            or actual_rows != expected_rows
        ):

            pytest.fail(
                f"Q{question_id}: {label} does not match the "
                f"independently calculated expected result.\n\n"
                f"Expected columns:\n{expected_columns}\n\n"
                f"Actual columns:\n{actual_columns}\n\n"
                f"Expected rows:\n{format_rows(expected_rows)}\n\n"
                f"Actual rows:\n{format_rows(actual_rows)}"
            )


# ============================================================================
# QUESTION 29: MATERIALIZED VIEW
# ============================================================================

def capture_materialized_view(
    cursor,
    sql,
    label,
):
    """
    Execute a materialized-view definition in an isolated savepoint.

    The view is rolled back after its results have been captured.
    """

    savepoint_name = f"q29_{label}"

    cursor.execute(
        f"SAVEPOINT {savepoint_name}"
    )

    try:

        cursor.execute(
            "DROP MATERIALIZED VIEW IF EXISTS daily_exam_metrics"
        )

        statements = split_sql_statements(sql)

        if not statements:

            raise ValueError(
                "No SQL statements found."
            )

        for statement in statements:

            cursor.execute(statement)

        cursor.execute(
            """
            SELECT
                exam_date,
                total_exams,
                failed_exams,
                failure_rate_percent

            FROM daily_exam_metrics

            ORDER BY exam_date
            """
        )

        columns = tuple(
            description[0]
            for description in cursor.description
        )

        rows = Counter(
            normalize_value(row)
            for row in cursor.fetchall()
        )

        return columns, rows

    finally:

        cursor.execute(
            f"ROLLBACK TO SAVEPOINT {savepoint_name}"
        )

        cursor.execute(
            f"RELEASE SAVEPOINT {savepoint_name}"
        )


def expected_daily_metrics(cursor):
    """Calculate Q29's expected daily metrics directly from exams."""

    sql = """
        SELECT

            exam_date,

            COUNT(*) AS total_exams,

            COUNT(*) FILTER (
                WHERE grade_result IN ('p', 'troll')
            ) AS failed_exams,

            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE grade_result IN ('p', 'troll')
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_percent

        FROM exams

        GROUP BY exam_date

        ORDER BY exam_date
    """

    return execute_in_savepoint(
        cursor,
        sql,
        "q29_expected",
    )


# ============================================================================
# QUESTION 30: EXPLAIN ANALYZE
# ============================================================================

def extract_explain_statements(sql):
    """Extract EXPLAIN statements from a question block."""

    return [

        statement

        for statement in split_sql_statements(sql)

        if re.match(
            r"^\s*EXPLAIN\b",
            statement,
            re.IGNORECASE,
        )
    ]


def remove_explain_prefix(statement):
    """
    Remove EXPLAIN ANALYZE from a statement.

    Supports:

        EXPLAIN ANALYZE SELECT ...

        EXPLAIN (ANALYZE, BUFFERS) SELECT ...
    """

    pattern = re.compile(
        r"""
        ^\s*
        EXPLAIN
        \s+
        (?:
            ANALYZE\b
            |
            \([^)]*\bANALYZE\b[^)]*\)
        )
        \s*
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    match = pattern.match(statement)

    if not match:

        raise ValueError(
            "Q30 requires EXPLAIN ANALYZE statements."
        )

    query = statement[
        match.end():
    ].strip()

    if not re.match(
        r"^(SELECT|WITH)\b",
        query,
        re.IGNORECASE,
    ):

        raise ValueError(
            "Q30 EXPLAIN ANALYZE must wrap a SELECT or WITH query."
        )

    return query


def extract_plan_metrics(plan):
    """Extract PostgreSQL execution-plan metrics."""

    patterns = {

        "execution_time_ms":
            r"Execution Time:\s*([\d.]+)\s*ms",

        "planning_time_ms":
            r"Planning Time:\s*([\d.]+)\s*ms",

        "estimated_total_cost":
            r"cost=[\d.]+\.\.([\d.]+)",

        "root_actual_time_ms":
            r"actual time=[\d.]+\.\.([\d.]+)",
    }

    matches = {

        key: re.search(
            pattern,
            plan,
            re.IGNORECASE,
        )

        for key, pattern in patterns.items()
    }

    required_metrics = (
        "execution_time_ms",
        "planning_time_ms",
        "root_actual_time_ms",
    )

    for metric in required_metrics:

        if not matches[metric]:

            raise ValueError(
                f"EXPLAIN ANALYZE output is missing {metric}."
            )

    return {

        key: (
            float(match.group(1))
            if match
            else None
        )

        for key, match in matches.items()
    }


def capture_plan(
    cursor,
    statement,
    label,
):
    """Execute EXPLAIN ANALYZE and capture its plan and query results."""

    savepoint_name = f"q30_{label}"

    cursor.execute(
        f"SAVEPOINT {savepoint_name}"
    )

    try:

        cursor.execute(statement)

        plan_rows = cursor.fetchall()

        plan = "\n".join(
            str(row[0])
            for row in plan_rows
        )

        if not plan.strip():

            raise ValueError(
                "EXPLAIN ANALYZE returned an empty plan."
            )

        metrics = extract_plan_metrics(plan)

        underlying_query = remove_explain_prefix(
            statement
        )

        columns, rows = execute_and_capture(
            cursor,
            underlying_query,
        )

        if columns is None:

            raise ValueError(
                "The underlying query returned no result set."
            )

        return {

            "plan": plan,

            "metrics": metrics,

            "columns": columns,

            "rows": rows,
        }

    finally:

        cursor.execute(
            f"ROLLBACK TO SAVEPOINT {savepoint_name}"
        )

        cursor.execute(
            f"RELEASE SAVEPOINT {savepoint_name}"
        )


def expected_q30_results(cursor):
    """
    Independently calculate the expected student GPA results.

    The mapping follows the repository's Q13/Q30 grade scale.
    """

    sql = """
        SELECT

            s.first_name || ' ' || s.last_name AS student_name,

            ROUND(
                AVG(
                    CASE
                        WHEN e.grade_result = 'o++' THEN 6.0
                        WHEN e.grade_result = 'o+' THEN 5.0
                        WHEN e.grade_result = 'o' THEN 4.0
                        WHEN e.grade_result = 'ee' THEN 3.0
                        WHEN e.grade_result = 'a' THEN 2.0
                        WHEN e.grade_result = 'p' THEN 1.0
                        ELSE 0.0
                    END
                ),
                2
            ) AS avg_gpa

        FROM students s

        JOIN exams e
            ON e.student_id = s.student_id

        GROUP BY
            s.student_id,
            s.first_name,
            s.last_name
    """

    return execute_in_savepoint(
        cursor,
        sql,
        "q30_expected",
    )


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def query_files():
    """Load canonical workspace and reference SQL blocks."""

    user_queries = load_numbered_queries(
        WORKSPACE_FILE
    )

    reference_queries = load_numbered_queries(
        SOLUTION_FILE
    )

    return user_queries, reference_queries


# ============================================================================
# TESTS: FILE STRUCTURE AND DATABASE
# ============================================================================

@pytest.mark.parametrize(
    "filepath",
    [
        WORKSPACE_FILE,
        SOLUTION_FILE,
    ],
)
def test_question_marker_integrity(filepath):
    """Verify that the canonical SQL section contains Q1-Q30 exactly once."""

    marker_ids = extract_question_markers(
        filepath
    )

    assert marker_ids == list(QUESTION_IDS), (
        f"{filepath}: expected canonical markers Q1-Q30 "
        f"in order; found {marker_ids}."
    )


def test_sandbox_connection(db_cursor):
    """Verify PostgreSQL connectivity and the presence of seeded students."""

    db_cursor.execute(
        "SELECT COUNT(*) FROM students"
    )

    student_count = db_cursor.fetchone()[0]

    assert student_count > 0, (
        "No students found in the database. "
        "Check init/01_schema.sql and init/02_seed.sql."
    )


# ============================================================================
# TESTS: QUESTIONS 1-28
# ============================================================================

@pytest.mark.parametrize(
    "question_id",
    [
        pytest.param(
            question_id,
            id=f"query_{question_id}",
        )

        for question_id in COMPARABLE_IDS
    ],
)
def test_query_match_solution(
    db_cursor,
    query_files,
    question_id,
):
    """
    Compare Q1-Q28.

    Q11, Q24 and Q25 also receive independent correctness validation.
    """

    user_queries, reference_queries = query_files

    user_sql = user_queries.get(question_id)

    reference_sql = reference_queries.get(question_id)

    if not user_sql:

        pytest.fail(
            f"Q{question_id}: no SQL answer found in "
            f"{WORKSPACE_FILE}."
        )

    if not reference_sql:

        pytest.fail(
            f"Q{question_id}: reference solution missing from "
            f"{SOLUTION_FILE}."
        )

    if question_id in {11, 24, 25}:

        validate_independently(
            db_cursor,
            question_id,
            user_sql,
            reference_sql,
        )

    compare_queries(
        db_cursor,
        user_sql,
        reference_sql,
        question_id,
    )


# ============================================================================
# TEST: QUESTION 29
# ============================================================================

def test_query_29_materialized_view_contents(
    db_cursor,
    query_files,
):
    """
    Validate the user's Q29 materialized view.

    Expected metrics are independently calculated from exams.
    """

    user_queries, reference_queries = query_files

    user_sql = user_queries.get(29)

    reference_sql = reference_queries.get(29)

    if not user_sql:

        pytest.fail(
            f"Q29: add your materialized-view SQL to "
            f"{WORKSPACE_FILE}."
        )

    if not reference_sql:

        pytest.fail(
            "Q29: reference materialized view is missing."
        )

    try:

        user_columns, user_rows = capture_materialized_view(
            db_cursor,
            user_sql,
            "user",
        )

    except Exception as error:

        pytest.fail(
            f"Q29: your materialized view failed:\n{error}"
        )

    try:

        reference_columns, reference_rows = capture_materialized_view(
            db_cursor,
            reference_sql,
            "reference",
        )

    except Exception as error:

        pytest.fail(
            f"Q29: reference materialized view failed:\n{error}"
        )

    expected_columns, expected_rows = expected_daily_metrics(
        db_cursor
    )

    assert expected_columns == Q29_COLUMNS, (
        f"Q29: independent query returned unexpected columns: "
        f"{expected_columns}"
    )

    assert user_columns == Q29_COLUMNS, (
        f"Q29: your materialized view columns are incorrect. "
        f"Expected {Q29_COLUMNS}; received {user_columns}."
    )

    assert reference_columns == Q29_COLUMNS, (
        "Q29: reference materialized view has incorrect columns."
    )

    assert user_rows == expected_rows, (
        "Q29: your materialized view does not match "
        "the independently calculated metrics.\n"
        f"Expected:\n{format_rows(expected_rows)}\n\n"
        f"Actual:\n{format_rows(user_rows)}"
    )

    assert reference_rows == expected_rows, (
        "Q29: reference materialized view does not match "
        "the independently calculated metrics."
    )


# ============================================================================
# TEST: QUESTION 30
# ============================================================================

def test_query_30_explain_analyze_plans(
    db_cursor,
    query_files,
):
    """
    Validate both Q30 approaches.

    Checks:
    - Exactly two EXPLAIN ANALYZE statements.
    - Both approaches execute successfully.
    - Both approaches return equivalent results.
    - User results match reference results.
    - Results match an independent GPA calculation.

    No assertion requires one query to be faster. Execution time and
    planner cost depend on database size, indexes, caching, statistics,
    PostgreSQL version and hardware.
    """

    user_queries, reference_queries = query_files

    user_sql = user_queries.get(30)

    reference_sql = reference_queries.get(30)

    if not user_sql:

        pytest.fail(
            f"Q30: add both EXPLAIN ANALYZE queries to "
            f"{WORKSPACE_FILE}."
        )

    if not reference_sql:

        pytest.fail(
            "Q30: reference solution is missing."
        )

    user_statements = extract_explain_statements(
        user_sql
    )

    reference_statements = extract_explain_statements(
        reference_sql
    )

    assert len(user_statements) == 2, (
        "Q30: expected exactly two user EXPLAIN ANALYZE "
        f"statements; found {len(user_statements)}."
    )

    assert len(reference_statements) == 2, (
        "Q30: expected exactly two reference EXPLAIN ANALYZE "
        f"statements; found {len(reference_statements)}."
    )

    user_plans = [

        capture_plan(
            db_cursor,
            statement,
            f"user_{index}",
        )

        for index, statement in enumerate(
            user_statements,
            start=1,
        )
    ]

    reference_plans = [

        capture_plan(
            db_cursor,
            statement,
            f"reference_{index}",
        )

        for index, statement in enumerate(
            reference_statements,
            start=1,
        )
    ]

    user_first, user_second = user_plans

    reference_first, reference_second = reference_plans

    # ------------------------------------------------------------
    # User approaches must agree.
    # ------------------------------------------------------------

    assert user_first["columns"] == user_second["columns"], (
        "Q30: your two approaches return different columns."
    )

    assert user_first["rows"] == user_second["rows"], (
        "Q30: your correlated and JOIN approaches return "
        "different results."
    )

    # ------------------------------------------------------------
    # Reference approaches must agree.
    # ------------------------------------------------------------

    assert reference_first["columns"] == reference_second["columns"], (
        "Q30: reference approaches return different columns."
    )

    assert reference_first["rows"] == reference_second["rows"], (
        "Q30: reference approaches return different results."
    )

    # ------------------------------------------------------------
    # User and reference must agree.
    # ------------------------------------------------------------

    assert user_first["columns"] == reference_first["columns"], (
        "Q30: your output columns differ from the reference."
    )

    assert user_first["rows"] == reference_first["rows"], (
        "Q30: your output rows differ from the reference."
    )

    # ------------------------------------------------------------
    # Independent GPA validation.
    # ------------------------------------------------------------

    expected_columns, expected_rows = expected_q30_results(
        db_cursor
    )

    assert user_first["columns"] == expected_columns, (
        "Q30: output columns differ from the independent GPA calculation."
    )

    assert user_first["rows"] == expected_rows, (
        "Q30: output rows differ from the independent GPA calculation."
    )

    # ------------------------------------------------------------
    # Display execution-plan metrics.
    # ------------------------------------------------------------

    print(
        "\nQ30 — EXPLAIN ANALYZE comparison"
    )

    for index, result in enumerate(
        user_plans,
        start=1,
    ):

        metrics = result["metrics"]

        print(
            f"\nYour plan {index}:"
        )

        print(
            f"  Planning time:        "
            f"{metrics['planning_time_ms']} ms"
        )

        print(
            f"  Execution time:       "
            f"{metrics['execution_time_ms']} ms"
        )

        print(
            f"  Estimated total cost: "
            f"{metrics['estimated_total_cost']}"
        )

        print(
            f"  Root actual time:     "
            f"{metrics['root_actual_time_ms']} ms"
        )


# ============================================================================
# EXACT COMMAND-LINE QUESTION SELECTION
# ============================================================================

def question_node_id(question_id):
    """
    Return the exact pytest node ID for one question.

    This avoids pytest -k substring matching.
    """

    filepath = os.path.abspath(__file__)

    if question_id in COMPARABLE_IDS:

        return (
            f"{filepath}::"
            f"test_query_match_solution[query_{question_id}]"
        )

    if question_id == 29:

        return (
            f"{filepath}::"
            "test_query_29_materialized_view_contents"
        )

    if question_id == 30:

        return (
            f"{filepath}::"
            "test_query_30_explain_analyze_plans"
        )

    raise ValueError(
        f"Unsupported question number: {question_id}"
    )


def main(argv=None):
    """Run all tests or one exact question."""

    parser = argparse.ArgumentParser(
        description="Run Hogwarts PostgreSQL SQL Sandbox tests."
    )

    parser.add_argument(
        "--question",
        type=int,
        choices=range(1, 31),
        metavar="N",
        help="run exactly one question (1-30)",
    )

    args = parser.parse_args(argv)

    pytest_args = ["-v"]

    if args.question is not None:

        pytest_args.append(
            question_node_id(args.question)
        )

        if args.question == 30:

            pytest_args.append("-s")

    else:

        pytest_args.append(
            os.path.abspath(__file__)
        )

    return int(
        pytest.main(pytest_args)
    )


if __name__ == "__main__":
    raise SystemExit(main())
