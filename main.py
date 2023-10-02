from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import mysql.connector
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory="public"), name="static")

@app.get("/")
def read_root():
    return FileResponse("view/index.html", media_type="text/html")

@app.get("/db")
def get_database():
    connection = mysql.connector.connect(
        host="database",
        user="root",
        password="my-secret-pw",
        database="database"
    )
    cursor = connection.cursor()
    cursor.execute("SELECT DATABASE()")
    result = cursor.fetchone()
    connection.close()

    return {"Hello": "World", "DB": result[0]}
