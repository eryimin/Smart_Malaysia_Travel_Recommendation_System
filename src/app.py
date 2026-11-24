"""Flask backend for the Smart Malaysia Travel Recommendation System."""



import os

import hmac

from functools import wraps


from flask import (

    Flask,

    jsonify,

    render_template,

    request,

    session,

    redirect

)



from werkzeug.security import check_password_hash

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False



from travel_recommender import TravelRecommender

from user_profile import UserProfile

from history_store import get_history, append_history

import json

from datetime import datetime

from pathlib import Path



# Load environment variables from .env

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)



ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()

ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")





app = Flask(

    __name__,

    template_folder="../templates",

    static_folder="../static"

)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-development-only-change-this-key")





travel_recommender = TravelRecommender()



# ==========================================

# ADMIN AUTHENTICATION

# ==========================================



ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()

ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")





def admin_required(function):

    @wraps(function)

    def decorated_function(*args, **kwargs):



        if not session.get("is_admin"):

            return jsonify({

                "success": False,

                "error": "Admin access required."

            }), 403



        return function(*args, **kwargs)



    return decorated_function



#admin login api

@app.route("/api/admin/login", methods=["POST"])

def admin_login():



    data = request.get_json(silent=True) or {}



    email = data.get("email", "")

    password = data.get("password", "")



    if not isinstance(email, str) or not isinstance(password, str):

        return jsonify({

            "success": False,

            "error": "Invalid login details."

        }), 400



    email = email.strip().lower()








    if (

        not ADMIN_EMAIL

        or not ADMIN_PASSWORD_HASH

        or not hmac.compare_digest(email, ADMIN_EMAIL)

        or not check_password_hash(ADMIN_PASSWORD_HASH, password)

    ):

        return jsonify({

            "success": False,

            "error": "Incorrect admin email or password."

        }), 401



    session.clear()

    session["is_admin"] = True

    session["admin_email"] = ADMIN_EMAIL



    return jsonify({

        "success": True,

        "message": "Admin login successful."

    })



#admin logout api

@app.route("/api/admin/logout", methods=["POST"])

@admin_required

def admin_logout():



    session.clear()



    return jsonify({

        "success": True,

        "message": "Admin logged out successfully."

    })



@app.route("/api/admin/status", methods=["GET"])

def admin_status():



    is_admin = session.get("is_admin", False)



    return jsonify({

        "is_admin": is_admin

    })





# ==========================================

# USER RATING AND REVIEW SYSTEM

# ==========================================



# File used to store user ratings and reviews

REVIEWS_FILE = (

    Path(__file__).resolve().parent.parent

    / "data" / "reviews.json"

)





def load_reviews():



    if not REVIEWS_FILE.exists():

        return []



    with open(REVIEWS_FILE, "r", encoding="utf-8") as file:

        return json.load(file)





def save_reviews(reviews):



    REVIEWS_FILE.parent.mkdir(

        parents=True,

        exist_ok=True

    )



    with open(REVIEWS_FILE, "w", encoding="utf-8") as file:

        json.dump(

            reviews,

            file,

            indent=4,

            ensure_ascii=False

        )





# ==========================================

# USER AND DESTINATION HELPERS

# ==========================================



def current_user():



    user_id = session.get("user_id")



    return UserProfile(user_id) if user_id else None



# ==========================================

# LOAD ALL USER PROFILES FOR ADMIN

# ==========================================



def load_all_user_profiles():



    profiles_dir = (

        Path(__file__).resolve().parent.parent

        / "data" / "profiles"

    )



    users = []



    if not profiles_dir.exists():

        return users



    for profile_file in profiles_dir.glob("*.json"):



        try:

            with open(

                profile_file,

                "r",

                encoding="utf-8"

            ) as file:

                profile = json.load(file)



            if not isinstance(profile, dict):

                continue



            users.append({

                "user_id": profile.get("user_id"),

                "created_at": profile.get("created_at"),

                "total_recommendations": len(

                    profile.get("recommendation_history", [])

                ),

                "total_favourites": len(

                    profile.get("favourites", [])

                )

            })



        except (OSError, ValueError, TypeError):

            continue



    return users





