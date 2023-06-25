from flask import Flask, render_template, jsonify,redirect, url_for, session, request, send_file
from flask_mail import Mail, Message
from flask_session import Session
import random
import bcrypt
import sqlite3
import json
import os
import requests
import secrets
from PIL import Image
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
posts = []
DB_NAME = 'chat.db'
UPLOAD_FOLDER = 'static/uploads/files'
UPLOAD ='static/uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
app.config['UPLOAD'] = UPLOAD
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

## Configure Flask-Mail

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'otpverifycodegram@gmail.com'  # Replace with your email address
app.config['MAIL_PASSWORD'] = 'xoqzbsdtqlkdjxuk'  # Replace with your password

mail = Mail(app)

# Configure Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        email = request.form['email']

        # Check if the username and email are already taken
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
        username_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
        email_count = c.fetchone()[0]
        conn.close()

        if username_count > 0:
            error = 'Username already taken. Please choose a different username.'
            return render_template('signup.html', error=error)
        elif email_count > 0:
            error = 'Email already taken. Please choose a different email.'
            return render_template('signup.html', error=error)

        # Generate a verification code
        verification_code = random.randint(100000, 999999)

        # Send verification email
        msg = Message('Codegram - Email Verification', sender='codegramotpverification@gmail.com', recipients=[email])
        msg.body = f"Your verification code is: {verification_code}"
        mail.send(msg)

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Connect to the database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, email TEXT, verification_code INTEGER, verified INTEGER DEFAULT 0)')
        c.execute('INSERT INTO users (username, password, email, verification_code) VALUES (?, ?, ?, ?)', (username, hashed_password.decode('utf-8'), email, verification_code))
        conn.commit()
        conn.close()

        # Set the username in the session
        session['username'] = username

        return redirect(url_for('verify'))

    return render_template('signup.html')


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        verification_code = int(request.form['verification_code'])
        username = session.get('username')

        if not username:
            error = 'Invalid verification code. Please try again.'
            return render_template('verify.html', error=error)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT verification_code FROM users WHERE username = ?', (username,))
        stored_code = c.fetchone()[0]

        if verification_code == stored_code:
            # Update the 'verified' flag in the database
            # Connect to the database
            conn = sqlite3.connect('database.db')
            c = conn.cursor()

            # Check if the 'verified' column already exists
            c.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in c.fetchall()]
            if 'verified' not in columns:
                # Add the 'verified' column
                c.execute("ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0")

            c.execute('UPDATE users SET verified = 1 WHERE username = ?', (username,))
            conn.commit()
            conn.close()

            return redirect(url_for('profile_setup'))
        else:
            error = 'Invalid verification code. Please try again.'
            return render_template('verify.html', error=error)

    return render_template('verify.html')


def is_profile_setup_complete(username):
    with open('users_data.txt', 'r') as file:
        data = json.load(file)
        if username in data:
            return True

    # Check if the user's profile picture file exists in the uploads folder
    profile_picture_path = os.path.join('static/uploads', f"{username}.jpg")
    if os.path.exists(profile_picture_path):
        return True

    # Profile setup is not complete
    return False

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('homepage'))

    if request.method == 'POST':
        username = request.form['username'].strip().lower()  # Remove spaces and convert to lowercase
        password = request.form['password']

        # Connect to the database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        # Retrieve the hashed password for the given username
        c.execute('SELECT password FROM users WHERE username = ?', (username,))
        hashed_password = c.fetchone()
        # Close the connection
        conn.close()

        if hashed_password is None or not bcrypt.checkpw(password.encode('utf-8'), hashed_password[0].encode('utf-8')):
            error = 'Invalid username or password. Please try again.'
            return render_template('home.html', error=error)
        else:
            session['username'] = username  # Set the 'username' value in the session

            if is_profile_setup_complete(username):
                return redirect(url_for('homepage'))
            else:
                return redirect(url_for('profile_setup'))

    return render_template('home.html', posts=posts)

@app.route('/like_post', methods=['POST'])
def like_post():
    post_id = request.form['post_id']

    # Get the username from the session
    username = session.get('username')

    if username is None:
        # User is not logged in, handle accordingly (e.g., redirect to login page)
        return redirect(url_for('login'))

    # Connect to the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Check if the user has already liked the post
    c.execute('SELECT * FROM likes WHERE post_id = ? AND username = ?', (post_id, username))
    existing_like = c.fetchone()

    if existing_like is None:
        # User has not liked the post, insert the like into the database
        c.execute('INSERT INTO likes (post_id, username) VALUES (?, ?)', (post_id, username))

        # Update the likes count for the post in the posts table
        c.execute('UPDATE posts SET likes = likes + 1 WHERE id = ?', (post_id,))
    else:
        # User has already liked the post, handle accordingly (e.g., show an error message)
        error = 'You have already liked this post'
        # Close the connection
        conn.close()
        return redirect(url_for('homepage', error=error))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    return redirect(url_for('homepage'))

