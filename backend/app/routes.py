import random
import logging
import re


from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app.database_model import User, PublicCrum
from app.mysql_connection import db

logger = logging.getLogger(__name__)

# Inventories Container
inventories = {}


# inventory_item id
inventory_id_counter = 1


# -------------------------------------------------------------#
# NOTE: For Public


# NOTE: For Private

# Crumbs Container
crumbs_private = []  # crumbs_private = {}
# crumb_id
crumb_id_private = 1
# -------------------------------------------------------------#


crumbl_blueprint = Blueprint("crumbl_blueprint", __name__)


@crumbl_blueprint.route("/", methods=["GET"])
def home():
    return jsonify("Crumbl Backend Online!")


# NOTE: Middleware for login_required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "You must be logged in to access this route"}), 403

        try:
            # verify user still exists in database
            user = User.query.get(session["user_id"])

            if not user:
                session.clear()
                return jsonify({"error": "User not found"}), 401

            # Check if session has expired
            if "last_activity" in session:
                last_activity = datetime.fromtimestamp(session["last_activity"])
                if datetime.now() - last_activity > timedelta(hours=24):
                    session.clear()  # Fixed typo: was session.clears()
                    return (
                        jsonify({"error": "Session expired, please login again"}),
                        401,
                    )

            # Update last_activity timestamp
            session["last_activity"] = datetime.now().timestamp()
            return f(*args, **kwargs)

        except Exception as e:
            raise e

    return decorated_function


# NOTE: Login route
@crumbl_blueprint.route("/login", methods=["POST"])
def login():
    try:
        email = request.json.get("email")
        password = request.json.get("password")

        # validate input
        if not all([email, password]):
            return jsonify({"error": "Email and password are required"}), 400

        # query the user from database
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid email or password"}), 401

        # create session
        session["user_id"] = user.id
        session["logged_in"] = True
        session["last_activity"] = datetime.now().timestamp()

        # Set session to expire after 24 hours
        session.permanent = True

        return (
            jsonify(
                {
                    "message": "Login successfully",
                    "user": {
                        "firstName": user.firstName,
                        "lastName": user.lastName,
                        "email": user.email,
                    },
                }
            ),
            200,
        )
    except Exception as e:
        import traceback

        print("Error occurred:")
        print(traceback.format_exc)
        return jsonify({"error": f"Login failed : {str(e)}"}), 500


