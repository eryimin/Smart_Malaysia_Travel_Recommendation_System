MERGED SMART MALAYSIA TRAVEL SYSTEM
===================================
Use these files to replace the same paths in your EXISTING project. Do not delete your other files.

REPLACED: src/app.py, templates/index.html, static/js/app.js, static/css/style.css
NEW: templates/admin.html, templates/admin_dashboard.html, data/reviews.json, generate_demo_reviews.py
INCLUDED: static/images/login_landmarks.png, .env.example, .gitignore

KEEP YOUR EXISTING: src/travel_recommender.py, src/user_profile.py, data/destinations.json, other data,
static/js/destination_images.js, static/js/festival_design.js, static/css/festival_design.css,
existing images, welcome banner, and any other project assets.

IMPORTANT: Create .env from .env.example and use NEW admin credentials + random Flask secret key.
The shared .env secret from the chat is intentionally not included.
Generate admin password hash in Python:
  python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YOUR_NEW_PASSWORD'))"
For Flask secret key:
  python -c "import secrets; print(secrets.token_hex(32))"

Install: pip install flask werkzeug python-dotenv
Run: python src/app.py
Open: http://127.0.0.1:5000/ and http://127.0.0.1:5000/admin
The demo reviews file is prepopulated; do not run generate_demo_reviews.py unless you want additional demo records.
Review admin metrics distinguish unique reviewers from all user profiles; teammate implementation counts reviewers.
