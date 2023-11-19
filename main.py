import datetime
import pytz
import json
import decimal
import uuid
import fastapi
import mysql.connector
import bcrypt
import secrets
import hashlib
import html
import aioredis
import os
import pickle
import base64
import asyncio
from util.db_manager import DatabaseManager
from util.ws_manager import WebSocketManager
from fastapi import FastAPI, Depends, HTTPException, Request, File, Form, UploadFile, status
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mysql.connector.pooling import MySQLConnectionPool
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from typing import Optional
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build

CHUNK_SIZE = 2048
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_BID_AMOUNT = 99999999.99
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

app = FastAPI()
load_dotenv()
db_manager = DatabaseManager()
ws_manager = WebSocketManager()
executors = {
    'default': ThreadPoolExecutor(20),
}
scheduler = BackgroundScheduler(executors=executors)
scheduler.start()

app.mount("/static", StaticFiles(directory="public"), name="static")
templates = Jinja2Templates(directory="view")

"""
Set up a connection pool
"""
dbconfig = {
    "host": "db",
    "user": "root",
    "password": "my-secret-pw",
    "database": "database",
}
pool = MySQLConnectionPool(pool_name="mypool", pool_size=10, **dbconfig)

"""
Create a database connection using a connection pool
"""
def get_db():
    connection = pool.get_connection()
    try:
        # Yield the connection for usage by the caller
        yield connection
    finally:
        # Ensure that the connection is closed after usage
        connection.close()

"""
Hash a given token using SHA-256
"""
def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

"""
Check for auctions that have ended but do not have winners, and update them
"""
def check_ended_auctions():
    db_gen = get_db()
    db = next(db_gen)
    try:
        # Get all ended auctions without winners
        ended_auctions = db_manager.get_ended_auctions_without_winners(db)
        for auction in ended_auctions:
            # Update the winner for each ended auction
            db_manager.update_auction_winner(auction['id'], db)
    finally:
        # This will trigger the "finally" block in get_db() to close the connection
        next(db_gen, None)

"""
Custom encoder function to handle non-JSON serializable objects
"""
def encoder(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

"""
Authenticate with Gmail and get the service object
"""
def get_gmail_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no valid credentials, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleAuthRequest())
        else:
            # Here we use the environment variable to get the path to the credentials file
            flow = InstalledAppFlow.from_client_secrets_file(
                os.getenv('GMAIL_CREDENTIALS_PATH'), SCOPES)
            creds = flow.run_local_server(port=8000)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service

"""
Function to send a verification email to the user
"""
def send_verification_email(user_email, verification_url):
    service = get_gmail_service()
    
    message = MIMEMultipart()
    message["From"] = "team.jessebeard@gmail.com"
    message["To"] = user_email
    message["Subject"] = "Verify your email with Jesse's Beard"

    text = f"""Hi there,\n\nWe're excited to have you join our community at Jesse's Beard!
    \nTo get started, we just need to confirm your email address. Please click the link below to verify your email and activate your account:
    \n{verification_url}\n\nIf you didn't sign up for an account with Jesse's Beard, no action is needed - you can safely ignore this email.\n\nThank you for joining us!\n\nBest regards,\nTeam Jesse's Beard
    """

    message.attach(MIMEText(text, 'plain'))

    # encoded message
    encoded_message = {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}

    try:
        # Call the Gmail API to send the email
        service.users().messages().send(userId="me", body=encoded_message).execute()
        print("Verification email sent successfully.")
    except Exception as e:
        print(f'An error occurred: {e}')

"""
Event handler for application startup
"""
@app.on_event("startup")
async def startup_event():
    redis_host = os.environ.get('REDIS_HOST', 'redis')
    redis_port = os.environ.get('REDIS_PORT', 6379)
    app.state.redis = await aioredis.from_url(f"redis://{redis_host}:{redis_port}", encoding="utf-8", decode_responses=True)


"""
Event handler for application shutdown
"""
@app.on_event("shutdown")
async def shutdown_event():
    # Shut down the scheduled job to avoid any lingering tasks
    scheduler.shutdown()

    # Close the Redis connection pool
    if app.state.redis:
        await app.state.redis.close()

