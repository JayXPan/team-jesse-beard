import fastapi
import mysql.connector
import bcrypt
import secrets
import hashlib
import html
import os
from util.db_manager import DatabaseManager
from fastapi import FastAPI, Depends, HTTPException, Request, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mysql.connector.pooling import MySQLConnectionPool
from typing import Optional

CHUNK_SIZE = 2048
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
app = FastAPI()
db_manager = DatabaseManager()

app.mount("/static", StaticFiles(directory="public"), name="static")
templates = Jinja2Templates(directory="view")

# Set up a connection pool
dbconfig = {
    "host": "db",
    "user": "root",
    "password": "my-secret-pw",
    "database": "database",
}
pool = MySQLConnectionPool(pool_name="mypool", pool_size=10, **dbconfig)

def get_db():
    connection = pool.get_connection()
    try:
        yield connection
    finally:
        connection.close()

def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

@app.middleware("http")
async def add_custom_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
def read_root(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    token = request.cookies.get('token')
    username = db_manager.get_username_from_token(token, db)

    return templates.TemplateResponse("index.html", {"request": request, "username": username})


@app.post("/register/")
async def register(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    form_data = await request.form()
    username = html.escape(form_data.get("username"))
    password = form_data.get("password")
    
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    db_manager.register_user(username, hashed_password, db)

    return {"status": "Successfully registered"}


@app.post("/login/")
async def login(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    form_data = await request.form()
    username = html.escape(form_data.get("username"))
    password = form_data.get("password")

    try:
        user = db_manager.get_user_by_username(username, db)

        if not user or not bcrypt.checkpw(password.encode(), user[1].encode()):
            raise HTTPException(status_code=401, detail="Incorrect username or password")

        token = secrets.token_hex(80)
        hashed_token = hash_token(token)
        db_manager.update_user_token(hashed_token, username, db)

        response = JSONResponse(content={"status": "Login successful", "username": username})
        response.set_cookie(key="token", value=token, httponly=True, max_age=3600)
        return response
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
Endpoint to handle the creation of new posts.
It checks if the user is authenticated by verifying their token.
"""
@app.post("/make-post/")
async def make_post(
    request: Request,
    db: mysql.connector.MySQLConnection = Depends(get_db),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    uploaded_image: Optional[UploadFile] = File(None),
    starting_price: Optional[float] = Form(None),
    duration: Optional[int] = Form(None)
):

    if not title or not description or not uploaded_image.filename or not starting_price or not duration:
        return JSONResponse(status_code=400, content={"error": "All fields are required."})

    # Check if the token is present
    token = request.cookies.get("token")
    if token is None:
        return JSONResponse(status_code=403, content={"error": "Login required to make a post."})

    # Hash the token for database verification
    hashed_token = hash_token(token)

    try:
        result = db_manager.get_user_from_token(hashed_token, db)

        # If no matching user is found, return an error
        if not result:
            return JSONResponse(status_code=403, content={"error": "Please register and login with your account to make a post."})
        
        username = result[0]
        user_id = result[1]
        if not os.path.exists("public/images"):
            os.makedirs("public/images")

        file_extension = os.path.splitext(uploaded_image.filename)[1].lower()
        if file_extension not in ALLOWED_IMAGE_EXTENSIONS:
            return JSONResponse(status_code=400, content={"error": "Invalid image file format."})
        # Generate a unique filename
        unique_filename = f"item_{user_id}_image{file_extension}"
        image_path = os.path.join("public/images", unique_filename)
        with open(image_path, "wb") as buffer:
            while True:
                chunk = await uploaded_image.read(CHUNK_SIZE)
                if not chunk:
                    break
                buffer.write(chunk)
        db_manager.insert_post(username, title, description, unique_filename, starting_price, duration, db)

        # Respond with the post details
        response = JSONResponse(
            {"username": html.escape(username),
             "title": html.escape(title),
             "description": html.escape(description),
             "image": html.escape(image_path),
             "starting_price": starting_price,
             "duration": duration})

        return response
    
    except HTTPException as he:
        raise he

"""
Endpoint to retrieve all the posts.
"""
@app.get("/get-posts/")
async def get_posts(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    token = request.cookies.get("token")
    posts = db_manager.get_all_posts(token, db)

    # Return a list of post dictionaries with likes count
    return {
        "posts": [
            {
                "id": post[0], 
                "username": post[1], 
                "title": post[2], 
                "description": post[3],
                "image": post[4],
                "starting_price": post[5],
                "duration": post[6],
                "likes": post[7],
                "liked": post[8] > 0
            }
            for post in posts
        ]
    }

"""
Handles the liking and unliking of a post.
"""
@app.post("/toggle-like/{post_id}")
async def toggle_like(post_id: int, request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    token = request.cookies.get("token")
    if not token:
        return JSONResponse(status_code=403, content={"error": "Login required to like a post."})

    hashed_token = hash_token(token)
    return db_manager.toggle_post_like(post_id, hashed_token, db)