def destination_by_id(destination_id):



    return next(

        (

            d for d in travel_recommender.destinations

            if d["id"] == destination_id

        ),

        None

    )





# ==========================================

# HOME PAGE

# ==========================================



@app.route("/")

def index():



    return render_template("index.html")



# ==========================================

# ADMIN PAGE

# ==========================================



@app.route("/admin", methods=["GET"])

def admin_page():

    return render_template("admin.html")



# ==========================================

# ADMIN DASHBOARD PAGE

# ==========================================



@app.route("/admin/dashboard", methods=["GET"])

def admin_dashboard():



    if not session.get("is_admin"):

        return redirect("/admin")



    return render_template("admin_dashboard.html")





# ==========================================

# TRAVEL OPTIONS

# ==========================================



@app.route("/api/travel/options", methods=["GET"])

def travel_options():



    options = dict(travel_recommender.form_options)



    options["destination_categories"] = (

        ["Any"] +

        [

            k.replace("_", " ").title()

            for k in travel_recommender.CATEGORY_RULES

        ]

    )



    return jsonify(options)





# ==========================================

# GET ALL DESTINATIONS

# ==========================================



@app.route("/api/travel/festivals", methods=["GET"])
def festival_promotions():
    # Estimated promotional scenarios; original destination prices remain unchanged.
    return jsonify({"festivals": list(travel_recommender.festivals.values())})


@app.route("/api/travel/destinations", methods=["GET"])

def get_destinations():



    return jsonify(travel_recommender.destinations)





# ==========================================

# NEW: GET AVERAGE RATINGS FOR ALL DESTINATIONS

# ==========================================



@app.route("/api/travel/destinations/<destination_id>", methods=["GET"])
def get_destination(destination_id):
    destination = destination_by_id(destination_id)
    return jsonify(destination) if destination else (jsonify({"error": "Destination not found"}), 404)


@app.route("/api/travel/ratings", methods=["GET"])

def get_all_destination_ratings():



    reviews = load_reviews()



    ratings = {}



    for destination in travel_recommender.destinations:



        destination_id = destination["id"]



        destination_reviews = [

            review for review in reviews

            if review["destination_id"] == destination_id

        ]



        total_ratings = len(destination_reviews)



        average_rating = (

            round(

                sum(review["rating"] for review in destination_reviews)

                / total_ratings,

                1

            )

            if total_ratings > 0 else 0

        )



        ratings[destination_id] = {

            "average_rating": average_rating,

            "total_ratings": total_ratings

        }



    return jsonify(ratings)







# ==========================================

# NEW: GET ALL DESTINATIONS WITH USER REVIEWS

# ==========================================



@app.route("/api/travel/all-reviews", methods=["GET"])

def get_all_travel_reviews():



    reviews = load_reviews()



    result = []



    for destination in travel_recommender.destinations:



        destination_id = destination["id"]



        destination_reviews = [

            review for review in reviews

            if review["destination_id"] == destination_id

        ]



        # Skip destinations without ratings

        if not destination_reviews:

            continue



        total_ratings = len(destination_reviews)



        average_rating = round(

            sum(review["rating"] for review in destination_reviews)

            / total_ratings,

            1

        )



        result.append({

            "destination_id": destination_id,

            "destination_name": destination["name"],

            "state": destination["state"],

            "average_rating": average_rating,

            "total_ratings": total_ratings,

            "reviews": destination_reviews

        })



    # Show highest-rated destinations first

    result.sort(

        key=lambda item: (

            item["average_rating"],

            item["total_ratings"]

        ),

        reverse=True

    )



    return jsonify({

        "success": True,

        "destinations": result

    })







# ==========================================