@app.route('/dislike_post', methods=['POST'])
def dislike_post():
    post_id = request.form['post_id']

    # Get the username from the session
    username = session.get('username')

    if username is None:
        # User is not logged in, handle accordingly (e.g., redirect to login page)
        return redirect(url_for('login'))

    # Connect to the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Check if the user has already disliked the post
    c.execute('SELECT * FROM dislikes WHERE post_id = ? AND username = ?', (post_id, username))
    existing_dislike = c.fetchone()

    if existing_dislike is None:
        # User has not disliked the post, insert the dislike into the database
        c.execute('INSERT INTO dislikes (post_id, username) VALUES (?, ?)', (post_id, username))

        # Update the dislikes count for the post in the posts table
        c.execute('UPDATE posts SET dislikes = dislikes + 1 WHERE id = ?', (post_id,))
    else:
        # User has already disliked the post, handle accordingly (e.g., show an error message)
        error = 'You have already disliked this post'
        # Close the connection
        conn.close()
        return redirect(url_for('homepage', error=error))

    # Commit the changes to the database and close the connection
    conn.commit()
    conn.close()

    # Redirect the user to the homepage
    return redirect(url_for('homepage'))

@app.route('/comment_post/<int:post_id>', methods=['GET', 'POST'])
def comment_post(post_id):
    # Connect to the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create the comments table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                username TEXT,
                comment_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Commit the changes
    conn.commit()

    if request.method == 'POST':
        # Get the comment text from the form
        comment_text = request.form['comment']

        # Get the username from the session
        username = session.get('username')

        if username is None:
            # User is not logged in, handle accordingly (e.g., redirect to login page)
            return redirect(url_for('login'))

        # Insert the comment into the database
        c.execute('INSERT INTO comments (post_id, username, comment_text) VALUES (?, ?, ?)',
                  (post_id, username, comment_text))

        # Commit the changes
        conn.commit()

        # Redirect to the homepage or the post page
        return redirect(url_for('homepage'))

    # Retrieve the comments for the given post
    c.execute('SELECT * FROM comments WHERE post_id = ?', (post_id,))
    comments = c.fetchall()

    # Close the connection
    conn.close()

    # Render the comment form and pass the comments data to the HTML template
    return render_template('comment.html', post_id=post_id, comments=comments)

@app.route('/profile')
def profile():
    # Retrieve username from session
    username = session.get('username')

    # Retrieve user information from the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Retrieve user's bio and interests from users_data.txt
    with open('users_data.txt', 'r') as f:
        try:
            data = json.load(f)
        except json.decoder.JSONDecodeError:
            data = {}
        user_data = data.get(username, {})
        bio = user_data.get('bio', '')
        interests = user_data.get('interests', [])

    # Set the file path for the user's profile picture
    profile_picture_path = os.path.join('static/uploads', f'{username}.jpg')
    # Check if the profile picture file exists
    if os.path.isfile(profile_picture_path):
        profile_picture = url_for('static', filename=f'uploads/{username}.jpg')
    else:
        profile_picture = url_for('static', filename='uploads/default.jpg')  # Use a default picture if not found

    c.execute("SELECT id, content, likes FROM posts WHERE username=?", (username,))
    posts_db = c.fetchall()
    posts = [{'id': post[0], 'content': post[1], 'likes': post[2]} for post in posts_db]

    # Close the connection
    conn.close()

    # Render the profile page with the retrieved data
    return render_template('profile.html', username=username, bio=bio, interests=interests,
                           profile_picture=profile_picture, posts=posts)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile_setup', methods=['GET', 'POST'])
