import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi import Header, HTTPException
import sqlite3

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

def check_password(x_password: str | None):
    if not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="Server admin password not configured"
        )

    if x_password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )


app = FastAPI(title="Medi-Helper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "medi_helper.db"

class Medicine(BaseModel):
    name: str
    shelf: str
    row: str | None = None
    price: float | None = None

class MedicineUpdate(BaseModel):
    name: str
    shelf: str
    row: str
    price: float

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.on_event("startup")
def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL unique,
            shelf TEXT NOT NULL,
            row TEXT,
            price REAL
        )
    """)
    conn.commit()
    conn.close()


@app.get("/")
def home():
    return {
        "status": "running",
        "app": "Medi-Helper",
        "message": "Backend with database is live"
    }

@app.post("/add-medicine")
def add_medicine(med: Medicine, x_password: str = Header(None)):
    check_password(x_password)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM medicines WHERE LOWER(name) = LOWER(?)",
        (med.name,)
    )
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return {"message": "Medicine already exists"}

    cursor.execute(
        """
        INSERT INTO medicines (name, shelf, row, price)
        VALUES (?, ?, ?, ?)
        """,
        (med.name, med.shelf, med.row, med.price)
    )

    conn.commit()
    conn.close()

    return {
        "message": "Medicine added successfully",
        "medicine": med
    }


@app.get("/search-medicine")
def search_medicine(query: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name, shelf, row, price
        FROM medicines
        WHERE LOWER(name) LIKE LOWER(?)
        """,
        (f"%{query}%",)
    )

    medicines = cursor.fetchall()
    conn.close()

    if not medicines:
        return {"message": "No medicines found"}

    results = []
    for med in medicines:
        results.append({
            "name": med["name"],
            "shelf": med["shelf"],
            "row": med["row"],
            "price": med["price"]
        })

    return {
        "count": len(results),
        "results": results
    }

@app.put("/update-medicine")
def update_medicine(med: MedicineUpdate, x_password: str = Header(None)):
    check_password(x_password)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM medicines WHERE LOWER(name) = LOWER(?)",
        (med.name,)
    )
    existing = cursor.fetchone()

    if not existing:
        conn.close()
        return {"message": "Medicine not found"}

    cursor.execute(
        """
        UPDATE medicines
        SET shelf = ?, row = ?, price = ?
        WHERE LOWER(name) = LOWER(?)
        """,
        (med.shelf, med.row, med.price, med.name)
    )

    conn.commit()
    conn.close()

    return {"message": "Medicine updated successfully"}

@app.delete("/delete-medicine")
def delete_medicine(name: str, x_password: str = Header(None)):
    check_password(x_password)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM medicines WHERE LOWER(name) = LOWER(?)",
        (name,)
    )
    existing = cursor.fetchone()

    if not existing:
        conn.close()
        return {"message": "Medicine not found"}

    cursor.execute(
        "DELETE FROM medicines WHERE LOWER(name) = LOWER(?)",
        (name,)
    )

    conn.commit()
    conn.close()

    return {"message": "Medicine deleted successfully"}

