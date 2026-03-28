from __future__ import annotations


def _safe_execute(cursor, statement: str) -> None:
    try:
        cursor.execute(statement)
    except Exception as exc:
        message = str(exc)
        if "ORA-00955" not in message:
            raise


def init_schema(conn) -> None:
    cursor = conn.cursor()
    _safe_execute(
        cursor,
        """
        CREATE TABLE vision_runs (
            run_id        VARCHAR2(64) PRIMARY KEY,
            image_path    VARCHAR2(1024),
            elapsed_seconds NUMBER,
            features_json CLOB CHECK (features_json IS JSON),
            report_json   CLOB CHECK (report_json IS JSON),
            created_at    TIMESTAMP DEFAULT SYSTIMESTAMP
        )
        """,
    )
    _safe_execute(
        cursor,
        """
        CREATE TABLE vision_vectors (
            vector_id      VARCHAR2(64) PRIMARY KEY,
            run_id         VARCHAR2(64) NOT NULL REFERENCES vision_runs(run_id) ON DELETE CASCADE,
            feature_kind   VARCHAR2(64) NOT NULL,
            chunk_text     CLOB,
            embedding      VECTOR(16, FLOAT32) NOT NULL,
            created_at     TIMESTAMP DEFAULT SYSTIMESTAMP
        )
        """,
    )
    conn.commit()


def reset_schema(conn) -> None:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vision_vectors")
    cursor.execute("DELETE FROM vision_runs")
    conn.commit()
