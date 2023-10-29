import datetime
import pytz
import mysql.connector
import hashlib
from fastapi import HTTPException
from fastapi.responses import JSONResponse

MAX_BID_AMOUNT = 99999999.99
class DatabaseManager:

    def hash_token(self, token):
        return hashlib.sha256(token.encode()).hexdigest()
    
    def get_user_from_token(self, hashed_token, db):
        cursor = db.cursor()
        try:
            cursor.execute(
                "SELECT username, id FROM users WHERE hashed_token = %s",
                (hashed_token,)
            )
            result = cursor.fetchone()
            return result
        finally:
            cursor.close()
    
    def get_username_from_token(self, token, db):
        if not token:
            return 'Guest'

        hashed_token = self.hash_token(token)

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
            return 'Guest'
        finally:
            cursor.close()

    def get_user_by_username(self, username, db):
        try:
            cursor = db.cursor()
            cursor.execute(
                "SELECT username, hashed_password FROM users WHERE username = %s", 
                (username,)
            )
            user = cursor.fetchone()
            return user
        finally:
            cursor.close()
    
    def update_user_token(self, hashed_token, username, db):
        try:
            cursor = db.cursor()
            cursor.execute(
                "UPDATE users SET hashed_token = %s WHERE username = %s", 
                (hashed_token, username)
            )
            db.commit()
        finally:
            cursor.close()

    def register_user(self, username, hashed_password, db):
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

    def insert_post(self, username, title, description, unique_filename, starting_price, current_bid, end_time, duration, db):
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO posts(username, title, description, image, starting_price, current_bid, end_time, duration) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (username, title, description, unique_filename, starting_price, current_bid, end_time, duration)
            )
            db.commit()
        except mysql.connector.Error as err:
            raise HTTPException(status_code=500, detail=str(err))
        finally:
            cursor.close()

    def get_all_posts(self, token, db):
        cursor = db.cursor()

        try:
            # Check if there are any posts
            cursor.execute("SELECT COUNT(*) FROM posts")
            post_count = cursor.fetchone()[0]

            # If there are no posts, return an empty list immediately
            if post_count == 0:
                return []
            
            if token:
                hashed_token = self.hash_token(token)
                cursor.execute("SELECT id FROM users WHERE hashed_token = %s", (hashed_token,))
                user = cursor.fetchone()
                user_id = user[0]
                
                # Fetch post details for authenticated user
                query = """
                SELECT 
                    p.id, p.username, p.title, p.description, p.image, p.starting_price, p.current_bid, p.current_bidder_id, p.end_time, p.duration,
                    COUNT(pl.id) AS likes_count,
                    SUM(CASE WHEN pl.user_id = %s THEN 1 ELSE 0 END) AS liked_by_user
                FROM 
                    posts p
                LEFT JOIN 
                    post_likes pl ON p.id = pl.post_id
                GROUP BY 
                    p.id, p.username, p.title, p.description, p.image, p.starting_price, p.current_bid, p.current_bidder_id, p.end_time, p.duration
                """

                cursor.execute(query, (user_id,))
            else:
                # Fetch post details for guests
                query = """
                SELECT 
                    p.id, p.username, p.title, p.description, p.image, p.starting_price, p.current_bid, p.current_bidder_id, p.end_time, p.duration,
                    COUNT(pl.id) AS likes_count,
                    0 AS liked_by_user
                FROM 
                    posts p
                LEFT JOIN 
                    post_likes pl ON p.id = pl.post_id
                GROUP BY 
                    p.id, p.username, p.title, p.description, p.image, p.starting_price, p.current_bid, p.current_bidder_id, p.end_time, p.duration
                """

                cursor.execute(query)
            posts = cursor.fetchall()
            return posts
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()


    def toggle_post_like(self, post_id, hashed_token, db):
        with db.cursor() as cursor:
            # Fetch the user id associated with this token
            cursor.execute("SELECT id FROM users WHERE hashed_token = %s", (hashed_token,))
            user = cursor.fetchone()
            if not user:
                return JSONResponse(status_code=403, content={"error": "Invalid user."})

            user_id = user[0]

            # Check if the user has already liked the post
            cursor.execute("SELECT id FROM post_likes WHERE post_id = %s AND user_id = %s", (post_id, user_id))
            result = cursor.fetchone()

            if result:
                # User has liked the post, so remove the like
                cursor.execute("DELETE FROM post_likes WHERE id = %s", (result[0],))
                likedByUser = False
            else:
                # User hasn't liked the post, so add the like
                cursor.execute("INSERT INTO post_likes (post_id, user_id) VALUES (%s, %s)", (post_id, user_id))
                likedByUser = True

            db.commit()

            # Fetch the updated like count
            cursor.execute("SELECT COUNT(id) FROM post_likes WHERE post_id = %s", (post_id,))
            likes = cursor.fetchone()

        return {"likes": likes[0] if likes else 0, "likedByUser": likedByUser}


    def update_bid_if_higher(self, post_id, amount, token, db):
        cursor = db.cursor()
        try:
            hashed_token = self.hash_token(token)

            # Check if the user is the creator of the post
            cursor.execute("SELECT username FROM posts WHERE id = %s", (post_id,))
            creator = cursor.fetchone()
            if creator and creator[0] == self.get_username_from_token(token, db):
                return "Creator cannot bid on their own auction"

            # Check the current highest bid
            if amount > MAX_BID_AMOUNT:
                return "The bid amount exceeds the maximum allowed value."
            cursor.execute("SELECT current_bid, end_time FROM posts WHERE id = %s", (post_id,))
            current_bid, end_time = cursor.fetchone()

            eastern = pytz.timezone('US/Eastern')
            current_time_in_eastern = datetime.datetime.now(eastern)
            if end_time.tzinfo is None:
                end_time = eastern.localize(end_time)
            if current_time_in_eastern >= end_time:
                return "Auction has ended"

            if amount <= current_bid:
                return "Bid amount must be greater than the current highest bid"

            # Fetch user id from token
            cursor.execute("SELECT id FROM users WHERE hashed_token = %s", (hashed_token,))
            user_id = cursor.fetchone()[0]

            # Insert bid into bids table
            cursor.execute("INSERT INTO bids(post_id, user_id, amount) VALUES (%s, %s, %s)",
                        (post_id, user_id, amount))

            # Update current bid and bidder in posts table
            cursor.execute("UPDATE posts SET current_bid = %s, current_bidder_id = %s WHERE id = %s",
                        (amount, user_id, post_id))
            
            db.commit()
            return {"status": "success", "message": "Bid placed successfully", "bid_value": amount, "auction_id": post_id}

        except Exception as e:
            return str(e)
        finally:
            cursor.close()