def profile_setup():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Retrieve form data
        profile_picture = request.files['profile_picture']
        bio = request.form['bio']
        interests = request.form.getlist('interests')

        # Input validation
        errors = []

        if profile_picture and not allowed_file(profile_picture.filename):
            errors.append("Invalid file format. Please upload an image with the extension: jpg, jpeg, or png.")

        if len(bio) > 200:
            errors.append("Bio should not exceed 200 characters.")

        if errors:
            return render_template('setup.html', errors=errors)

        # Save profile picture to a file
        if profile_picture:
            username = session['username']
            filename = username + '.jpg'  # Save the file with a .jpg extension
            file_path = os.path.join(app.config['UPLOAD'], filename)
            
            # Save the image with JPEG format
            image = Image.open(profile_picture)
            image.save(file_path, 'JPEG')

        # Save user data to the users_data.txt file
        username = session['username']
        user_data = {
            'username': username,
            'bio': bio,
            'interests': interests
        }
        with open('users_data.txt', 'r') as file:
            try:
                data = json.load(file)
            except json.decoder.JSONDecodeError:
                data = {}
        with open('users_data.txt', 'w') as file:
            data[username] = user_data
            json.dump(data, file)

        # Redirect the user to the desired page after successful setup
        return redirect(url_for('homepage'))

    username = session['username']  # Retrieve the username from the session
    return render_template('setup.html', username=username)

from flask import request, redirect, url_for, session

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        post_content = request.form['content']
        caption = request.form['caption']
        language = request.form['language']  # Retrieve the selected language from the form
        file = request.files['file']

        # Connect to the database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Insert the post data into the posts table
        username = session['username']
        c.execute('INSERT INTO posts (content, caption, language, username) VALUES (?, ?, ?, ?)', (post_content, caption, language, username))
        post_id = c.lastrowid

        # Get the file data and save it with a unique name based on the post ID
        if file:
            # Generate a unique file name using the post ID
            filename = f"{post_id}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Save the file name in the database for the corresponding post
            c.execute('UPDATE posts SET file_name = ? WHERE id = ?', (filename, post_id))

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

        return redirect(url_for('homepage'))

    return render_template('create_post.html')

@app.route('/download_file/<filename>')
def download_file(filename):
    upload_folder = app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    return send_file(file_path, as_attachment=True)

@app.route('/homepage')
def homepage():
    # Connect to the database
    conn = sqlite3.connect('database.db')
    user_id = session.get('user_id')

    if user_id:
        # Fetch the username from the database based on the user_id
        c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username = c.fetchone()[0]
    else:
        username = None

    c = conn.cursor()

    # Create the posts table if it doesn't exist
    c.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, username TEXT, likes INTEGER DEFAULT 0, dislikes INTEGER DEFAULT 0, comments_count INTEGER DEFAULT 0, file_name TEXT, caption TEXT)')

    # Fetch all the posts from the posts table with the like, dislike, comment counts, and caption
    c.execute('SELECT id, content, username, likes, dislikes, comments_count, file_name, caption, language FROM posts')
    posts_db = c.fetchall()
    usernames = [post[2] for post in posts_db]


    # Close the connection
    conn.close()
    
    # Convert the fetched posts to a list of dictionaries
    posts_data = [
        {
            'id': post[0],
            'content': post[1],
            'username': post[2],
            'like_count': post[3],
            'dislike_count': post[4],
            'comment_count': post[5],
            'file_name': post[6],
            'caption': post[7],
            'language': post[8]
        } for post in posts_db
    ]
    profile_pictures = {}
    for username in usernames:
        profile_picture_path = os.path.join('static/uploads', f'{username}.jpg')
        if os.path.isfile(profile_picture_path):
            profile_pictures[username] = url_for('static', filename=f'uploads/{username}.jpg')
        else:
            profile_pictures[username] = url_for('static', filename='uploads/default.jpg')


    error = request.args.get('error')  # Get the 'error' query parameter

    return render_template('homepage.html', posts=posts_data, username=username,error=error,profile_pictures=profile_pictures)

@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    # Connect to the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Get the username from the session
    username = session['username']

    # Check if the post belongs to the current user
    c.execute('SELECT * FROM posts WHERE id = ? AND username = ?', (post_id, username))
    post = c.fetchone()

    if post is None:
        # Post not found or does not belong to the user, handle accordingly (e.g., show an error message)
        error = 'Post not found or you are not authorized to delete it'
        # Close the connection
        conn.close()
        return redirect(url_for('homepage', error=error))

    # Delete the post from the database
    c.execute('DELETE FROM posts WHERE id = ?', (post_id,))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    return redirect(url_for('homepage'))

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')  # Get the 'query' parameter from the request

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)')
    c.execute('SELECT username FROM users WHERE username LIKE ?', ('%' + query + '%',))
    usernames = [result[0] for result in c.fetchall()]
    conn.close()

    results = []
    with open('users_data.txt', 'r') as f:
        try:
            data = json.load(f)
        except json.decoder.JSONDecodeError:
            data = {}

    for username in usernames:
        user_data = data.get(username, {})
        bio = user_data.get('bio', '')
        interests = user_data.get('interests', [])
        profile_picture = f'static/uploads/{username}.jpg'
        if not os.path.exists(profile_picture):
            profile_picture = 'static/uploads/default.jpg'
        results.append({
            'username': username,
            'bio': bio,
            'interests': interests,
            'profile_picture_url': profile_picture
        })

    return render_template('search.html', query=query, results=results)