"""
Middleware for rate limiting requests per IP address.

- Block requests from an IP address if it has made more than 50 requests within a 10 second period.
- If an IP is blocked, return a 429 "Too Many Requests" response for 30 seconds.
- Adds a X-Content-Type-Options: nosniff header to each response for security.
"""
@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    redis = request.app.state.redis
    x_forwarded_for = request.headers.get('x-forwarded-for')
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.client.host
    key = f"rate_limit:{client_ip}"
    
    try:
        is_blocked = await redis.get(f"block:{client_ip}")
        if is_blocked:
            return PlainTextResponse(
                "Too Many Requests - You must wait 30 seconds before attempting again", 
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Increment the request count for the IP
        current_count = await redis.incr(key)
        if current_count == 1:
            await redis.expire(key, 10)
        if current_count > 50:
            # Too many requests, block for 30 seconds
            await redis.setex(f"block:{client_ip}", 30, "1")
            return PlainTextResponse("Too Many Requests", status_code=status.HTTP_429_TOO_MANY_REQUESTS)
    except Exception as e:
        print(f"Error occurred: {e}")

    # Continue processing the request
    response = await call_next(request)

    # Add custom headers here before returning the response
    response.headers["X-Content-Type-Options"] = "nosniff"

    return response

"""
Endpoint to handle the root path.
"""
@app.get("/")
def read_root(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):

    # Check if the token is present
    token = request.cookies.get("token")
    username = db_manager.get_username_from_token(token, db)

    if username != 'Guest':

        # Hash the token for database verification
        hashed_token = hash_token(token)
        user = db_manager.get_user_from_token(hashed_token, db)
        username, _, email, email_verified = user
        if email_verified == "YES":
            with open('view/index.html', 'r+') as file:

                content = file.read()

                # modify html
                new_content = content.replace('Email: Not Verified <a href="#" id="verificationLink">Verify Email</a>',
                                              'Email: Verified')
                output_file_path = 'view/index_modified.html'

                with open(output_file_path, 'w') as output_file:
                    output_file.write(new_content)

                return templates.TemplateResponse("index_modified.html", {"request": request, "username": username})

    return templates.TemplateResponse("index.html", {"request": request, "username": username})

"""
Endpoint to handle the new user registration.
"""
@app.post("/register/")
async def register(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    form_data = await request.form()
    username = html.escape(form_data.get("username"))
    password = form_data.get("password")
    
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    db_manager.register_user(username, hashed_password, db)

    return {"status": "Successfully registered"}
"""
Endpoint to handle send email verification.
"""
@app.post("/verify_email/")
async def send_verification(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    data = await request.json()
    email = data.get('email')
    print("reached here: " + email)

    # gen url token
    random_bytes = secrets.token_bytes(80)
    verification_token = base64.urlsafe_b64encode(random_bytes).decode('utf-8')
    cursor = db.cursor()

    # Check if the token is present
    token = request.cookies.get("token")
    if token is None:
        return JSONResponse(status_code=403, content={"error": "Login required to make a post."})

    # Hash the token for database verification
    hashed_token = hash_token(token)

    # update user token
    try:
        cursor.execute(
            "UPDATE users SET verification_token = %s, email = %s WHERE hashed_token = %s",
            (verification_token, email, hashed_token)
        )
        db.commit()
    finally:
        cursor.close()

    verification_link = f"http://localhost:8080/verify_clicked?token={verification_token}"
    send_verification_email(email, verification_link)

"""
Endpoint to handle completing verification.
"""
@app.get("/verify_clicked")
def verify_clicked(token: str, db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE users SET email_verified = %s WHERE verification_token = %s",
            ("YES", token)
        )
        db.commit()
    finally:
        cursor.close()
    return RedirectResponse(url='http://localhost:8080/', status_code=status.HTTP_303_SEE_OTHER)

"""
Endpoint to handle the user login.
"""
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
        if not os.path.exists("public/images"):
            os.makedirs("public/images")

        file_extension = os.path.splitext(uploaded_image.filename)[1].lower()
        if file_extension not in ALLOWED_IMAGE_EXTENSIONS:
            return JSONResponse(status_code=400, content={"error": "Invalid image file format."})
        # Generate a unique filename
        unique_filename = f"item_{str(uuid.uuid4())[:10]}_image{file_extension}"
        image_path = os.path.join("public/images", unique_filename)
        with open(image_path, "wb") as buffer:
            while True:
                chunk = await uploaded_image.read(CHUNK_SIZE)
                if not chunk:
                    break
                buffer.write(chunk)
        utc_now = datetime.datetime.now(pytz.utc)
        end_time_utc = utc_now + datetime.timedelta(minutes=duration)
        # eastern = pytz.timezone('US/Eastern')
        # end_time = datetime.datetime.now(eastern) + datetime.timedelta(minutes=duration)
        current_bid = starting_price
        if starting_price > MAX_BID_AMOUNT:
            return JSONResponse(status_code=400, content={"error": "The starting price exceeds the maximum allowed value."})
        db_manager.insert_post(username, title, description, unique_filename, starting_price, current_bid, end_time_utc, duration, db)
        eastern = pytz.timezone('US/Eastern')
        end_time_eastern = end_time_utc.astimezone(eastern)

        # Respond with the post details
        response = JSONResponse(
            {"username": html.escape(username),
             "title": html.escape(title),
             "description": html.escape(description),
             "image": html.escape(image_path),
             "starting_price": starting_price,
             "current_bid": current_bid,
             "end_time": end_time_eastern.isoformat(),
             "duration": duration})

        return response
    except OverflowError:
        return JSONResponse(status_code=400, content={"error": "Duration results in an invalid end time."})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.ER_DATA_TOO_LONG:
            return JSONResponse(status_code=400, content={"error": "Input data too long."})
        elif err.errno == mysql.connector.errorcode.ER_TRUNCATED_WRONG_VALUE:
            return JSONResponse(status_code=400, content={"error": "Invalid data format."})
        else:
            raise HTTPException(status_code=500, detail=str(err))

"""
Endpoint to retrieve all the posts.
"""
@app.get("/get-posts/")
async def get_posts(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    token = request.cookies.get("token")
    utc_zone = pytz.utc
    eastern_zone = pytz.timezone('US/Eastern')
    posts_data = db_manager.get_all_posts(token, db)

    posts = []
    for post_tuple in posts_data:
        post = list(post_tuple)

        if post[8]:
            # Convert the UTC end_time from the database to Eastern Time
            eastern_end_time = utc_zone.localize(post[8]).astimezone(eastern_zone)
            post[8] = eastern_end_time.isoformat()  # Modify the end_time value

        posts.append(post)

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
                "current_bid": post[6],
                "current_bidder": post[7],
                "end_time": post[8],
                "duration": post[9],
                "winner": post[10], 
                "winning_bid": float(post[11]) if post[11] else None,
                "likes": post[12],
                "liked": post[13] > 0
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

"""
Handles websocket operations.
"""
@app.websocket("/websocket")
async def websocket_endpoint(websocket: fastapi.WebSocket, db: mysql.connector.MySQLConnection = Depends(get_db)):
    await ws_manager.connect(websocket)
    utc_zone = pytz.utc
    eastern_zone = pytz.timezone('US/Eastern')

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await ws_manager.send_personal_message("Malformed JSON", websocket)
                continue
            token = websocket.cookies.get("token")
            if message["type"] == "bid":
                if token is None:
                    await websocket.send_text(json.dumps({"error": "Login required to bid."}))
                    return

                bid_value = float(message["value"])
                auction_id = message["auction_id"]
                result = db_manager.update_bid_if_higher(auction_id, bid_value, token, db)
                if isinstance(result, str):
                    await websocket.send_text(json.dumps({"error": result}))
                    continue
          
                data = json.dumps({
                    "type": "bidUpdate",
                    "value": result["bid_value"],
                    "auction_id": result["auction_id"]
                })
                await ws_manager.broadcast(data)
            elif message["type"] == "newPostRequest":
                latest_posts = db_manager.get_all_posts(token, db)

                posts = []
                # Convert end_time of each post from UTC to Eastern Time
                for post_tuple in latest_posts:
                    post = list(post_tuple)
                    if post[8]:
                        # Convert to Eastern Time
                        eastern_end_time = utc_zone.localize(post[8]).astimezone(eastern_zone)
                        # Update the end_time to the ISO format string in Eastern Time
                        post[8] = eastern_end_time.isoformat()
                        # Update the original post with the new end_time
                    posts.append(post)

                data = json.dumps({
                    "type": "newPost",
                    "post": posts
                }, default=encoder)
                await ws_manager.broadcast(data)
            else:
                await ws_manager.send_personal_message("Invalid data format", websocket)

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        ws_manager.disconnect(websocket)


"""
Schedule the check_ended_auctions function to run at regular intervals (every 5 seconds)
"""
scheduler.add_job(check_ended_auctions, trigger='interval', seconds=5)