# GET DESTINATION RATINGS AND REVIEWS

# ==========================================



@app.route(

    "/api/travel/destinations/<destination_id>/reviews",

    methods=["GET"]

)

def get_destination_reviews(destination_id):



    destination = destination_by_id(destination_id)



    if not destination:

        return jsonify({

            "error": "Destination not found"

        }), 404



    reviews = [

        review for review in load_reviews()

        if review["destination_id"] == destination_id

    ]



    total_reviews = len(reviews)



    average_rating = (

        round(

            sum(review["rating"] for review in reviews)

            / total_reviews,

            1

        )

        if total_reviews > 0 else 0

    )



    return jsonify({

        "destination_id": destination_id,

        "average_rating": average_rating,

        "total_reviews": total_reviews,

        "reviews": reviews

    })





# ==========================================

# NEW: SUBMIT DESTINATION RATING

# WRITTEN REVIEW IS OPTIONAL

# ==========================================



@app.route(

    "/api/travel/destinations/<destination_id>/reviews",

    methods=["POST"]

)

def submit_destination_review(destination_id):



    # Check whether the user is logged in

    user = current_user()



    if not user:

        return jsonify({

            "success": False,

            "error": "Please log in before submitting a rating."

        }), 401



    # Check whether the destination exists

    destination = destination_by_id(destination_id)



    if not destination:

        return jsonify({

            "success": False,

            "error": "Destination not found"

        }), 404



    # Get submitted data

    data = request.get_json(silent=True) or {}



    rating = data.get("rating")



    # Written review is optional

    review = data.get("review") or ""



    # Validate rating (1 to 5 stars)

    if (

        type(rating) is not int

        or rating < 1

        or rating > 5

    ):

        return jsonify({

            "success": False,

            "error": "Please select a rating between 1 and 5 stars."

        }), 400



    # Validate review data type

    if not isinstance(review, str):

        return jsonify({

            "success": False,

            "error": "Review must be text."

        }), 400



    review = review.strip()



    # Review is optional, but cannot exceed 1000 characters

    if len(review) > 1000:

        return jsonify({

            "success": False,

            "error": "Review cannot exceed 1000 characters."

        }), 400



    # Load existing ratings and reviews

    reviews = load_reviews()



    # Check whether this user has already rated this destination

    existing_review = next(

        (

            item for item in reviews

            if item["destination_id"] == destination_id

            and item["user_id"] == user.user_id

        ),

        None

    )



    # Get current date and time

    current_time = datetime.now().isoformat(

        timespec="seconds"

    )



    if existing_review:



        # Update the user's previous rating and review

        existing_review["rating"] = rating

        existing_review["review"] = review

        existing_review["created_at"] = current_time



        message = "Your rating has been updated successfully!"



    else:



        # Create a new rating and review

        new_review = {

            "destination_id": destination_id,

            "user_id": user.user_id,

            "rating": rating,

            "review": review,

            "created_at": current_time

        }



        reviews.append(new_review)



        message = "Your rating has been submitted successfully!"



    # Save updated ratings and reviews

    save_reviews(reviews)



    return jsonify({

        "success": True,

        "message": message

    })





# ==========================================

# CREATE USER / LOGIN

# ==========================================



@app.route("/api/user/create", methods=["POST"])

def create_user():



    data = request.get_json(silent=True) or {}



    try:



        user = UserProfile(

            data.get("user_id", "traveller1")

        )



        session["user_id"] = user.user_id



        return jsonify({

            "success": True,

            "user_id": user.user_id,

            "preferences": user.get_preferences()

        })



    except ValueError as error:



        return jsonify({

            "success": False,

            "error": str(error)

        }), 400





# ==========================================

# USER TRAVEL PREFERENCES

# ==========================================



@app.route("/api/user/preferences", methods=["GET", "POST"])