@app.route('/globalchat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']  # Retrieve the username from the session
    return render_template('globalchat.html', username=username)

@app.route('/get_chat_history')
def get_chat_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT username, content FROM messages ORDER BY timestamp')
    messages = cursor.fetchall()
    chat_history = [{'username': username, 'content': content} for username, content in messages]
    conn.close()
    return jsonify({'messages': chat_history})

@app.route('/send_chat_message', methods=['POST'])
def send_chat_message():
    data = request.get_json()
    username = data['username']
    content = data['content']
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (username, content) VALUES (?, ?)', (username, content))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/profile/<username>')
def user_profile(username):
    # Read the user data from the file
    with open('users_data.txt', 'r') as f:
        try:
            data = json.load(f)
        except json.decoder.JSONDecodeError:
            data = {}

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, content, likes FROM posts WHERE username=?", (username,))
    posts_db = c.fetchall()
    posts = [{'id': post[0], 'content': post[1], 'likes': post[2]} for post in posts_db]

    # Close the connection
    conn.close()

    # Get the user's data from the loaded JSON
    user_data = data.get(username, {})
    bio = user_data.get('bio', '')
    interests = user_data.get('interests', [])

    # Set the file path for the user's profile picture
    profile_picture_path = os.path.join('static/uploads', f'{username}.jpg')
    # Check if the profile picture file exists
    if os.path.isfile(profile_picture_path):
        profile_picture = url_for('static', filename=f'uploads/{username}.jpg')
    else:
        profile_picture = url_for('static', filename='uploads/default.jpg')  # Use a default picture if not found
    # Render the profile template with the retrieved data
    return render_template('userprofile.html', username=username,posts=posts, profile_picture=profile_picture, bio=bio, interests=interests)

# Route for displaying the settings page
@app.route('/settings')
def settings():
    if 'username' not in session:
        return redirect(url_for('login'))
    # Retrieve the user's existing data from users_data.txt and pass it to the template
    # Replace 'username' with the actual username of the logged-in user
    username = session['username']
    with open('users_data.txt', 'r') as file:
        users_data = json.load(file)
        user_data = users_data.get(username)
        if user_data is None:
            return "User data not found."
        bio = user_data.get('bio', '')

    return render_template('settings.html', username=username, bio=bio)

# Route for handling profile picture upload
@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    # Retrieve the uploaded profile picture file
    profile_picture = request.files['profile_picture']
    
    # Save the file with the username as the filename
    # Replace 'username' with the actual username of the logged-in user
    username = session['username']
    filename = f'static/uploads/{username}.jpg'
    profile_picture.save(filename)
    
    # Perform any additional logic or database updates
    
    return redirect('/settings')

# Route for handling profile picture deletion
@app.route('/delete_profile_picture', methods=['POST'])
def delete_profile_picture():
    # Delete the profile picture file
    # Replace 'username' with the actual username of the logged-in user
    username = session['username']
    filename = f'static/uploads/{username}.jpg'
    if filename:
        os.remove(filename)
    else:
        error="No picture found"
    # Perform any additional logic or database updates
    
    return redirect('/settings')

# Route for updating the bio
@app.route('/update_bio', methods=['POST'])
def update_bio():
    # Retrieve the new bio from the form submission
    new_bio = request.form['bio']
    
    # Update the bio in users_data.txt for the logged-in user
    # Replace 'username' with the actual username of the logged-in user
    username = session['username']
    with open('users_data.txt', 'r') as file:
        users_data = json.load(file)
        user_data = users_data.get(username)
        if user_data:
            user_data['bio'] = new_bio
            # Save the updated data back to users_data.txt
            with open('users_data.txt', 'w') as file:
                json.dump(users_data, file)
    
    # Perform any additional logic or database updates
    
    return redirect('/settings')