# NOTE: email validattion
def is_valid_email(email):
    """
    validate email format using regex pattern
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


# NOTE: Register route
@crumbl_blueprint.route("/register", methods=["POST"])
def register():
    # PERF: for frontend, no need yet

    # if request.method == "OPTIONS":
    # return _build_cors_prelight_response()

    global user_id_counter, users

    try:
        # Debug print the request data
        print("Request JSON:", request.json)

        # Get User Input with debug prints
        email = request.json.get("email")
        firstName = request.json.get("firstName")
        lastName = request.json.get("lastName")
        homeAddress = request.json.get("homeAddress")
        password = request.json.get("password")

        # Validate required fields
        if not all([email, homeAddress, password]):
            return jsonify({"error": "Missing required fields"}), 400

        # validate email format
        if not is_valid_email(email):
            return jsonify({"error": "All fields are required"}), 400

        # Check if user already exists - modified for list structure
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "User's email already exist"}), 400

        # Create new user instance
        new_user = User(
            email=email,
            firstName=firstName,
            lastName=lastName,
            password=password,
            homeAddress=homeAddress,
        )

        # add to database and commit
        try:
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"User registered successfully: {email}")
            return (
                jsonify(
                    {
                        "message": "New user Created Successfully",
                        "user": {
                            "user_id": new_user.id,
                            "email": new_user.email,
                            "homeAddress": new_user.homeAddress,
                        },
                    }
                ),
                201,
            )

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        import traceback

        print("Error occurred:")
        print(traceback.format_exc())
        return jsonify({"error": f"Failed to register user: {str(e)}"}), 500


@crumbl_blueprint.route("/users", methods=["GET"])
def list_users():
    return jsonify({"user": users}), 200


@crumbl_blueprint.route("/logout", methods=["POST"])
@login_required
def logout():
    try:
        # Clear all session data
        session.clear()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Logout failed: {str(e)}"}), 500


# -------------------------------------------------------------#
# TODO: CRUD Operations for Inventory: - BETTY
# - Create Inventory Item: Allow the creation of new inventory
# items with fields like item name, description, quantity, and
# price. With auto creation of ID Read Inventory Items: Provide
# APIs to list all inventory items or fetch a single item based on
# its ID.
# - Update Inventory Item: Allow the modification of an inventory
# item's details (name, quantity, price, etc.).by id
# - Delete Inventory Item: Enable deletion of an inventory item by ID
# -------------------------------------------------------------#



# lists full list of cookies
@crumbl_blueprint.route("/crumbls", methods=["GET"])
def listCookies():
    crumsPublic = PublicCrum.query.all()
    return jsonify([crum.serialize() for crum in crumsPublic])
   


# find specific cookie by ID number
@crumbl_blueprint.route("/crumbls/<int:cid>", methods=["GET"])
def findCrum(cid):
    crum = PublicCrum.query.get(cid)
    if crum is None:
        return jsonify("error: Crumbl Cookie not found"), 404
    return jsonify(crum.serialize())



# creates new crumbl cookie
@crumbl_blueprint.route("/crumbls", methods=["POST"])
def makeCrum():
    global crumbl_id_public
    if (
        not request.json
        or "name" not in request.json
        or "description" not in request.json
        or "quantity" not in request.json
        or "price" not in request.json
    ):
        return jsonify("error missing information"), 400

    try: 
        quant = int(request.json["quantity"])
        if quant < 0:
            return jsonify("Error:Quantity must be non-negative value"),400
        
        priced = round(float(request.json["price"]),2)
        if priced < 0: 
            return jsonify("Error:Price must be non-negative value"),400

    except ValueError:
            return jsonify("Error: Quantity must be integer and price must be float"),400

        
    newCrumbl = PublicCrum(
        name = request.json["name"],
        description = request.json["description"],
        quantity= quant,
        price = priced,
        #id = nID
    )
    db.session.add(newCrumbl)
    db.session.commit()

    return jsonify(newCrumbl.serialize()),201

 


# updates existing cookie
@crumbl_blueprint.route("/crumbls/<int:cid>", methods=["PUT"])
def updateCrum(cid):
  
    crum = PublicCrum.query.get(cid)
    if crum is None:
        jsonify("could not find cookie to update"), 404
    if not request.json:
        jsonify("please use proper json standards"), 400
    
    
    if 'quantity' in request.json:
        try:
            quant = int(request.json.get('quantity',crum.quantity))
            if quant < 0:
                return jsonify("Error:Quantity must be non-negative value"),400
        except ValueError:
            return jsonify("Error: Quantity must be a valid integer"),400
   
    if 'price' in request.json:
        try:
            price = round(float(request.json.get('price', crum.price)),2)
            if price < 0: 
                return jsonify("Error:Price must be non-negative value"),400
        except ValueError:
            return jsonify("Error: Price must be a valid float"),400
        
    crum.name = request.json.get('name', crum.name)
    crum.description = request.json.get('description', crum.description)
    crum.quantity = quant
    crum.price = price

    db.session.commit()
    return jsonify(crum.serialize())



# deletes crumbl cookie
@crumbl_blueprint.route("/crumbls/<int:cid>", methods=["DELETE"])
def deleteCrum(cid):
 
    crum = PublicCrum.query.get(cid)
    if crum is None:
        return jsonify("Crumble cookie could not be found"), 404
    
    db.session.delete(crum)
    db.session.commit()
    
    return jsonify({'success': 'crumbl cookie deleted'}), 200
 

# -------------------------------------------------------------#
# TODO: USER-Specific Inventory Management: - PHONG
# - Each Logged-in user will have their own inventory items, ensuring
# that users can only access and modify their own data.
# - Use sessions to ensure that only authenticated users can access
# inventory-related CRUD Operations
# -------------------------------------------------------------#
@crumbl_blueprint.route("/mycrumbls", methods=["GET"])
@login_required
def myListCookies():
    user_id = session.get("user_id")
    user_crumbls = [crum for crum in crumbs_private if crum["user_id"] == user_id]
    return jsonify(user_crumbls)


@crumbl_blueprint.route("/mycrumbls/<int:cid>", methods=["GET"])
@login_required
def findMyCrum(cid):
    user_id = session.get("user_id")
    foundC = next(
        (
            crum
            for crum in crumbs_private
            if crum["ID"] == cid and crum["user_id"] == user_id
        ),
        None,
    )
    if foundC is None:
        return jsonify({"error": "Crumbl Cookie not found"}), 404
    return jsonify(foundC)


@crumbl_blueprint.route("/mycrumbls", methods=["POST"])
@login_required
def makeMyCrum():
    user_id = session.get("user_id")
    if (
        not request.json
        or "name" not in request.json
        or "description" not in request.json
        or "quantity" not in request.json
        or "price" not in request.json
    ):
        return jsonify({"error": "Missing information"}), 400

    global crumb_id_private
    newCID = crumb_id_private
    crumb_id_private += 1
    newCrumbl = {
        "name": request.json["name"],
        "description": request.json["description"],
        "quantity": request.json["quantity"],
        "price": request.json["price"],
        "ID": newCID,
        "user_id": user_id,  # Associate new item with the logged-in user
    }
    crumbs_private.append(newCrumbl)
    return jsonify(newCrumbl), 201


@crumbl_blueprint.route("/mycrumbls/<int:cid>", methods=["PUT"])
@login_required
def updateMyCrum(cid):
    user_id = session.get("user_id")
    crum = next(
        (
            crum
            for crum in crumbs_private
            if crum["ID"] == cid and crum["user_id"] == user_id
        ),
        None,
    )
    if crum is None:
        return jsonify({"error": "Crumbl Cookie not found or unauthorized"}), 404
    if not request.json:
        return jsonify({"error": "Invalid JSON format"}), 400

    # Update fields if provided in request
    crum["name"] = request.json.get("name", crum["name"])
    crum["description"] = request.json.get("description", crum["description"])
    crum["quantity"] = request.json.get("quantity", crum["quantity"])
    crum["price"] = request.json.get("price", crum["price"])
    return jsonify(crum)


@crumbl_blueprint.route("/mycrumbls/<int:cid>", methods=["DELETE"])
@login_required
def deleteMyCrum(cid):
    global crumbs_private
    user_id = session.get("user_id")
    crum = next(
        (
            crum
            for crum in crumbs_private
            if crum["ID"] == cid and crum["user_id"] == user_id
        ),
        None,
    )
    if crum is None:
        return jsonify({"error": "Crumbl Cookie not found or unauthorized"}), 404
    crumbs_private = [
        c for c in crumbs_private if not (c["ID"] == cid and c["user_id"] == user_id)
    ]
    return jsonify({"message": "Item deleted successfully."}), 200


# -------------------------------------------------------------#
# TODO: Session and Cookie Security: - MATHEW
# - Secure user sessions with encryption (Flask Security key)
# - Implement proper session expiration handing to automatically
# log out.
# -------------------------------------------------------------#