def user_preferences():



    user = current_user()



    if not user:

        return jsonify({

            "error": "User not logged in"

        }), 401



    if request.method == "GET":

        return jsonify(user.get_preferences())



    data = request.get_json(silent=True)



    try:



        if not isinstance(data, dict):

            raise ValueError(

                "Provide travel preferences as a JSON object."

            )



        merged = {

            **user.get_preferences(),

            **data

        }



        # Validate before saving

        travel_recommender._parse_preferences(merged)



        user.set_preferences(data)



        return jsonify({

            "success": True,

            "preferences": user.get_preferences()

        })



    except ValueError as error:



        return jsonify({

            "success": False,

            "error": str(error)

        }), 400





# ==========================================

# AI TRAVEL RECOMMENDATIONS

# ==========================================



@app.route("/api/travel/recommendations", methods=["POST"])

def get_recommendations():



    data = request.get_json(silent=True)



    try:



        if not isinstance(data, dict):

            raise ValueError(

                "Provide travel preferences as a JSON object."

            )



        user = current_user()



        # Festival mode is temporary and must not become a saved preference.
        festival_mode = data.pop("festival_mode", False)
        festival_id = data.pop("festival_id", None)
        if not isinstance(festival_mode, bool):
            raise ValueError("Invalid festival mode.")
        if festival_mode and not isinstance(festival_id, str):
            raise ValueError("Choose a valid festival.")
        preferences = {**user.get_preferences(), **data} if user else data
        recommendations = travel_recommender.recommend(
            preferences, festival_id=festival_id if festival_mode else None
        )



        
        if user:

            user.set_preferences(preferences)

            # Preserve existing history before the old
            # history-saving method potentially limits it.
            get_history(
                user.user_id,
                user.get_recommendation_history()
            )

            # Keep the existing user profile behaviour.
            user.add_to_recommendation_history(
                user.get_preferences(),
                [
                    item["destination"]["id"]
                    for item in recommendations
                ]
            )

            # Save to the new unlimited history archive.
            # Normal Mode and Festival Mode are separated.
            append_history(
                user.user_id,
                user.get_preferences(),
                [
                    item["destination"]["id"]
                    for item in recommendations
                ],
                festival_id if festival_mode else None
            )



        return jsonify({

            "success": True,

            "count": len(recommendations),

            "recommendations": recommendations

        })



    except ValueError as error:



        return jsonify({

            "success": False,

            "error": str(error)

        }), 400





# ==========================================

# USER FAVOURITES

# ==========================================



@app.route("/api/user/favourites", methods=["GET", "POST", "DELETE"])

def manage_favourites():



    user = current_user()



    if not user:

        return jsonify({

            "error": "User not logged in"

        }), 401



    if request.method == "GET":



        return jsonify([

            destination_by_id(id_)

            for id_ in user.get_favourites()

            if destination_by_id(id_)

        ])



    data = request.get_json(silent=True) or {}



    destination_id = data.get("destination_id")



    if (

        not isinstance(destination_id, str)

        or not destination_by_id(destination_id)

    ):

        return jsonify({

            "error": "Valid destination_id is required"

        }), 400



    if request.method == "POST":

        user.add_favourite(destination_id)

    else:

        user.remove_favourite(destination_id)



    return jsonify({

        "success": True,

        "favourite_destination_ids": user.get_favourites()

    })





# ==========================================

# RECOMMENDATION HISTORY

# ==========================================

# ==========================================
# RECOMMENDATION HISTORY
# ==========================================

@app.route("/api/user/history", methods=["GET"])
def travel_history():

    user = current_user()

    if not user:
        return jsonify({
            "error": "User not logged in"
        }), 401

    return jsonify(
        get_history(
            user.user_id,
            user.get_recommendation_history()
        )
    )


# ==========================================

# SYSTEM STATISTICS

# ==========================================



@app.route("/api/stats", methods=["GET"])

def stats():



    destinations = travel_recommender.destinations



    return jsonify({

        "total_destinations": len(destinations),

        "states": len({

            d["state"] for d in destinations

        }),

        "regions": sorted({

            d["region"] for d in destinations

        })

    })





