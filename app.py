import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "mysecretkey123"
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///infj_platform.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), nullable=False, unique=True)

    password = db.Column(db.String(100), nullable=False)

    bio = db.Column(db.Text, default="")

    favorite_quote = db.Column(db.String(300), default="")

    profile_picture = db.Column(
        db.String(500),
        default="https://i.imgur.com/2DhmtJ4.png"
    )

    posts = db.relationship("Post", backref="author", lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    is_anonymous = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)

    category = db.Column(db.String(100), default="General")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    comments = db.relationship(
        "Comment",
        backref="post",
        lazy=True,
        cascade="all, delete"
    )

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Journal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(100), nullable=False)
    energy = db.Column(db.String(100), nullable=False)
    note = db.Column(db.Text)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))    

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) 

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))

    post = db.relationship("Post")   

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    message = db.Column(db.String(300))

    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )   


@app.route("/journal", methods=["GET", "POST"])
@login_required
def journal():
    if request.method == "POST":
        content = request.form.get("content")

        if content:
            new_entry = Journal(content=content, user_id=current_user.id)
            db.session.add(new_entry)
            db.session.commit()

        return redirect("/journal")

    entries = Journal.query.filter_by(user_id=current_user.id).order_by(Journal.id.desc()).all()
    return render_template("journal.html", entries=entries)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/learn")
def learn():
    return render_template("learn.html")

@app.route("/community", methods=["GET", "POST"])
@login_required
def community():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        category = request.form.get("category")
        is_anonymous = True if request.form.get("anonymous") == "on" else False

        if title and content:
            new_post = Post(
                title=title,
                content=content,
                user_id=current_user.id,
                is_anonymous=is_anonymous,
                category=category
            )

            db.session.add(new_post)
            db.session.commit()

        return redirect("/community")

    selected_category = request.args.get("category")
    search = request.args.get("search")

    query = Post.query

    if selected_category and selected_category != "All":
        query = query.filter_by(category=selected_category)

    if search:
        query = query.filter(
            (Post.title.contains(search)) |
            (Post.content.contains(search)) |
            (Post.category.contains(search))
        )

    posts = query.order_by(Post.id.desc()).all()

    return render_template(
        "community.html",
        posts=posts,
        selected_category=selected_category,
        search=search
    )

@app.route("/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    content = request.form.get("comment")

    if content:
        new_comment = Comment(content=content, post_id=post_id, user_id=current_user.id)
        db.session.add(new_comment)
        db.session.commit()

        post = Post.query.get(post_id)

        if post.user_id != current_user.id:
            notification = Notification(
                message=f"{current_user.username} commented on your post.",
                user_id=post.user_id
            )

            db.session.add(notification)
            db.session.commit()

    return redirect("/community")

@app.route("/like_post/<int:post_id>")
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)

    post.likes += 1
    db.session.commit()

    return redirect("/community")

@app.route("/infj-basics")
def infj_basics():
    return render_template("infj_basics.html")


@app.route("/cognitive-functions")
def cognitive_functions():
    return render_template("cognitive_functions.html")


@app.route("/infj-love")
def infj_love():
    return render_template("infj_love.html")


@app.route("/infj-growth")
def infj_growth():
    return render_template("infj_growth.html")

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

@app.route("/delete_post/<int:post_id>")
@login_required
def delete_post(post_id):

    post = Post.query.get_or_404(post_id)

    if post.user_id != current_user.id:
        return "Unauthorized"

    db.session.delete(post)
    db.session.commit()

    return redirect("/community")

@app.route("/delete_comment/<int:comment_id>")
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    db.session.delete(comment)
    db.session.commit()

    return redirect("/community")

