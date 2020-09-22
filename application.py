import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

from flask import url_for

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///adventure.db")

@app.route("/")
def landingpage():
    return render_template("landingpage.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("You must provide a username")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("You must provide a password")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to index page
        return redirect("/dashboard")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Display register.html if user is not registered
    if request.method == "GET":
        return render_template("register.html")

    # Get input from form and add to database
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        password2 = request.form.get("password2")

        if password != password2:

            flash("Passwords don't match")
            return render_template("register.html")

        # Look for username in database
        check = db.execute("SELECT * FROM users WHERE username =:username",username=username)

        # If username does not exist already, add new user to database
        if not check:

            hash_pwd = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            db.execute("INSERT INTO users (username, hash) VALUES(?,?)",username,hash_pwd)

            #Return to login page
            flash('You were successfully registered!')
            return render_template("login.html")

        else:

            flash("Username already in use")
            return render_template("register.html")


@app.route("/index/<string:project_id>", methods=["GET", "POST"])
@login_required
def index(project_id):
    """Display all lists and items from a selected project"""

    if request.method == "GET":
        # Name of selected project
        project_rows=db.execute("SELECT * FROM projects WHERE project_id=:project_id AND user_id=:user_id", project_id=project_id, user_id=session["user_id"])

        # Show saved lists
        saved_lists = db.execute("SELECT * FROM lists WHERE user_id = :user_id AND project_id=:project_id", user_id=session["user_id"],project_id=project_id)

        # If lists exist, make a table for each list
        items = db.execute("SELECT * FROM items WHERE id = :user_id", user_id=session["user_id"])

        # Weight of each list
        list_total = {}

        #Total weight of all items
        total_weight = 0

        for row in saved_lists:

            # Get list ID
            list_id = row["list_id"]

            # Look for items with selected list ID in items
            for item in items:

                if item["list_id"] == list_id:

                    item_weight =+ item["weight"] * item["quantity"]

                    # Add list ID if it does not exist
                    if list_id not in list_total.keys():

                        list_total[list_id] = item_weight

                    # List exists in dict, update total weight for that list
                    else:

                        list_total[list_id] += item_weight

                    # Update total for all items
                    total_weight += item_weight

        return render_template("index.html", items=items, saved_lists=saved_lists, total_weight=total_weight, list_total=list_total, project_rows=project_rows, project_id=project_id)

    # Add project description
    if request.method == "POST":

        # Get user input
        description = request.form.get("description")

        # Update database
        db.execute("UPDATE projects SET project_description=:description WHERE project_id=:project_id AND user_id=:user_id",
                    description=description,
                    project_id=project_id,
                    user_id=session["user_id"])

        return redirect(url_for('index', project_id=project_id))

@app.route("/newitem/<string:project_id>", methods=["POST"])
@login_required
def newitem(project_id):
    """Add item to list"""

    list_id = request.form["list_id"]
    item_name = request.form.get("item_name")
    description = request.form.get("description")
    weight = request.form.get("weight")
    quantity = request.form.get("quantity")
    user_id = session["user_id"]
    project_id=project_id

    # Add to database
    db.execute("INSERT INTO items (id, list_id, item_name, description, weight, quantity, project_id) VALUES (:user_id, :list_id, :item_name, :description, :weight, :quantity, :project_id)",
                user_id=user_id, list_id=list_id, item_name=item_name, description=description, weight=weight, quantity=quantity, project_id=project_id)

    return redirect(url_for('index', project_id=project_id))


@app.route("/newlist/<string:project_id>", methods=["POST"])
@login_required
def newlist(project_id):
    """Add list to project"""

    list_name = request.form.get("list_name")

    #Store list name and user id in database
    db.execute("INSERT INTO lists (user_id, list_name, project_id) VALUES (:user_id, :list_name, :project_id)", user_id=session["user_id"], list_name=list_name, project_id=project_id)

    return redirect(url_for('index', project_id=project_id))


@app.route("/del_list/<string:project_id>", methods=["GET", "POST"])
@login_required
def del_list(project_id):
    """ Deletes list from selected project"""

    if request.method == "GET":

        # Show saved lists
        saved_lists = db.execute("SELECT * FROM lists WHERE user_id = :user_id AND project_id=:project_id", user_id=session["user_id"], project_id=project_id)

    else:

        list_id = request.form["list_id"]

        # Delete from lists table
        db.execute("DELETE FROM lists WHERE list_id = :list_id AND user_id = :user_id AND project_id=:project_id", list_id=list_id, user_id=session["user_id"], project_id=project_id)

        # Delete from items table
        db.execute("DELETE FROM items WHERE list_id = :list_id AND id = :id AND project_id=:project_id", list_id=list_id, id=session["user_id"], project_id=project_id)

        return redirect(url_for('index', project_id=project_id))

@app.route("/del_item/<string:project_id>", methods=["POST"])
@login_required
def del_item(project_id):
    """Remove item from list"""

    # Get value of selected checkboxes - gets value by name
    selected = request.form.getlist('check')

    # Delete from database
    for item in selected:
        db.execute("DELETE FROM items WHERE id=:user_id AND item_id=:item_id AND project_id=:project_id", user_id=session["user_id"], item_id=item, project_id=project_id)

    return redirect(url_for('index', project_id=project_id))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    """Display dashboard"""

    if request.method == "GET":

        projects = db.execute("SELECT * FROM projects WHERE user_id=:user_id", user_id=session["user_id"])

        return render_template("dashboard.html", projects=projects)

    else:

        project_name = request.form.get("project_name")

        #Insert into projects
        db.execute("INSERT INTO projects (user_id, project_name) VALUES (:user_id, :project_name)", user_id=session["user_id"], project_name=project_name)

        return redirect("/dashboard")


@app.route("/del_project", methods=["GET", "POST"])
@login_required
def del_project():

    # Display projects
    if request.method == "GET":

        projects = db.execute("SELECT * FROM projects WHERE user_id=:user_id", user_id=session["user_id"])

        return render_template("dashboard.html", projects=projects)

    # Delete selected project
    else:
        project_id = request.form.get("project_id")

        # Projects
        db.execute("DELETE FROM projects WHERE project_id =:project_id AND user_id=:user_id", project_id=project_id, user_id=session["user_id"])

        # Items
        db.execute("DELETE FROM items WHERE project_id=:project_id AND id=:user_id", project_id=project_id, user_id=session["user_id"])

        # Lists
        db.execute("DELETE FROM lists WHERE project_id=:project_id AND user_id=:user_id", project_id=project_id, user_id=session["user_id"])

        return redirect ("/dashboard")


@app.route("/share_project/<int:project_id>", methods=["POST"])
@login_required
def share_project(project_id):
    """Share project to community/explore page"""

    # Get project name
    project_rows = db.execute("SELECT * FROM projects WHERE user_id =:user_id AND project_id=:project_id", user_id=session["user_id"], project_id=project_id)
    project_name = str(project_rows[0]["project_name"])

    # Project description
    description = project_rows[0]["project_description"]

    # Find all lists with project_id in "lists"
    lists = db.execute("SELECT * FROM lists WHERE project_id =:project_id AND user_id=:user_id", project_id=project_id, user_id=session["user_id"])

    # Find all items with project_id in "items"
    items = db.execute("SELECT * FROM items WHERE project_id =:project_id AND id=:user_id", project_id=project_id, user_id=session["user_id"])

    # Get username
    username_rows = db.execute("SELECT username FROM users WHERE id = :user_id", user_id = session["user_id"])
    username = str(username_rows[0]["username"])

    # Add project name to explore projects
    db.execute("INSERT INTO explore_projects (user_id, username, project_name) VALUES(:user_id, :username, :project_name)",
                user_id = session["user_id"],
                username=username,
                project_name=project_name)

    # Get project ID for this project. If the project has been posted before, the most recent one is selected.
    explore_project_rows = db.execute("SELECT project_id FROM explore_projects WHERE project_name = :project_name", project_name=project_name)
    explore_project_id = explore_project_rows[-1]["project_id"]

    if description:
        db.execute("UPDATE explore_projects SET project_description=:description WHERE project_id=:project_id AND user_id=:user_id",
                    description=description,
                    project_id=explore_project_id,
                    user_id=session["user_id"])

    for row in lists:
        # Add list names to explore_lists table
        db.execute("INSERT INTO explore_lists (user_id, project_id, list_id, list_name, project_name) VALUES (:user_id, :project_id, :list_id, :list_name, :project_name)",
                    user_id=session["user_id"],
                    project_id=explore_project_id,
                    list_id = row["list_id"],
                    list_name = row["list_name"],
                    project_name = project_name)

        for item in items:

            if item["list_id"] == row["list_id"]:

                # Add items to explore_items table
                db.execute("INSERT INTO explore_items (user_id, project_id, list_id, item_id, item_name, description, weight, quantity) VALUES (:user_id, :project_id, :list_id, :item_id, :item_name, :description, :weight, :quantity)",
                            user_id=session["user_id"],
                            project_id=explore_project_id,
                            list_id=row["list_id"],
                            item_id=item["item_id"],
                            item_name=item["item_name"],
                            description=item["description"],
                            weight=item["weight"],
                            quantity=item["quantity"])

    return redirect("/explore")


@app.route("/explore", methods=["GET"])
def explore():
    """Display post titles"""

    projects = db.execute("SELECT * FROM explore_projects")

    return render_template("explore.html", projects=projects)


@app.route("/explore_index/<int:project_id>", methods=["GET"])
def explore_index(project_id):
    """Display shared projects"""

    # Name of selected project
    project_rows=db.execute("SELECT * FROM explore_projects WHERE project_id=:project_id", project_id=project_id)
    project_name=project_rows[0]["project_name"]

    # Show saved lists
    saved_lists = db.execute("SELECT * FROM explore_lists WHERE project_id=:project_id", project_id=project_id)

    # Get all items related to project
    items = db.execute("SELECT * FROM explore_items WHERE project_id = :project_id", project_id=project_id)

    # Weight of each list
    list_total = {}

    #Total weight of all items
    total_weight = 0

    for row in saved_lists:

        # Get list ID
        list_id = row["list_id"]

        # Look for items with selected list ID in items
        for item in items:

            if item["list_id"] == list_id:

                item_weight =+ item["weight"] * item["quantity"]

                # Add list ID if it does not exist
                if list_id not in list_total.keys():

                    list_total[list_id] = item_weight

                # List exists in dict, update total weight for that list
                else:

                    list_total[list_id] += item_weight

                # Update total for all items
                total_weight += item_weight

    return render_template("explore_index.html", items=items, saved_lists=saved_lists, total_weight=total_weight, list_total=list_total, project_rows=project_rows, project_id=project_id)


@app.route("/edit_description/<int:project_id>", methods=["POST"])
@login_required
def edit_description(project_id):
    """Edit project description"""
    # User input
    new_description = request.form.get("edit_description")

    # Update description
    db.execute("UPDATE projects SET project_description=:new_description WHERE project_id=:project_id AND user_id=:user_id",
                    new_description=new_description,
                    project_id=project_id,
                    user_id=session["user_id"])

    return redirect(url_for('index', project_id=project_id))


@app.route("/edit_name/<int:project_id>", methods=["POST"])
@login_required
def edit_name(project_id):
    """Edit project name"""
    new_name = request.form.get("edit_name")

    # Update title
    db.execute("UPDATE projects SET project_name=:new_name WHERE project_id=:project_id AND user_id=:user_id",
                    new_name=new_name,
                    project_id=project_id,
                    user_id=session["user_id"])

    return redirect(url_for('index', project_id=project_id))


@app.route("/del_project_explore/<int:project_id>", methods=["POST"])
@login_required
def del_project_explore(project_id):
    """ Delete project - EXPLORE """
    projects = db.execute("SELECT * FROM explore_projects WHERE user_id=:user_id", user_id=session["user_id"])

    # Explore_projects
    db.execute("DELETE FROM explore_projects WHERE project_id =:project_id AND user_id=:user_id", project_id=project_id, user_id=session["user_id"])

    # Explore_Items
    db.execute("DELETE FROM explore_items WHERE project_id=:project_id AND user_id=:user_id", project_id=project_id, user_id=session["user_id"])

    # Explore_Lists
    db.execute("DELETE FROM explore_lists WHERE project_id=:project_id AND user_id=:user_id", project_id=project_id, user_id=session["user_id"])

    return redirect("/explore")


@app.route("/edit_description_explore/<int:project_id>", methods=["POST"])
@login_required
def edit_description_explore(project_id):
    """Edit project description - EXPLORE"""

    # User input
    new_description = request.form.get("edit_description")

    # Update description
    db.execute("UPDATE explore_projects SET project_description=:new_description WHERE project_id=:project_id AND user_id=:user_id",
                    new_description=new_description,
                    project_id=project_id,
                    user_id=session["user_id"])


    return redirect(url_for('explore_index', project_id=project_id))


@app.route("/edit_name_explore/<int:project_id>", methods=["POST"])
@login_required
def edit_name_explore(project_id):
    """Edit project name - EXPLORE"""

    new_name = request.form.get("edit_name")

    # Update title
    db.execute("UPDATE explore_projects SET project_name=:new_name WHERE project_id=:project_id AND user_id=:user_id",
                    new_name=new_name,
                    project_id=project_id,
                    user_id=session["user_id"])

    return redirect(url_for('explore_index', project_id=project_id))