# ==========================================

# ADMIN DATA ANALYTICS

# ==========================================



@app.route("/api/admin/analytics", methods=["GET"])

@admin_required

def admin_analytics():



    # Load existing destinations and reviews

    destinations = travel_recommender.destinations

    reviews = load_reviews()



    total_destinations = len(destinations)

    total_ratings = len(reviews)



    # Calculate overall average rating

    valid_ratings = [

        review["rating"]

        for review in reviews

        if type(review.get("rating")) in (int, float)

        and 1 <= review["rating"] <= 5

    ]



    average_rating = round(

        sum(valid_ratings) / len(valid_ratings), 2

    ) if valid_ratings else 0



    # Calculate ratings for each destination

    destination_analytics = []



    for destination in destinations:



        destination_id = destination["id"]



        destination_reviews = [

            review for review in reviews

            if review.get("destination_id") == destination_id

            and type(review.get("rating")) in (int, float)

            and 1 <= review["rating"] <= 5

        ]



        count = len(destination_reviews)



        destination_average = round(

            sum(review["rating"] for review in destination_reviews)

            / count, 2

        ) if count else 0



        destination_analytics.append({

            "destination_id": destination_id,

            "name": destination["name"],

            "state": destination["state"],

            "average_rating": destination_average,

            "total_ratings": count

        })



    # Sort destinations by highest rating

    destination_analytics.sort(

        key=lambda item: (

            item["average_rating"],

            item["total_ratings"]

        ),

        reverse=True

    )



    reviews = load_reviews()



    users = {

        review.get("user_id").strip()

        for review in reviews

        if isinstance(review, dict)

        and isinstance(review.get("user_id"), str)

        and review.get("user_id").strip()

    }



    return jsonify({

        "success": True,

        "total_users": len(users),

        "total_destinations": total_destinations,

        "total_ratings": total_ratings,

        "average_rating": average_rating,

        "destinations": destination_analytics

    })



# ==========================================

# ADMIN REVIEWER MANAGEMENT API

# ==========================================



@app.route("/api/admin/users", methods=["GET"])

@admin_required

def admin_users():



    reviews = load_reviews()

    reviewers = {}



    for review in reviews:



        user_id = review.get("user_id")

        rating = review.get("rating")

        created_at = review.get("created_at", "")



        if not isinstance(user_id, str) or not user_id.strip():

            continue



        if type(rating) not in (int, float) or not 1 <= rating <= 5:

            continue



        if user_id not in reviewers:

            reviewers[user_id] = {

                "user_id": user_id,

                "total_reviews": 0,

                "rating_sum": 0,

                "latest_review": "",

                "demo_reviews": 0

            }



        user = reviewers[user_id]



        user["total_reviews"] += 1

        user["rating_sum"] += rating



        if isinstance(created_at, str):

            if created_at > user["latest_review"]:

                user["latest_review"] = created_at



        if review.get("is_demo") is True:

            user["demo_reviews"] += 1



    users = []



    for user in reviewers.values():



        users.append({

            "user_id": user["user_id"],

            "latest_review": user["latest_review"],

            "total_reviews": user["total_reviews"],

            "average_rating": round(

                user["rating_sum"] / user["total_reviews"], 2

            ),

            "demo_reviews": user["demo_reviews"]

        })



    users.sort(

        key=lambda user: user["latest_review"],

        reverse=True

    )



    return jsonify({

        "success": True,

        "total_users": len(users),

        "users": users

    })







# ==========================================

# ERROR HANDLER

# ==========================================



@app.errorhandler(404)

def not_found(error):



    return jsonify({

        "error": "Not found"

    }), 404





# ==========================================

# RUN FLASK APPLICATION

# ==========================================



if __name__ == "__main__":



    app.run(

        debug=True,

        host="127.0.0.1",

        port=5000

    )