# Route for the community page
@app.route('/community')
def community():
    # Fetch Python news
    python_news = get_python_news()

    # Fetch popular Python repositories
    python_repositories = get_popular_python_repositories()

    # Fetch C++ news
    cpp_news = get_cpp_news()

    # Fetch popular C++ repositories
    cpp_repositories = get_cpp_repositories()

    # Fetch Java news
    java_news = get_java_news()

    # Fetch popular Java repositories
    java_repositories = get_java_repositories()

    # Render the community.html template with the data
    return render_template('community.html', python_news=python_news, python_repositories=python_repositories,
                           cpp_news=cpp_news, cpp_repositories=cpp_repositories, java_news=java_news,
                           java_repositories=java_repositories)


# Function to fetch Python news
def get_python_news():
    api_key = "478b6c96de244efdb2e7d00ae3635c80"
    url = f"https://newsapi.org/v2/everything?q=python&apiKey={api_key}"
    response = requests.get(url)
    data = response.json()
    articles = data.get('articles', [])
    return articles


# Function to fetch popular Python repositories
def get_popular_python_repositories():
    url = "https://api.github.com/search/repositories?q=language:python&sort=stars&order=desc"
    response = requests.get(url)
    data = response.json()
    repositories = data.get('items', [])
    return repositories


@app.route('/news/cpp')
def get_cpp_news():
    # Retrieve latest news about C++
    api_key = '478b6c96de244efdb2e7d00ae3635c80'
    url = f'https://newsapi.org/v2/everything?q=c%2B%2B&apiKey={api_key}'
    response = requests.get(url)
    data = response.json()
    articles = data.get('articles', [])
    return articles


@app.route('/repositories/cpp')
def get_cpp_repositories():
    url = 'https://api.github.com/search/repositories?q=language:cpp&sort=stars&order=desc'
    response = requests.get(url)
    data = response.json()
    repositories = data.get('items', [])
    return repositories


@app.route('/news/java')
def get_java_news():
    # Retrieve latest news about Java
    api_key = '478b6c96de244efdb2e7d00ae3635c80'
    url = f'https://newsapi.org/v2/everything?q=java&apiKey={api_key}'
    response = requests.get(url)
    data = response.json()
    articles = data.get('articles', [])
    return articles


@app.route('/repositories/java')
def get_java_repositories():
    # Retrieve popular Java repositories
    url = 'https://api.github.com/search/repositories?q=language:java&sort=stars&order=desc'
    response = requests.get(url)
    data = response.json()
    repositories = data.get('items', [])
    return repositories


@app.route("/opinions")
def opinions():
    # Connect to the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Fetch opinions and upvotes from the opinions table
    c.execute("SELECT id, opinion_text, upvotes FROM opinions")
    opinions = c.fetchall()

    # Close the connection
    conn.close()

    # Pass the opinions data to the opinions.html template
    return render_template('opinions.html', opinions=opinions)


@app.route('/submit_opinion', methods=['POST'])
def submit_opinion():
    opinion_text = request.form['opinion']
    upvotes = 0

    # Connect to the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Insert the opinion into the opinions table
    c.execute('INSERT INTO opinions (opinion_text, upvotes) VALUES (?, ?)',
              (opinion_text, upvotes))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    # Redirect the user back to the opinions page or any other desired page
    return redirect(url_for('opinions'))
@app.route('/upvote/<int:opinion_id>', methods=['POST'])
def upvote(opinion_id):
    # Check if the user is authenticated
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login page if not authenticated

    username = session['username']  # Get the username from the session

    # Connect to the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Fetch the current upvotes count from the opinions table
    c.execute("SELECT upvotes FROM opinions WHERE id=?", (opinion_id,))
    row = c.fetchone()
    if row is not None:
        current_upvotes = row[0]
    else:
        current_upvotes = 0  # Default value when no result is found

    # Check if the user has already upvoted
    c.execute("SELECT COUNT(*) FROM upvotes WHERE opinion_id=? AND username=?", (opinion_id, username))
    row = c.fetchone()
    if row is not None:
        has_upvoted = row[0] > 0
    else:
        has_upvoted = False

    # Update the upvotes count if the user hasn't upvoted yet
    if not has_upvoted:
        current_upvotes += 1

        # Insert the upvote into the upvotes table
        c.execute("INSERT INTO upvotes (opinion_id, username) VALUES (?, ?)", (opinion_id, username))

        # Update the upvotes count in the opinions table
        c.execute("UPDATE opinions SET upvotes=? WHERE id=?", (current_upvotes, opinion_id))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    # Redirect the user back to the opinions page or any other desired page
    return redirect(url_for('opinions'))


@app.route("/logout")
def logout():
    # Clear the session data
    session.clear()
    # Redirect the user to the login page or any other page
    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True,host='192.168.1.49')