@app.route("/delete_journal/<int:entry_id>")
@login_required
def delete_journal(entry_id):

    entry = Journal.query.get_or_404(entry_id)

    if entry.user_id != current_user.id:
        return "Unauthorized"

    db.session.delete(entry)
    db.session.commit()

    return redirect("/journal")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            return "Username already exists. Try another one."

        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect("/dashboard")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            login_user(user)

            return redirect("/dashboard")

        return "Invalid username or password."

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user_posts = Post.query.filter_by(user_id=current_user.id).all()
    user_journals = Journal.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "dashboard.html",
        user_posts=user_posts,
        user_journals=user_journals
    )

@app.route("/profile")
@login_required
def profile():

    user_posts = Post.query.filter_by(user_id=current_user.id).all()

    user_journals = Journal.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        "profile.html",
        user_posts=user_posts,
        user_journals=user_journals
    )

@app.route("/mood", methods=["GET", "POST"])
@login_required
def mood():
    if request.method == "POST":
        mood_value = request.form.get("mood")
        energy = request.form.get("energy")
        note = request.form.get("note")

        new_mood = Mood(
            mood=mood_value,
            energy=energy,
            note=note,
            user_id=current_user.id
        )

        db.session.add(new_mood)
        db.session.commit()

        return redirect("/mood")

    moods = Mood.query.filter_by(user_id=current_user.id).order_by(Mood.id.desc()).all()

    return render_template("mood.html", moods=moods)

@app.route("/delete_mood/<int:mood_id>")
@login_required
def delete_mood(mood_id):
    mood_entry = Mood.query.get_or_404(mood_id)

    if mood_entry.user_id != current_user.id:
        return "Unauthorized"

    db.session.delete(mood_entry)
    db.session.commit()

    return redirect("/mood")

@app.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        username = request.form.get("username")
        bio = request.form.get("bio")
        favorite_quote = request.form.get("favorite_quote")
        profile_picture_url = request.form.get("profile_picture")

        current_user.username = username
        current_user.bio = bio
        current_user.favorite_quote = favorite_quote

        uploaded_file = request.files.get("profile_picture_file")

        if uploaded_file and uploaded_file.filename != "":
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            uploaded_file.save(file_path)

            current_user.profile_picture = "/" + file_path.replace("\\", "/")

        elif profile_picture_url:
            current_user.profile_picture = profile_picture_url

        db.session.commit()

        return redirect("/profile")

    return render_template("edit_profile.html")

@app.route("/save_post/<int:post_id>")
@login_required
def save_post(post_id):
    existing = Bookmark.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()

    if not existing:
        bookmark = Bookmark(
            user_id=current_user.id,
            post_id=post_id
        )

        db.session.add(bookmark)
        db.session.commit()

    return redirect("/community")

@app.route("/saved")
@login_required
def saved():
    bookmarks = Bookmark.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template("saved.html", bookmarks=bookmarks)

@app.route("/remove_saved/<int:bookmark_id>")
@login_required
def remove_saved(bookmark_id):

    bookmark = Bookmark.query.get_or_404(bookmark_id)

    if bookmark.user_id != current_user.id:
        return "Unauthorized"

    db.session.delete(bookmark)
    db.session.commit()

    return redirect("/saved")

@app.route("/notifications")
@login_required
def notifications():

    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.id.desc()).all()

    return render_template(
        "notifications.html",
        notifications=notifications
    )

@app.route("/library")
@login_required
def library():

    books = [
        {
            "id": "monte_cristo",
            "title": "The Count of Monte Cristo",
            "author": "Alexandre Dumas",
            "cover": "https://images.unsplash.com/photo-1512820790803-83ca734da794"
        }
    ]

    return render_template(
        "library.html",
        books=books
    )


@app.route("/read/<book_id>")
@login_required
def read_book(book_id):

    if book_id == "monte_cristo":

        with open(
            "books/monte_cristo.txt",
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()

        return render_template(
            "reader.html",
            title="The Count of Monte Cristo",
            author="Alexandre Dumas",
            content=content
        )

    return "Book not found"

@app.route("/search")
@login_required
def search():
    return render_template("search.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)