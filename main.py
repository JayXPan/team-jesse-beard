import fastapi
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
import bcrypt
import secrets
import hashlib
import html


app = FastAPI()

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


def get_username_from_token(token, db: mysql.connector.MySQLConnection):
    if not token:
        return 'Guest'

    hashed_token = hash_token(token)

    cursor = db.cursor()
    try:
        stmt = """
        SELECT u.username 
        FROM users u
        WHERE u.hashed_token = %s
        LIMIT 1
        """
        cursor.execute(stmt, (hashed_token,))
        result = cursor.fetchone()
        return result[0] if result else 'Guest'

    except mysql.connector.Error as err:
        print("Error:", err)
        return 'Guest'

    finally:
        cursor.close()


@app.middleware("http")
async def add_custom_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
def read_root(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    token = request.cookies.get('token')
    username = get_username_from_token(token, db)

    return templates.TemplateResponse("index.html", {"request": request, "username": username})


@app.post("/register/")
async def register(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    form_data = await request.form()
    username = html.escape(form_data.get("username"))
    password = form_data.get("password")
    
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO users(username, hashed_password) VALUES (%s, %s)", 
            (username, hashed_password.decode())
        )
        db.commit()
    except mysql.connector.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already registered")
    except:
        raise HTTPException(status_code=500, detail="Server error during registration")
    finally:
        cursor.close()

    return {"status": "Successfully registered"}


@app.post("/login/")
async def login(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    form_data = await request.form()
    username = html.escape(form_data.get("username"))
    password = form_data.get("password")

    cursor = db.cursor()
    try:
        cursor.execute(
            "SELECT username, hashed_password FROM users WHERE username = %s", 
            (username,)
        )
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(password.encode(), user[1].encode()):
            raise HTTPException(status_code=401, detail="Incorrect username or password")

        token = secrets.token_hex(80)
        hashed_token = hash_token(token)
        cursor.execute(
            "UPDATE users SET hashed_token = %s WHERE username = %s", 
            (hashed_token, username)
        )
        db.commit()

        response = JSONResponse(content={"status": "Login successful", "username": username})
        response.set_cookie(key="token", value=token, httponly=True, max_age=3600)
        return response
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error during login")
    finally:
        cursor.close()

"""
Endpoint to handle the creation of new posts.
It checks if the user is authenticated by verifying their token.
"""
@app.post("/make-post/")
async def make_post(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    # Extracting form data
    form_data = await request.form()
    title =  html.escape(form_data.get("title"))
    description =  html.escape(form_data.get("description"))

    # Check if the token is present
    token = request.cookies.get("token")
    if token is None:
        return JSONResponse(status_code=403, content={"error": "Login required to make a post."})

    # Hash the token for database verification
    hashed_token = hash_token(token)

    cursor = db.cursor()

    try:
        # Check if the hashed token belongs to a registered user
        cursor.execute(
            "SELECT username FROM users WHERE hashed_token = %s",
            (hashed_token,)
        )

        result = cursor.fetchone()

        # If no matching user is found, return an error
        if not result:
            return JSONResponse(status_code=403, content={"error": "Please register and login with your account to make a post."})
        
        username = result[0]

        # Insert the new post into the database
        cursor.execute(
            "INSERT INTO posts(username,title,description) VALUES (%s,%s,%s)",
            (username, title, description)
        )
        db.commit()

        # Respond with the post details
        response = JSONResponse(
            {"username": html.escape(username),
             "title": html.escape(title),
             "description": html.escape(description)})

        return response
    
    # Exception handlers for potential errors during the process
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error during login")
    finally:
        cursor.close()

"""
Endpoint to retrieve all the posts.
"""
@app.get("/get-posts/")
async def get_posts(db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()

    try:
        cursor.execute("SELECT username, title, description FROM posts")
        posts = cursor.fetchall()
        # Return a list of post dictionaries
        return {"posts": [{"username": post[0], "title": post[1], "description": post[2]} for post in posts]}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error while fetching posts")
    finally:
        cursor.close()
