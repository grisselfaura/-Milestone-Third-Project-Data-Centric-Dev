# Imported modules
import os
from flask import (
    Flask, flash, render_template, 
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env 


# Declaring app name
app = Flask(__name__)

# Config environmental variables saved on the env.py
app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
# secret key needed to create session cookies
app.secret_key = os.environ.get("SECRET_KEY")

# Creating an instance of Mongo
mongo = PyMongo(app)


# HOME
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")

# Code explanation from DCD  
@app.route('/documents')
def documents():
	# The URL looks something like 
	# /documents?limit=6&offset=0
	 
	# Request the limit (in the example URL == 6)	
	p_limit = int(request.args['limit'])

	# Request the offset (in the example URL == 0)	
	p_offset = int(request.args['offset'])
	
	# Prevent user to enter pages with negative values (server error)
	# only if he manually enters the value to URL
	if p_offset < 0:
		p_offset = 0

	# Prevent user to enter pages with values over the collection count(server error)
	# only if he manually enters the value to URL
	num_results = recipes_collection.find().count(),
	if p_offset > num_results:
		p_offset = num_results

	# Send the query with limit and offset taken from args
	recipes = recipes_collection.find().limit(p_limit).skip(p_offset)

	args = {
		"p_limit" : p_limit,
		"p_offset" : p_offset,
		"num_results" : num_results,
		"next_url" : f"/documents?limit={str(p_limit)}&offset={str(p_offset + p_limit)}",
		"prev_url" : f"/documents?limit={str(p_limit)}&offset={str(p_offset - p_limit)}",
		"recipes" : recipes
	}
	return render_template("documents.html", args=args)


# READ
# Page to view all recipes
@app.route("/get_recipes")
def get_recipes():
    recipes = list(mongo.db.recipes.find())
    #recipes = list(mongo.db.recipes.find({category_name: 1})) CHECK HOW TO CONNECT THIS TO FILTER
    return render_template("recipes.html", recipes=recipes)


# Page to view one recipes
@app.route("/view_recipe/<recipe_id>")
def view_recipe(recipe_id):
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    return render_template("view_recipe.html", recipe=recipe)


# Search functionality in the recipe page
@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    # Message for no search missing
    if len(recipes) == 0:
        flash("0 matches for \"{}\"".format(
            request.form.get("query")))
    return render_template("recipes.html", recipes=recipes)


# Register
@app.route("/join_free", methods=["GET", "POST"])
def join_free():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})
    
        if existing_user:
            flash("Username already exists, please choose another name.")
            return redirect(url_for("join_free")) 

        # Checking confirmation password
        password = request.form.get("password")
        password2 = request.form.get("password2")        

        if password == password2:
            join_free = {
                "username": request.form.get("username").lower(),
                "email": request.form.get("email").lower(), 
                "password": generate_password_hash(request.form.get("password"))
            }
            mongo.db.users.insert_one(join_free)

            # put the new user into "session" cookie
            session["user"] = request.form.get("username").lower()
            flash("Registration successful!")
            return redirect(url_for("myrecipes", username=session["user"]))

        else: 
            flash("Password does not match")
            return redirect(url_for("join_free"))

    return render_template("join_free.html")


# Sign In
@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                existing_user["password"], request.form.get("password")):
                    session["user"] = request.form.get("username").lower()
                    flash("Welcome, {}".format(
                        request.form.get("username")))
                    return redirect(url_for(
                        "myrecipes", username=session["user"]))
                    
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("sign_in"))

        else:
            # username doesnt exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("sign_in"))
    
    return render_template("sign_in.html")


@app.route("/myrecipes/<username>", methods=["GET", "POST"])
def myrecipes(username):
    # grab the session user's username from db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    
    if session["user"]: 
        return render_template("myrecipes.html", username=username)

    return redirect(url_for("sign_in"))


# Sign Out
@app.route("/sign_out")
def sign_out():
    # remove user from session cookies
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("sign_in"))


# CREATE
@app.route("/add_recipe",  methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        share_recipe = "on" if request.form.get("share_recipe") else "off"
        recipe = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_difficulty": request.form.get("recipe_difficulty"),
            "basic_ingredients": request.form.get("basic_ingredients").split(','),
            "complementary_ingredients": request.form.get("complementary_ingredients"),
            "recipe_method": request.form.get("recipe_method"),
            "recipe_images": request.form.get("recipe_images"),
            "closing_line": request.form.get("closing_line"),
            "share_recipe": share_recipe,
            "created_by": session["user"]
        }
        mongo.db.recipes.insert_one(recipe)
        flash("Recipe Successfully Added")
        return redirect(url_for("get_recipes"))

    categories = mongo.db.categories.find().sort("category_name", 1)
    difficulty = mongo.db.difficulty.find().sort("sort_difficult", 1)
    return render_template("add_recipe.html", categories=categories, 
                            difficulty=difficulty)


# UPDATE
@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if request.method == "POST":
        share_recipe = "on" if request.form.get("share_recipe") else "off"
        submit = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_difficulty": request.form.get("recipe_difficulty"),
            "basic_ingredients": request.form.get("basic_ingredients").split(','),
            "complementary_ingredients": request.form.get("complementary_ingredients"),
            "recipe_method": request.form.get("recipe_method"),
            "recipe_images": request.form.get("recipe_images"),
            "closing_line": request.form.get("closing_line"),
            "share_recipe": share_recipe,
            "created_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, submit)
        flash("Recipe Successfully Updated")
        return redirect(url_for("view_recipe", recipe_id=recipe_id))

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    difficulty = mongo.db.difficulty.find().sort("sort_difficult", 1)
    return render_template("edit_recipe.html", recipe=recipe, categories=categories, 
                            difficulty=difficulty)

# DELETE
@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    flash("Recipe Successfully Deleted")
    return redirect(url_for("get_recipes"))


@app.route("/get_categories")
def get_categories():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("categories.html", categories=categories)


@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    if request.method == "POST":
        category = {
            "category_name": request.form.get("category_name"),
            "category_image": request.form.get("category_image")
        }
        mongo.db.categories.insert_one(category)
        flash("New Category Added")
        return redirect(url_for("get_categories"))
        
    return render_template("add_category.html")


@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    if request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name"),
            "category_image": request.form.get("category_image")
        }
        mongo.db.categories.update({"_id": ObjectId(category_id)}, submit)
        flash("Category Successfully Updated")
        return redirect(url_for("get_categories"))
        
    category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
    return render_template("edit_category.html", category=category)


@app.route("/delete_category/<category_id>")
def delete_category(category_id):        
    mongo.db.categories.remove({"_id": ObjectId(category_id)})
    flash("Category Successfully Deleted")
    return redirect(url_for("get_categories"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)# change to false before submit this for assesment

