
import os
import time

import psycopg2
from psycopg2.extras import RealDictCursor

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="StudentHub API")


# Database connection
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )


# Initialize database
@app.on_event("startup")
def startup():

    for attempt in range(20):
        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL
                )
            """)

            cur.execute("""
                ALTER TABLE items
                ADD COLUMN IF NOT EXISTS course VARCHAR(100)
                NOT NULL DEFAULT 'General'
            """)

            conn.commit()
            cur.close()
            conn.close()

            print("StudentHub database connected!")
            return

        except psycopg2.OperationalError:
            if attempt == 19:
                raise

            time.sleep(2)


# Student request model
class Student(BaseModel):
    name: str
    course: str


# GET: Fetch all students
@app.get("/items")
def get_students():

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM items ORDER BY id DESC")

    students = cur.fetchall()

    cur.close()
    conn.close()

    return students


# POST: Add student
@app.post("/items")
def add_student(student: Student):

    name = student.name.strip()
    course = student.course.strip()

    if not name or not course:
        raise HTTPException(status_code=400, detail="All fields are required")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        INSERT INTO items (name, course)
        VALUES (%s, %s)
        RETURNING *
    """, (name, course))

    new_student = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return new_student


# PUT: Update student
@app.put("/items/{student_id}")
def update_student(student_id: int, student: Student):

    name = student.name.strip()
    course = student.course.strip()

    if not name or not course:
        raise HTTPException(status_code=400, detail="All fields are required")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        UPDATE items
        SET name = %s, course = %s
        WHERE id = %s
        RETURNING *
    """, (name, course, student_id))

    updated_student = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    if updated_student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    return updated_student


# DELETE: Remove student
@app.delete("/items/{student_id}")
def delete_student(student_id: int):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM items
        WHERE id = %s
        RETURNING id
    """, (student_id,))

    deleted_student = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    if deleted_student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    return {"message": "Student deleted successfully"}
