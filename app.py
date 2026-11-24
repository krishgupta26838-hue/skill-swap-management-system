import os
import re
import time
from datetime import datetime, date, timedelta
from decimal import Decimal
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort
)
import mysql.connector
from mysql.connector import Error as DBError
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default-dev-skillswap-secret-key-2026")

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "skill_swap_db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_SSL_CA = os.getenv("DB_SSL_CA", "")


# =====================================================
# DATABASE HELPER & CONNECTION MANAGER
# =====================================================

def get_db_connection(use_database=True):
    """Establishes and returns a MySQL connection."""
    kwargs = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "charset": "utf8mb4",
        "use_unicode": True,
        "autocommit": False
    }
    if DB_SSL_CA:
        kwargs["ssl_ca"] = DB_SSL_CA
        kwargs["ssl_verify_cert"] = True
    if use_database:
        kwargs["database"] = DB_NAME
    return mysql.connector.connect(**kwargs)
    return mysql.connector.connect(**kwargs)


def split_sql_statements(content):
    """Splits multiple SQL statements safely respecting quotes and comments."""
    statements = []
    current = []
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    n = len(content)
    while i < n:
        c = content[i]
        c2 = content[i:i+2]
        
        if in_line_comment:
            if c == '\n':
                in_line_comment = False
            i += 1
            continue
            
        if in_block_comment:
            if c2 == '*/':
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
            
        if not in_single and not in_double and not in_backtick:
            if c2 == '--' or c == '#':
                in_line_comment = True
                i += 1
                continue
            if c2 == '/*':
                in_block_comment = True
                i += 2
                continue

        if c == "'" and not in_double and not in_backtick:
            if i > 0 and content[i-1] == '\\':
                pass
            else:
                in_single = not in_single
        elif c == '"' and not in_single and not in_backtick:
            if i > 0 and content[i-1] == '\\':
                pass
            else:
                in_double = not in_double
        elif c == '`' and not in_single and not in_double:
            in_backtick = not in_backtick

        if c == ';' and not in_single and not in_double and not in_backtick:
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(c)
        i += 1
        
    tail = ''.join(current).strip()
    if tail:
        statements.append(tail)
    return statements


# =====================================================
# AUTH DECORATORS & CONTEXT PROCESSORS
# =====================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "Admin":
            flash("Access denied. Admin privileges are required.", "danger")
            return redirect(url_for("user_dashboard"))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_global_data():
    """Provides current user state and pending counters to all templates."""
    user = None
    counts = {"pending_requests": 0, "pending_verifications": 0}
    if "user_id" in session:
        user = {
            "id": session.get("user_id"),
            "name": session.get("name"),
            "email": session.get("email"),
            "role": session.get("role"),
            "is_admin": session.get("role") == "Admin"
        }
        # Fetch pending counts for badge display in navigation
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # Pending received requests for this user
            cursor.execute(
                """
                SELECT COUNT(*) as cnt
                FROM LEARNING_REQUEST lr
                JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
                WHERE us.user_id = %s AND lr.status = 'Pending'
                """,
                (user["id"],)
            )
            r = cursor.fetchone()
            if r:
                counts["pending_requests"] = r["cnt"]

            if user["is_admin"]:
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM SKILL_VERIFICATION WHERE verification_status = 'Pending'"
                )
                v = cursor.fetchone()
                if v:
                    counts["pending_verifications"] = v["cnt"]
        except Exception:
            pass
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return {"current_user": user, "nav_counts": counts}


# =====================================================
# AUTHENTICATION ROUTES
# =====================================================

@app.route("/")
def index():
    if "user_id" in session:
        if session.get("role") == "Admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        phone = request.form.get("phone", "").strip() or None

        if not name or not email or not password:
            flash("Please fill in all required fields (Name, Email, Password).", "danger")
            return render_template("auth/register.html", name=name, email=email, phone=phone)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", name=name, email=email, phone=phone)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html", name=name, email=email, phone=phone)

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # Check unique email
            cursor.execute("SELECT user_id FROM `USER` WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("An account with that email already exists. Please log in.", "warning")
                return render_template("auth/register.html", name=name, email=email, phone=phone)

            hashed_pw = generate_password_hash(password)
            cursor.execute(
                """
                INSERT INTO `USER` (name, email, password, phone, role)
                VALUES (%s, %s, %s, %s, 'User')
                """,
                (name, email, hashed_pw, phone)
            )
            conn.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("login"))
        except DBError as err:
            if conn:
                conn.rollback()
            flash(f"Database error during registration: {err.msg}", "danger")
            return render_template("auth/register.html", name=name, email=email, phone=phone)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("auth/login.html", email=email)

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id, name, email, password, role FROM `USER` WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()

            if user and check_password_hash(user["password"], password):
                session.clear()
                session["user_id"] = user["user_id"]
                session["name"] = user["name"]
                session["email"] = user["email"]
                session["role"] = user["role"]
                flash(f"Welcome back, {user['name']}!", "success")
                next_page = request.args.get("next")
                if next_page and next_page.startswith("/"):
                    return redirect(next_page)
                if user["role"] == "Admin":
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("user_dashboard"))
            else:
                flash("Invalid email or password. Please try again.", "danger")
                return render_template("auth/login.html", email=email)
        except DBError as err:
            flash(f"Database error during login: {err.msg}", "danger")
            return render_template("auth/login.html", email=email)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("auth/login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("login"))


# =====================================================
# USER DASHBOARD & PROFILE
# =====================================================

@app.route("/dashboard")
@login_required
def user_dashboard():
    user_id = session["user_id"]
    conn = None
    cursor = None
    stats = {
        "offering_count": 0,
        "learning_count": 0,
        "pending_sent": 0,
        "pending_received": 0,
        "upcoming_sessions": 0,
        "avg_rating": None,
        "review_count": 0
    }
    upcoming_sessions = []
    recent_requests = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Offering skills count
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM USER_SKILL WHERE user_id = %s AND skill_type = 'Offering'",
            (user_id,)
        )
        stats["offering_count"] = cursor.fetchone()["cnt"]

        # 2. Learning skills count
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM USER_SKILL WHERE user_id = %s AND skill_type = 'Learning'",
            (user_id,)
        )
        stats["learning_count"] = cursor.fetchone()["cnt"]

        # 3. Pending requests sent
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM LEARNING_REQUEST WHERE requester_id = %s AND status = 'Pending'",
            (user_id,)
        )
        stats["pending_sent"] = cursor.fetchone()["cnt"]

        # 4. Pending requests received
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM LEARNING_REQUEST lr
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            WHERE us.user_id = %s AND lr.status = 'Pending'
            """,
            (user_id,)
        )
        stats["pending_received"] = cursor.fetchone()["cnt"]

        # 5. Upcoming sessions
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM `SESSION` s
            JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            WHERE (lr.requester_id = %s OR us.user_id = %s)
              AND s.status = 'Scheduled'
              AND s.session_date >= CURDATE()
            """,
            (user_id, user_id)
        )
        stats["upcoming_sessions"] = cursor.fetchone()["cnt"]

        # 6. Average rating as a teacher
        cursor.execute(
            """
            SELECT COUNT(f.feedback_id) AS cnt, AVG(f.rating) AS avg_score
            FROM FEEDBACK f
            JOIN `SESSION` s ON f.session_id = s.session_id
            JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            WHERE us.user_id = %s AND f.reviewer_id != %s
            """,
            (user_id, user_id)
        )
        r_rating = cursor.fetchone()
        if r_rating and r_rating["cnt"] > 0:
            stats["avg_rating"] = round(float(r_rating["avg_score"]), 2)
            stats["review_count"] = r_rating["cnt"]

        # 7. Next 3 upcoming sessions
        cursor.execute(
            """
            SELECT s.session_id, s.session_date, s.start_time, s.end_time, s.status,
                   sk.skill_name, sc.category_name,
                   lr.requester_id, us.user_id AS teacher_id,
                   req.name AS learner_name, tch.name AS teacher_name
            FROM `SESSION` s
            JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            JOIN `USER` req ON lr.requester_id = req.user_id
            JOIN `USER` tch ON us.user_id = tch.user_id
            WHERE (lr.requester_id = %s OR us.user_id = %s)
              AND s.status = 'Scheduled'
              AND s.session_date >= CURDATE()
            ORDER BY s.session_date ASC, s.start_time ASC
            LIMIT 3
            """,
            (user_id, user_id)
        )
        upcoming_sessions = cursor.fetchall()

        # 8. Recent 5 requests (sent or received)
        cursor.execute(
            """
            SELECT lr.request_id, lr.request_date, lr.status,
                   sk.skill_name, sc.category_name,
                   lr.requester_id, us.user_id AS teacher_id,
                   req.name AS learner_name, tch.name AS teacher_name
            FROM LEARNING_REQUEST lr
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            JOIN `USER` req ON lr.requester_id = req.user_id
            JOIN `USER` tch ON us.user_id = tch.user_id
            WHERE lr.requester_id = %s OR us.user_id = %s
            ORDER BY lr.request_date DESC
            LIMIT 5
            """,
            (user_id, user_id)
        )
        recent_requests = cursor.fetchall()

    except DBError as err:
        flash(f"Database error loading dashboard: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "user/dashboard.html",
        stats=stats,
        upcoming_sessions=upcoming_sessions,
        recent_requests=recent_requests
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]
    conn = None
    cursor = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip() or None

        if not name:
            flash("Name cannot be empty.", "danger")
            return redirect(url_for("profile"))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE `USER` SET name = %s, phone = %s WHERE user_id = %s",
                (name, phone, user_id)
            )
            conn.commit()
            session["name"] = name
            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile"))
        except DBError as err:
            if conn:
                conn.rollback()
            flash(f"Database error updating profile: {err.msg}", "danger")
            return redirect(url_for("profile"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # GET profile details
    user = None
    feedbacks = []
    avg_rating = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, name, email, phone, role, created_at FROM `USER` WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        # Feedbacks received as a teacher
        cursor.execute(
            """
            SELECT f.feedback_id, f.rating, f.comment, f.feedback_date,
                   reviewer.name AS reviewer_name, sk.skill_name
            FROM FEEDBACK f
            JOIN `SESSION` s ON f.session_id = s.session_id
            JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            JOIN `USER` reviewer ON f.reviewer_id = reviewer.user_id
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            WHERE us.user_id = %s AND f.reviewer_id != %s
            ORDER BY f.feedback_date DESC
            """,
            (user_id, user_id)
        )
        feedbacks = cursor.fetchall()

        if feedbacks:
            total_score = sum(fb["rating"] for fb in feedbacks)
            avg_rating = round(total_score / len(feedbacks), 2)

    except DBError as err:
        flash(f"Database error loading profile: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "user/profile.html",
        user=user,
        feedbacks=feedbacks,
        avg_rating=avg_rating
    )


# =====================================================
# MY SKILLS & BROWSE
# =====================================================

@app.route("/skills/my")
@login_required
def my_skills():
    user_id = session["user_id"]
    conn = None
    cursor = None
    offered_skills = []
    learning_skills = []
    all_categories = []
    skills_by_category = {}

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Offering skills with verification status
        cursor.execute(
            """
            SELECT us.user_skill_id, us.skill_id, sk.skill_name, sc.category_name,
                   sv.verification_id, sv.verification_status, sv.verification_date,
                   admin_u.name AS verified_by_admin
            FROM USER_SKILL us
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            LEFT JOIN SKILL_VERIFICATION sv ON us.user_skill_id = sv.user_skill_id
            LEFT JOIN `USER` admin_u ON sv.admin_id = admin_u.user_id
            WHERE us.user_id = %s AND us.skill_type = 'Offering'
            ORDER BY sc.category_name ASC, sk.skill_name ASC
            """,
            (user_id,)
        )
        offered_skills = cursor.fetchall()

        # 2. Learning skills
        cursor.execute(
            """
            SELECT us.user_skill_id, us.skill_id, sk.skill_name, sc.category_name
            FROM USER_SKILL us
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            WHERE us.user_id = %s AND us.skill_type = 'Learning'
            ORDER BY sc.category_name ASC, sk.skill_name ASC
            """,
            (user_id,)
        )
        learning_skills = cursor.fetchall()

        # 3. All skills grouped by category for adding
        cursor.execute(
            """
            SELECT s.skill_id, s.skill_name, sc.category_id, sc.category_name
            FROM SKILL s
            JOIN SKILL_CATEGORY sc ON s.category_id = sc.category_id
            ORDER BY sc.category_name ASC, s.skill_name ASC
            """
        )
        all_skills = cursor.fetchall()
        for s in all_skills:
            cat_name = s["category_name"]
            if cat_name not in skills_by_category:
                skills_by_category[cat_name] = []
            skills_by_category[cat_name].append(s)

        cursor.execute("SELECT category_id, category_name FROM SKILL_CATEGORY ORDER BY category_name ASC")
        all_categories = cursor.fetchall()

    except DBError as err:
        flash(f"Database error loading skills: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "user/my_skills.html",
        offered_skills=offered_skills,
        learning_skills=learning_skills,
        all_categories=all_categories,
        skills_by_category=skills_by_category
    )


@app.route("/skills/add", methods=["POST"])
@login_required
def add_my_skill():
    user_id = session["user_id"]
    skill_id = request.form.get("skill_id", type=int)
    skill_type = request.form.get("skill_type", "").strip()

    if not skill_id or skill_type not in ("Offering", "Learning"):
        flash("Invalid skill selection or skill type.", "danger")
        return redirect(url_for("my_skills"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check UNIQUE(user_id, skill_id, skill_type)
        cursor.execute(
            "SELECT user_skill_id FROM USER_SKILL WHERE user_id = %s AND skill_id = %s AND skill_type = %s",
            (user_id, skill_id, skill_type)
        )
        if cursor.fetchone():
            flash(f"You already have this skill in your '{skill_type}' list.", "warning")
            return redirect(url_for("my_skills"))

        cursor.execute(
            "INSERT INTO USER_SKILL (user_id, skill_id, skill_type) VALUES (%s, %s, %s)",
            (user_id, skill_id, skill_type)
        )
        conn.commit()
        flash(f"Successfully added to your {skill_type} skills!", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error adding skill: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_skills"))


@app.route("/skills/delete/<int:user_skill_id>", methods=["POST"])
@login_required
def delete_my_skill(user_skill_id):
    user_id = session["user_id"]
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check ownership
        cursor.execute(
            "SELECT user_skill_id, skill_type FROM USER_SKILL WHERE user_skill_id = %s AND user_id = %s",
            (user_skill_id, user_id)
        )
        listing = cursor.fetchone()
        if not listing:
            flash("Skill listing not found or unauthorized.", "danger")
            return redirect(url_for("my_skills"))

        # ER Diagram Rule: Check dependent rows before deleting USER_SKILL
        # Check requests
        cursor.execute(
            "SELECT COUNT(*) AS req_count FROM LEARNING_REQUEST WHERE user_skill_id = %s",
            (user_skill_id,)
        )
        req_count = cursor.fetchone()["req_count"]

        # Check verification
        cursor.execute(
            "SELECT COUNT(*) AS ver_count FROM SKILL_VERIFICATION WHERE user_skill_id = %s",
            (user_skill_id,)
        )
        ver_count = cursor.fetchone()["ver_count"]

        if req_count > 0 or ver_count > 0:
            reasons = []
            if req_count > 0:
                reasons.append(f"{req_count} learning request(s)")
            if ver_count > 0:
                reasons.append(f"{ver_count} verification record")
            flash(
                f"Cannot remove this skill listing because it has dependent records ({', '.join(reasons)}). "
                "Historical swap and verification records must be preserved.",
                "warning"
            )
            return redirect(url_for("my_skills"))

        cursor.execute("DELETE FROM USER_SKILL WHERE user_skill_id = %s", (user_skill_id,))
        conn.commit()
        flash("Skill listing removed successfully.", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error deleting skill: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_skills"))


@app.route("/skills/verify/<int:user_skill_id>", methods=["POST"])
@login_required
def request_skill_verification(user_skill_id):
    user_id = session["user_id"]
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify ownership & skill_type='Offering'
        cursor.execute(
            "SELECT user_skill_id, skill_type FROM USER_SKILL WHERE user_skill_id = %s AND user_id = %s",
            (user_skill_id, user_id)
        )
        listing = cursor.fetchone()
        if not listing:
            flash("Skill listing not found or unauthorized.", "danger")
            return redirect(url_for("my_skills"))

        if listing["skill_type"] != "Offering":
            flash("Only skills you offer can be submitted for verification.", "warning")
            return redirect(url_for("my_skills"))

        # Rule: auto-assign existing Admin with fewest Pending verifications
        cursor.execute(
            """
            SELECT u.user_id, COUNT(sv.verification_id) AS pending_count
            FROM `USER` u
            LEFT JOIN SKILL_VERIFICATION sv ON u.user_id = sv.admin_id AND sv.verification_status = 'Pending'
            WHERE u.role = 'Admin'
            GROUP BY u.user_id
            ORDER BY pending_count ASC, u.user_id ASC
            LIMIT 1
            """
        )
        admin_row = cursor.fetchone()
        if not admin_row:
            flash("No admin is currently registered to verify skills.", "danger")
            return redirect(url_for("my_skills"))

        assigned_admin_id = admin_row["user_id"]

        # Check if verification record already exists
        cursor.execute(
            "SELECT verification_id, verification_status FROM SKILL_VERIFICATION WHERE user_skill_id = %s",
            (user_skill_id,)
        )
        existing = cursor.fetchone()

        if existing:
            if existing["verification_status"] == "Verified":
                flash("This skill is already verified!", "info")
            elif existing["verification_status"] == "Pending":
                flash("A verification request for this skill is already pending review.", "info")
            elif existing["verification_status"] == "Rejected":
                # Re-request must UPDATE back to Pending
                cursor.execute(
                    """
                    UPDATE SKILL_VERIFICATION
                    SET verification_status = 'Pending', admin_id = %s, verification_date = NULL
                    WHERE verification_id = %s
                    """,
                    (assigned_admin_id, existing["verification_id"])
                )
                conn.commit()
                flash("Skill verification re-submitted for review!", "success")
        else:
            # Insert new verification request
            cursor.execute(
                """
                INSERT INTO SKILL_VERIFICATION (user_skill_id, admin_id, verification_status, verification_date)
                VALUES (%s, %s, 'Pending', NULL)
                """,
                (user_skill_id, assigned_admin_id)
            )
            conn.commit()
            flash("Verification request submitted successfully! An admin will review it.", "success")

    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error requesting verification: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_skills"))


@app.route("/browse")
@login_required
def browse_skills():
    user_id = session["user_id"]
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    verified_only = request.args.get("verified_only") == "1"

    conn = None
    cursor = None
    listings = []
    categories = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT category_id, category_name FROM SKILL_CATEGORY ORDER BY category_name ASC")
        categories = cursor.fetchall()

        # Build dynamic query
        query = """
            SELECT us.user_skill_id, us.user_id AS teacher_id,
                   u.name AS teacher_name, u.email AS teacher_email, u.phone AS teacher_phone,
                   s.skill_id, s.skill_name, sc.category_name,
                   sv.verification_status,
                   -- Teacher's average rating across all completed sessions
                   (
                       SELECT ROUND(AVG(f.rating), 2)
                       FROM FEEDBACK f
                       JOIN `SESSION` sess ON f.session_id = sess.session_id
                       JOIN LEARNING_REQUEST lr_sub ON sess.request_id = lr_sub.request_id
                       JOIN USER_SKILL us_sub ON lr_sub.user_skill_id = us_sub.user_skill_id
                       WHERE us_sub.user_id = u.user_id AND f.reviewer_id != u.user_id
                   ) AS teacher_rating,
                   (
                       SELECT COUNT(f.feedback_id)
                       FROM FEEDBACK f
                       JOIN `SESSION` sess ON f.session_id = sess.session_id
                       JOIN LEARNING_REQUEST lr_sub ON sess.request_id = lr_sub.request_id
                       JOIN USER_SKILL us_sub ON lr_sub.user_skill_id = us_sub.user_skill_id
                       WHERE us_sub.user_id = u.user_id AND f.reviewer_id != u.user_id
                   ) AS teacher_review_count,
                   -- Existing request from current user for this listing
                   (
                       SELECT lr_curr.status
                       FROM LEARNING_REQUEST lr_curr
                       WHERE lr_curr.requester_id = %s AND lr_curr.user_skill_id = us.user_skill_id
                   ) AS my_request_status
            FROM USER_SKILL us
            JOIN `USER` u ON us.user_id = u.user_id
            JOIN SKILL s ON us.skill_id = s.skill_id
            JOIN SKILL_CATEGORY sc ON s.category_id = sc.category_id
            LEFT JOIN SKILL_VERIFICATION sv ON us.user_skill_id = sv.user_skill_id
            WHERE us.skill_type = 'Offering'
              AND us.user_id != %s
        """
        params = [user_id, user_id]

        if q:
            query += " AND (s.skill_name LIKE %s OR u.name LIKE %s)"
            search_param = f"%{q}%"
            params.extend([search_param, search_param])

        if category_id:
            query += " AND sc.category_id = %s"
            params.append(category_id)

        if verified_only:
            query += " AND sv.verification_status = 'Verified'"

        query += " ORDER BY (sv.verification_status = 'Verified') DESC, s.skill_name ASC"

        cursor.execute(query, tuple(params))
        listings = cursor.fetchall()

    except DBError as err:
        flash(f"Database error browsing skills: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "user/browse.html",
        listings=listings,
        categories=categories,
        q=q,
        selected_category=category_id,
        verified_only=verified_only
    )


# =====================================================
# LEARNING REQUESTS
# =====================================================

@app.route("/requests")
@login_required
def requests_view():
    user_id = session["user_id"]
    conn = None
    cursor = None
    sent_requests = []
    received_requests = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Sent requests (current user is requester)
        cursor.execute(
            """
            SELECT lr.request_id, lr.request_date, lr.status,
                   sk.skill_name, sc.category_name,
                   tch.name AS teacher_name, tch.email AS teacher_email, tch.phone AS teacher_phone,
                   sv.verification_status,
                   (
                       SELECT COUNT(*)
                       FROM `SESSION` s
                       WHERE s.request_id = lr.request_id
                   ) AS session_count
            FROM LEARNING_REQUEST lr
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            JOIN `USER` tch ON us.user_id = tch.user_id
            LEFT JOIN SKILL_VERIFICATION sv ON us.user_skill_id = sv.user_skill_id
            WHERE lr.requester_id = %s
            ORDER BY lr.request_date DESC
            """,
            (user_id,)
        )
        sent_requests = cursor.fetchall()

        # 2. Received requests (current user is teacher)
        cursor.execute(
            """
            SELECT lr.request_id, lr.request_date, lr.status,
                   sk.skill_name, sc.category_name,
                   req.name AS requester_name, req.email AS requester_email, req.phone AS requester_phone,
                   (
                       SELECT COUNT(*)
                       FROM `SESSION` s
                       WHERE s.request_id = lr.request_id
                   ) AS session_count
            FROM LEARNING_REQUEST lr
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            JOIN `USER` req ON lr.requester_id = req.user_id
            WHERE us.user_id = %s
            ORDER BY lr.request_date DESC
            """,
            (user_id,)
        )
        received_requests = cursor.fetchall()

    except DBError as err:
        flash(f"Database error loading requests: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "user/requests.html",
        sent_requests=sent_requests,
        received_requests=received_requests
    )


@app.route("/requests/send/<int:user_skill_id>", methods=["POST"])
@login_required
def send_request(user_skill_id):
    user_id = session["user_id"]
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Validate target listing
        cursor.execute(
            "SELECT user_skill_id, user_id, skill_type FROM USER_SKILL WHERE user_skill_id = %s",
            (user_skill_id,)
        )
        target = cursor.fetchone()

        if not target:
            flash("Target skill listing was not found.", "danger")
            return redirect(url_for("browse_skills"))

        # Rule: only Offering skills
        if target["skill_type"] != "Offering":
            flash("Requests can only be sent for skill offerings.", "warning")
            return redirect(url_for("browse_skills"))

        # Rule: never requester's own listing
        if target["user_id"] == user_id:
            flash("You cannot request to learn from your own skill listing.", "warning")
            return redirect(url_for("browse_skills"))

        # Check existing row due to UNIQUE(requester_id, user_skill_id)
        cursor.execute(
            "SELECT request_id, status FROM LEARNING_REQUEST WHERE requester_id = %s AND user_skill_id = %s",
            (user_id, user_skill_id)
        )
        existing = cursor.fetchone()

        if existing:
            if existing["status"] == "Pending":
                flash("You already have a Pending request for this skill listing.", "info")
            elif existing["status"] == "Accepted":
                flash("Your request for this skill is already Accepted! You can schedule sessions.", "info")
            elif existing["status"] in ("Cancelled", "Rejected"):
                # Rule: Re-sending a request that was Cancelled or Rejected must UPDATE the existing row back to 'Pending' and refresh request_date
                cursor.execute(
                    """
                    UPDATE LEARNING_REQUEST
                    SET status = 'Pending', request_date = NOW()
                    WHERE request_id = %s
                    """,
                    (existing["request_id"],)
                )
                conn.commit()
                flash("Request re-sent successfully as Pending!", "success")
        else:
            cursor.execute(
                """
                INSERT INTO LEARNING_REQUEST (requester_id, user_skill_id, request_date, status)
                VALUES (%s, %s, NOW(), 'Pending')
                """,
                (user_id, user_skill_id)
            )
            conn.commit()
            flash("Learning request sent successfully!", "success")

    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error sending request: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("requests_view"))


@app.route("/requests/<int:request_id>/cancel", methods=["POST"])
@login_required
def cancel_request(request_id):
    user_id = session["user_id"]
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT request_id, requester_id, status FROM LEARNING_REQUEST WHERE request_id = %s",
            (request_id,)
        )
        req_row = cursor.fetchone()

        if not req_row or req_row["requester_id"] != user_id:
            flash("Request not found or unauthorized.", "danger")
            return redirect(url_for("requests_view"))

        if req_row["status"] != "Pending":
            flash(f"Only 'Pending' requests can be cancelled (current status: {req_row['status']}).", "warning")
            return redirect(url_for("requests_view"))

        cursor.execute(
            "UPDATE LEARNING_REQUEST SET status = 'Cancelled' WHERE request_id = %s",
            (request_id,)
        )
        conn.commit()
        flash("Request cancelled successfully.", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error cancelling request: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("requests_view"))


@app.route("/requests/<int:request_id>/action", methods=["POST"])
@login_required
def respond_request(request_id):
    user_id = session["user_id"]
    action = request.form.get("action", "").lower()

    if action not in ("accept", "reject"):
        flash("Invalid action on request.", "danger")
        return redirect(url_for("requests_view"))

    new_status = "Accepted" if action == "accept" else "Rejected"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check teacher ownership
        cursor.execute(
            """
            SELECT lr.request_id, lr.status, us.user_id AS teacher_id
            FROM LEARNING_REQUEST lr
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            WHERE lr.request_id = %s
            """,
            (request_id,)
        )
        req_row = cursor.fetchone()

        if not req_row or req_row["teacher_id"] != user_id:
            flash("Request not found or unauthorized.", "danger")
            return redirect(url_for("requests_view"))

        if req_row["status"] != "Pending":
            flash(f"Only 'Pending' requests can be responded to (current: {req_row['status']}).", "warning")
            return redirect(url_for("requests_view"))

        cursor.execute(
            "UPDATE LEARNING_REQUEST SET status = %s WHERE request_id = %s",
            (new_status, request_id)
        )
        conn.commit()
        flash(f"Request marked as {new_status}!", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error responding to request: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("requests_view"))


# =====================================================
# SESSIONS & FEEDBACK
# =====================================================

@app.route("/sessions")
@login_required
def sessions_view():
    user_id = session["user_id"]
    conn = None
    cursor = None
    upcoming_sessions = []
    past_sessions = []
    accepted_requests = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Accepted requests available for scheduling
        cursor.execute(
            """
            SELECT lr.request_id, sk.skill_name, sc.category_name,
                   lr.requester_id, us.user_id AS teacher_id,
                   req.name AS learner_name, tch.name AS teacher_name
            FROM LEARNING_REQUEST lr
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            JOIN `USER` req ON lr.requester_id = req.user_id
            JOIN `USER` tch ON us.user_id = tch.user_id
            WHERE (lr.requester_id = %s OR us.user_id = %s)
              AND lr.status = 'Accepted'
            ORDER BY lr.request_date DESC
            """,
            (user_id, user_id)
        )
        accepted_requests = cursor.fetchall()

        # 2. All sessions for current user (learner or teacher)
        cursor.execute(
            """
            SELECT s.session_id, s.request_id, s.session_date, s.start_time, s.end_time, s.status,
                   sk.skill_name, sc.category_name,
                   lr.requester_id, us.user_id AS teacher_id,
                   req.name AS learner_name, tch.name AS teacher_name,
                   -- Did current user submit feedback for this session?
                   (
                       SELECT COUNT(*)
                       FROM FEEDBACK f
                       WHERE f.session_id = s.session_id AND f.reviewer_id = %s
                   ) AS user_gave_feedback,
                   -- Total feedbacks for session
                   (
                       SELECT COUNT(*)
                       FROM FEEDBACK f
                       WHERE f.session_id = s.session_id
                   ) AS total_feedback_count
            FROM `SESSION` s
            JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            JOIN `USER` req ON lr.requester_id = req.user_id
            JOIN `USER` tch ON us.user_id = tch.user_id
            WHERE lr.requester_id = %s OR us.user_id = %s
            ORDER BY s.session_date DESC, s.start_time DESC
            """,
            (user_id, user_id, user_id)
        )
        all_sessions = cursor.fetchall()

        today = date.today()
        for sess in all_sessions:
            sess_date = sess["session_date"]
            if sess["status"] == "Scheduled" and sess_date >= today:
                upcoming_sessions.append(sess)
            else:
                past_sessions.append(sess)

    except DBError as err:
        flash(f"Database error loading sessions: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "user/sessions.html",
        upcoming_sessions=upcoming_sessions,
        past_sessions=past_sessions,
        accepted_requests=accepted_requests,
        today_str=date.today().isoformat()
    )


@app.route("/sessions/create", methods=["POST"])
@login_required
def create_session():
    user_id = session["user_id"]
    request_id = request.form.get("request_id", type=int)
    session_date_str = request.form.get("session_date", "").strip()
    start_time_str = request.form.get("start_time", "").strip()
    end_time_str = request.form.get("end_time", "").strip()

    if not request_id or not session_date_str or not start_time_str or not end_time_str:
        flash("Please provide all session details (request, date, start time, end time).", "danger")
        return redirect(url_for("sessions_view"))

    # Validation: date not in past
    try:
        session_date_val = datetime.strptime(session_date_str, "%Y-%m-%d").date()
        if session_date_val < date.today():
            flash("Session date cannot be in the past.", "warning")
            return redirect(url_for("sessions_view"))
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("sessions_view"))

    # Validation: end_time > start_time
    if end_time_str <= start_time_str:
        flash("End time must be strictly after start time.", "warning")
        return redirect(url_for("sessions_view"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Rule: sessions may only be created for requests with status 'Accepted'
        # and user must be learner or teacher
        cursor.execute(
            """
            SELECT lr.request_id, lr.status, lr.requester_id, us.user_id AS teacher_id
            FROM LEARNING_REQUEST lr
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            WHERE lr.request_id = %s
            """,
            (request_id,)
        )
        req_row = cursor.fetchone()

        if not req_row:
            flash("Learning request not found.", "danger")
            return redirect(url_for("sessions_view"))

        if req_row["status"] != "Accepted":
            flash("Sessions can only be scheduled for 'Accepted' learning requests.", "warning")
            return redirect(url_for("sessions_view"))

        if user_id not in (req_row["requester_id"], req_row["teacher_id"]):
            flash("You are not a participant in this learning request.", "danger")
            return redirect(url_for("sessions_view"))

        cursor.execute(
            """
            INSERT INTO `SESSION` (request_id, session_date, start_time, end_time, status)
            VALUES (%s, %s, %s, %s, 'Scheduled')
            """,
            (request_id, session_date_val, start_time_str, end_time_str)
        )
        conn.commit()
        flash("Session scheduled successfully!", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error scheduling session: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("sessions_view"))


@app.route("/sessions/<int:session_id>/status", methods=["POST"])
@login_required
def update_session_status(session_id):
    user_id = session["user_id"]
    new_status = request.form.get("status", "").strip()

    if new_status not in ("Completed", "Cancelled"):
        flash("Invalid session status update.", "danger")
        return redirect(url_for("sessions_view"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check participation
        cursor.execute(
            """
            SELECT s.session_id, s.status, lr.requester_id, us.user_id AS teacher_id
            FROM `SESSION` s
            JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            WHERE s.session_id = %s
            """,
            (session_id,)
        )
        sess = cursor.fetchone()

        if not sess or user_id not in (sess["requester_id"], sess["teacher_id"]):
            flash("Session not found or unauthorized.", "danger")
            return redirect(url_for("sessions_view"))

        cursor.execute(
            "UPDATE `SESSION` SET status = %s WHERE session_id = %s",
            (new_status, session_id)
        )
        conn.commit()
        flash(f"Session marked as {new_status}!", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error updating session: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("sessions_view"))


@app.route("/feedback/submit", methods=["POST"])
@login_required
def submit_feedback():
    user_id = session["user_id"]
    session_id = request.form.get("session_id", type=int)
    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip() or None

    if not session_id or not rating or not (1 <= rating <= 5):
        flash("Please provide a valid rating between 1 and 5 stars.", "danger")
        return redirect(url_for("sessions_view"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Strict Rule: Feedback only for Completed sessions, only by participant, 1 per (session, reviewer)
        cursor.execute(
            """
            SELECT s.session_id, s.status, lr.requester_id, us.user_id AS teacher_id
            FROM `SESSION` s
            JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id
            JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
            WHERE s.session_id = %s
            """,
            (session_id,)
        )
        sess = cursor.fetchone()

        if not sess:
            flash("Session was not found.", "danger")
            return redirect(url_for("sessions_view"))

        if sess["status"] != "Completed":
            flash("Feedback can only be submitted for 'Completed' sessions.", "warning")
            return redirect(url_for("sessions_view"))

        if user_id not in (sess["requester_id"], sess["teacher_id"]):
            flash("Only session participants can submit feedback.", "danger")
            return redirect(url_for("sessions_view"))

        # Check UNIQUE(session_id, reviewer_id)
        cursor.execute(
            "SELECT feedback_id FROM FEEDBACK WHERE session_id = %s AND reviewer_id = %s",
            (session_id, user_id)
        )
        if cursor.fetchone():
            flash("You have already submitted feedback for this session.", "info")
            return redirect(url_for("sessions_view"))

        cursor.execute(
            """
            INSERT INTO FEEDBACK (session_id, reviewer_id, rating, comment, feedback_date)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (session_id, user_id, rating, comment)
        )
        conn.commit()
        flash("Thank you! Your feedback has been recorded.", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error submitting feedback: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("sessions_view"))


# =====================================================
# ADMIN MANAGEMENT ROUTES
# =====================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = None
    cursor = None
    stats = {}
    chart_requests = {}
    chart_sessions = {}
    chart_categories = {"labels": [], "counts": []}
    recent_verifications = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Overview Stats
        cursor.execute("SELECT COUNT(*) AS cnt FROM `USER`")
        stats["total_users"] = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM SKILL")
        stats["total_skills"] = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM SKILL_CATEGORY")
        stats["total_categories"] = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM SKILL_VERIFICATION WHERE verification_status = 'Pending'")
        stats["pending_verifications"] = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM LEARNING_REQUEST")
        stats["total_requests"] = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM `SESSION`")
        stats["total_sessions"] = cursor.fetchone()["cnt"]

        # Chart 1: Requests by status
        cursor.execute(
            """
            SELECT status, COUNT(*) AS cnt
            FROM LEARNING_REQUEST
            GROUP BY status
            """
        )
        chart_requests = {r["status"]: r["cnt"] for r in cursor.fetchall()}

        # Chart 2: Sessions by status
        cursor.execute(
            """
            SELECT status, COUNT(*) AS cnt
            FROM `SESSION`
            GROUP BY status
            """
        )
        chart_sessions = {r["status"]: r["cnt"] for r in cursor.fetchall()}

        # Chart 3: Skills per category
        cursor.execute(
            """
            SELECT sc.category_name, COUNT(s.skill_id) AS cnt
            FROM SKILL_CATEGORY sc
            LEFT JOIN SKILL s ON sc.category_id = s.category_id
            GROUP BY sc.category_id, sc.category_name
            ORDER BY cnt DESC
            """
        )
        cat_rows = cursor.fetchall()
        chart_categories["labels"] = [r["category_name"] for r in cat_rows]
        chart_categories["counts"] = [r["cnt"] for r in cat_rows]

        # Recent pending verifications preview
        cursor.execute(
            """
            SELECT sv.verification_id, sv.verification_status,
                   u.name AS teacher_name, sk.skill_name, sc.category_name,
                   adm.name AS assigned_admin_name
            FROM SKILL_VERIFICATION sv
            JOIN USER_SKILL us ON sv.user_skill_id = us.user_skill_id
            JOIN `USER` u ON us.user_id = u.user_id
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            JOIN `USER` adm ON sv.admin_id = adm.user_id
            WHERE sv.verification_status = 'Pending'
            ORDER BY sv.verification_id DESC
            LIMIT 5
            """
        )
        recent_verifications = cursor.fetchall()

    except DBError as err:
        flash(f"Database error loading admin dashboard: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        chart_requests=chart_requests,
        chart_sessions=chart_sessions,
        chart_categories=chart_categories,
        recent_verifications=recent_verifications
    )


@app.route("/admin/users")
@admin_required
def admin_users():
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "").strip()

    conn = None
    cursor = None
    users = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT u.user_id, u.name, u.email, u.phone, u.role, u.created_at,
                   (SELECT COUNT(*) FROM USER_SKILL us WHERE us.user_id = u.user_id AND us.skill_type = 'Offering') AS offering_count,
                   (SELECT COUNT(*) FROM USER_SKILL us WHERE us.user_id = u.user_id AND us.skill_type = 'Learning') AS learning_count,
                   (
                       SELECT COUNT(*)
                       FROM `SESSION` s
                       JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id
                       JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id
                       WHERE lr.requester_id = u.user_id OR us.user_id = u.user_id
                   ) AS session_count
            FROM `USER` u
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (u.name LIKE %s OR u.email LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        if role_filter in ("User", "Admin"):
            query += " AND u.role = %s"
            params.append(role_filter)

        query += " ORDER BY u.user_id ASC"
        cursor.execute(query, tuple(params))
        users = cursor.fetchall()

    except DBError as err:
        flash(f"Database error loading users: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "admin/users.html",
        users=users,
        search=search,
        role_filter=role_filter
    )


@app.route("/admin/users/role/<int:user_id>", methods=["POST"])
@admin_required
def admin_toggle_user_role(user_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT user_id, role, name FROM `USER` WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("admin_users"))

        new_role = "User" if user["role"] == "Admin" else "Admin"

        # Prevent demoting self or last admin
        if user["role"] == "Admin" and new_role == "User":
            cursor.execute("SELECT COUNT(*) AS admin_count FROM `USER` WHERE role = 'Admin'")
            admin_count = cursor.fetchone()["admin_count"]
            if admin_count <= 1:
                flash("Cannot demote the last remaining administrator.", "warning")
                return redirect(url_for("admin_users"))

        cursor.execute("UPDATE `USER` SET role = %s WHERE user_id = %s", (new_role, user_id))
        conn.commit()
        flash(f"Updated role for {user['name']} to '{new_role}'.", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error updating role: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_users"))


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot delete your own account while logged in.", "warning")
        return redirect(url_for("admin_users"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT name FROM `USER` WHERE user_id = %s", (user_id,))
        target_user = cursor.fetchone()
        if not target_user:
            flash("User not found.", "danger")
            return redirect(url_for("admin_users"))

        # Strict Rule: Check dependent foreign keys
        # 1. USER_SKILL
        cursor.execute("SELECT COUNT(*) AS cnt FROM USER_SKILL WHERE user_id = %s", (user_id,))
        user_skills_cnt = cursor.fetchone()["cnt"]

        # 2. LEARNING_REQUEST (as requester)
        cursor.execute("SELECT COUNT(*) AS cnt FROM LEARNING_REQUEST WHERE requester_id = %s", (user_id,))
        req_cnt = cursor.fetchone()["cnt"]

        # 3. FEEDBACK (as reviewer)
        cursor.execute("SELECT COUNT(*) AS cnt FROM FEEDBACK WHERE reviewer_id = %s", (user_id,))
        feedback_cnt = cursor.fetchone()["cnt"]

        # 4. SKILL_VERIFICATION (as admin)
        cursor.execute("SELECT COUNT(*) AS cnt FROM SKILL_VERIFICATION WHERE admin_id = %s", (user_id,))
        admin_ver_cnt = cursor.fetchone()["cnt"]

        dependencies = []
        if user_skills_cnt > 0:
            dependencies.append(f"{user_skills_cnt} skill listing(s)")
        if req_cnt > 0:
            dependencies.append(f"{req_cnt} learning request(s)")
        if feedback_cnt > 0:
            dependencies.append(f"{feedback_cnt} feedback record(s)")
        if admin_ver_cnt > 0:
            dependencies.append(f"{admin_ver_cnt} assigned verification(s)")

        if dependencies:
            dep_msg = ", ".join(dependencies)
            flash(
                f"Cannot delete user '{target_user['name']}': foreign key constraints exist ({dep_msg}). "
                "Remove or reassign dependent records first to preserve database integrity.",
                "danger"
            )
            return redirect(url_for("admin_users"))

        cursor.execute("DELETE FROM `USER` WHERE user_id = %s", (user_id,))
        conn.commit()
        flash(f"User '{target_user['name']}' deleted successfully.", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error deleting user: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_users"))


@app.route("/admin/categories", methods=["GET", "POST"])
@admin_required
def admin_categories():
    conn = None
    cursor = None

    if request.method == "POST":
        category_name = request.form.get("category_name", "").strip()
        if not category_name:
            flash("Category name cannot be empty.", "danger")
            return redirect(url_for("admin_categories"))

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT category_id FROM SKILL_CATEGORY WHERE category_name = %s", (category_name,))
            if cursor.fetchone():
                flash("A category with this name already exists.", "warning")
            else:
                cursor.execute("INSERT INTO SKILL_CATEGORY (category_name) VALUES (%s)", (category_name,))
                conn.commit()
                flash(f"Category '{category_name}' created successfully!", "success")
        except DBError as err:
            if conn:
                conn.rollback()
            flash(f"Database error creating category: {err.msg}", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return redirect(url_for("admin_categories"))

    # GET categories
    categories = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT sc.category_id, sc.category_name, COUNT(s.skill_id) AS skill_count
            FROM SKILL_CATEGORY sc
            LEFT JOIN SKILL s ON sc.category_id = s.category_id
            GROUP BY sc.category_id, sc.category_name
            ORDER BY sc.category_name ASC
            """
        )
        categories = cursor.fetchall()
    except DBError as err:
        flash(f"Database error loading categories: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("admin/categories.html", categories=categories)


@app.route("/admin/categories/edit/<int:category_id>", methods=["POST"])
@admin_required
def admin_edit_category(category_id):
    category_name = request.form.get("category_name", "").strip()
    if not category_name:
        flash("Category name cannot be empty.", "danger")
        return redirect(url_for("admin_categories"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE SKILL_CATEGORY SET category_name = %s WHERE category_id = %s",
            (category_name, category_id)
        )
        conn.commit()
        flash("Category updated successfully!", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error updating category: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_categories"))


@app.route("/admin/categories/delete/<int:category_id>", methods=["POST"])
@admin_required
def admin_delete_category(category_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT category_name FROM SKILL_CATEGORY WHERE category_id = %s", (category_id,))
        cat = cursor.fetchone()
        if not cat:
            flash("Category not found.", "danger")
            return redirect(url_for("admin_categories"))

        # Check dependent skills
        cursor.execute("SELECT COUNT(*) AS cnt FROM SKILL WHERE category_id = %s", (category_id,))
        skill_cnt = cursor.fetchone()["cnt"]

        if skill_cnt > 0:
            flash(
                f"Cannot delete category '{cat['category_name']}': {skill_cnt} skills belong to it. "
                "Reassign or delete those skills first.",
                "danger"
            )
            return redirect(url_for("admin_categories"))

        cursor.execute("DELETE FROM SKILL_CATEGORY WHERE category_id = %s", (category_id,))
        conn.commit()
        flash(f"Category '{cat['category_name']}' deleted successfully.", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error deleting category: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_categories"))


@app.route("/admin/skills", methods=["GET", "POST"])
@admin_required
def admin_skills():
    conn = None
    cursor = None

    if request.method == "POST":
        skill_name = request.form.get("skill_name", "").strip()
        category_id = request.form.get("category_id", type=int)

        if not skill_name or not category_id:
            flash("Please provide both skill name and category.", "danger")
            return redirect(url_for("admin_skills"))

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT skill_id FROM SKILL WHERE skill_name = %s", (skill_name,))
            if cursor.fetchone():
                flash("A skill with this name already exists.", "warning")
            else:
                cursor.execute(
                    "INSERT INTO SKILL (skill_name, category_id) VALUES (%s, %s)",
                    (skill_name, category_id)
                )
                conn.commit()
                flash(f"Skill '{skill_name}' created successfully!", "success")
        except DBError as err:
            if conn:
                conn.rollback()
            flash(f"Database error creating skill: {err.msg}", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return redirect(url_for("admin_skills"))

    # GET skills
    skills = []
    categories = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT category_id, category_name FROM SKILL_CATEGORY ORDER BY category_name ASC")
        categories = cursor.fetchall()

        cursor.execute(
            """
            SELECT s.skill_id, s.skill_name, sc.category_id, sc.category_name,
                   (SELECT COUNT(*) FROM USER_SKILL us WHERE us.skill_id = s.skill_id AND us.skill_type = 'Offering') AS offering_count,
                   (SELECT COUNT(*) FROM USER_SKILL us WHERE us.skill_id = s.skill_id AND us.skill_type = 'Learning') AS learning_count
            FROM SKILL s
            JOIN SKILL_CATEGORY sc ON s.category_id = sc.category_id
            ORDER BY sc.category_name ASC, s.skill_name ASC
            """
        )
        skills = cursor.fetchall()
    except DBError as err:
        flash(f"Database error loading skills: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("admin/skills.html", skills=skills, categories=categories)


@app.route("/admin/skills/edit/<int:skill_id>", methods=["POST"])
@admin_required
def admin_edit_skill(skill_id):
    skill_name = request.form.get("skill_name", "").strip()
    category_id = request.form.get("category_id", type=int)

    if not skill_name or not category_id:
        flash("Skill name and category are required.", "danger")
        return redirect(url_for("admin_skills"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE SKILL SET skill_name = %s, category_id = %s WHERE skill_id = %s",
            (skill_name, category_id, skill_id)
        )
        conn.commit()
        flash("Skill updated successfully!", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error updating skill: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_skills"))


@app.route("/admin/skills/delete/<int:skill_id>", methods=["POST"])
@admin_required
def admin_delete_skill(skill_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT skill_name FROM SKILL WHERE skill_id = %s", (skill_id,))
        skill = cursor.fetchone()
        if not skill:
            flash("Skill not found.", "danger")
            return redirect(url_for("admin_skills"))

        # Check dependent USER_SKILL rows
        cursor.execute("SELECT COUNT(*) AS cnt FROM USER_SKILL WHERE skill_id = %s", (skill_id,))
        us_cnt = cursor.fetchone()["cnt"]

        if us_cnt > 0:
            flash(
                f"Cannot delete skill '{skill['skill_name']}': {us_cnt} user(s) currently offer or learn it. "
                "Remove those user skill entries first.",
                "danger"
            )
            return redirect(url_for("admin_skills"))

        cursor.execute("DELETE FROM SKILL WHERE skill_id = %s", (skill_id,))
        conn.commit()
        flash(f"Skill '{skill['skill_name']}' deleted successfully.", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error deleting skill: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_skills"))


@app.route("/admin/verifications")
@admin_required
def admin_verifications():
    status_filter = request.args.get("status", "Pending").strip()

    conn = None
    cursor = None
    verifications = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT sv.verification_id, sv.user_skill_id, sv.verification_status, sv.verification_date,
                   u.user_id AS teacher_id, u.name AS teacher_name, u.email AS teacher_email,
                   sk.skill_name, sc.category_name,
                   adm.user_id AS admin_id, adm.name AS admin_name
            FROM SKILL_VERIFICATION sv
            JOIN USER_SKILL us ON sv.user_skill_id = us.user_skill_id
            JOIN `USER` u ON us.user_id = u.user_id
            JOIN SKILL sk ON us.skill_id = sk.skill_id
            JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id
            JOIN `USER` adm ON sv.admin_id = adm.user_id
            WHERE 1=1
        """
        params = []
        if status_filter in ("Pending", "Verified", "Rejected"):
            query += " AND sv.verification_status = %s"
            params.append(status_filter)

        query += " ORDER BY sv.verification_id DESC"
        cursor.execute(query, tuple(params))
        verifications = cursor.fetchall()

    except DBError as err:
        flash(f"Database error loading verifications: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "admin/verifications.html",
        verifications=verifications,
        selected_status=status_filter
    )


@app.route("/admin/verifications/<int:verification_id>/action", methods=["POST"])
@admin_required
def admin_verify_skill(verification_id):
    acting_admin_id = session["user_id"]
    action = request.form.get("action", "").lower()

    if action not in ("verify", "reject"):
        flash("Invalid verification action.", "danger")
        return redirect(url_for("admin_verifications"))

    new_status = "Verified" if action == "verify" else "Rejected"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Rule: admin_id is updated to the admin who acted
        cursor.execute(
            """
            UPDATE SKILL_VERIFICATION
            SET verification_status = %s, verification_date = NOW(), admin_id = %s
            WHERE verification_id = %s
            """,
            (new_status, acting_admin_id, verification_id)
        )
        conn.commit()
        flash(f"Skill verification marked as {new_status} by {session.get('name')}.", "success")
    except DBError as err:
        if conn:
            conn.rollback()
        flash(f"Database error processing verification: {err.msg}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_verifications"))


# =====================================================
# SQL QUERY CONSOLE (STANDOUT FEATURE)
# =====================================================

SAMPLE_QUERIES = [
    {
        "title": "1. Simple SELECT (Users with Filter & Limit)",
        "category": "Basic Queries",
        "sql": "SELECT user_id, name, email, phone, role, created_at FROM `USER` WHERE role = 'User' ORDER BY name ASC LIMIT 5;"
    },
    {
        "title": "2. INNER JOIN across 4 Tables (Offered Skills with Categories & Tutors)",
        "category": "Joins",
        "sql": "SELECT u.name AS teacher_name, u.email, s.skill_name, sc.category_name FROM USER_SKILL us INNER JOIN `USER` u ON us.user_id = u.user_id INNER JOIN SKILL s ON us.skill_id = s.skill_id INNER JOIN SKILL_CATEGORY sc ON s.category_id = sc.category_id WHERE us.skill_type = 'Offering' ORDER BY sc.category_name, s.skill_name;"
    },
    {
        "title": "3. LEFT JOIN (All Skills and Number of Offering Tutors)",
        "category": "Joins",
        "sql": "SELECT s.skill_name, sc.category_name, COUNT(us.user_skill_id) AS total_tutors FROM SKILL s INNER JOIN SKILL_CATEGORY sc ON s.category_id = sc.category_id LEFT JOIN USER_SKILL us ON s.skill_id = us.skill_id AND us.skill_type = 'Offering' GROUP BY s.skill_id, s.skill_name, sc.category_name ORDER BY total_tutors ASC, s.skill_name ASC;"
    },
    {
        "title": "4. RIGHT JOIN (All Categories with Skill Counts)",
        "category": "Joins",
        "sql": "SELECT sc.category_id, sc.category_name, COUNT(s.skill_id) AS total_skills FROM SKILL s RIGHT JOIN SKILL_CATEGORY sc ON s.category_id = sc.category_id GROUP BY sc.category_id, sc.category_name ORDER BY total_skills DESC;"
    },
    {
        "title": "5. GROUP BY with HAVING (Teachers Offering 2 or More Skills)",
        "category": "Grouping & Aggregates",
        "sql": "SELECT u.user_id, u.name, COUNT(us.skill_id) AS skills_offered FROM `USER` u JOIN USER_SKILL us ON u.user_id = us.user_id WHERE us.skill_type = 'Offering' GROUP BY u.user_id, u.name HAVING COUNT(us.skill_id) >= 2 ORDER BY skills_offered DESC;"
    },
    {
        "title": "6. Aggregates (COUNT, AVG, MIN, MAX Rating per Teacher)",
        "category": "Grouping & Aggregates",
        "sql": "SELECT u.user_id, u.name AS teacher_name, COUNT(f.feedback_id) AS feedback_count, ROUND(AVG(f.rating), 2) AS average_rating, MIN(f.rating) AS min_rating, MAX(f.rating) AS max_rating FROM FEEDBACK f JOIN `SESSION` s ON f.session_id = s.session_id JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id JOIN `USER` u ON us.user_id = u.user_id WHERE f.reviewer_id = lr.requester_id GROUP BY u.user_id, u.name ORDER BY average_rating DESC;"
    },
    {
        "title": "7. Subquery with IN (Users who Sent at least one Accepted Request)",
        "category": "Subqueries",
        "sql": "SELECT user_id, name, email FROM `USER` WHERE user_id IN (SELECT requester_id FROM LEARNING_REQUEST WHERE status = 'Accepted');"
    },
    {
        "title": "8. Subquery with NOT EXISTS (Users who have Never Offered any Skill)",
        "category": "Subqueries",
        "sql": "SELECT u.user_id, u.name, u.email FROM `USER` u WHERE NOT EXISTS (SELECT 1 FROM USER_SKILL us WHERE us.user_id = u.user_id AND us.skill_type = 'Offering');"
    },
    {
        "title": "9. Correlated Subquery (Requests with More than 1 Session)",
        "category": "Subqueries",
        "sql": "SELECT lr.request_id, u.name AS requester, (SELECT COUNT(*) FROM `SESSION` s WHERE s.request_id = lr.request_id) AS session_count FROM LEARNING_REQUEST lr JOIN `USER` u ON lr.requester_id = u.user_id WHERE (SELECT COUNT(*) FROM `SESSION` s WHERE s.request_id = lr.request_id) > 1;"
    },
    {
        "title": "10. Self Join / Intersect (Users who BOTH Offer and Learn Skills)",
        "category": "Advanced Joins",
        "sql": "SELECT DISTINCT u.user_id, u.name, u.email FROM `USER` u JOIN USER_SKILL us_off ON u.user_id = us_off.user_id AND us_off.skill_type = 'Offering' JOIN USER_SKILL us_lrn ON u.user_id = us_lrn.user_id AND us_lrn.skill_type = 'Learning' ORDER BY u.name;"
    },
    {
        "title": "11. Top-Rated Teachers (Leaderboard with Review Summary)",
        "category": "Analytics",
        "sql": "SELECT u.user_id, u.name AS teacher_name, ROUND(AVG(f.rating), 2) AS rating, COUNT(f.feedback_id) AS total_reviews FROM `USER` u JOIN USER_SKILL us ON u.user_id = us.user_id JOIN LEARNING_REQUEST lr ON us.user_skill_id = lr.user_skill_id JOIN `SESSION` s ON lr.request_id = s.request_id JOIN FEEDBACK f ON s.session_id = f.session_id WHERE f.reviewer_id = lr.requester_id GROUP BY u.user_id, u.name ORDER BY rating DESC, total_reviews DESC;"
    },
    {
        "title": "12. Skills with No Offering Users (Unmet Demand)",
        "category": "Analytics",
        "sql": "SELECT s.skill_id, s.skill_name, sc.category_name FROM SKILL s JOIN SKILL_CATEGORY sc ON s.category_id = sc.category_id WHERE s.skill_id NOT IN (SELECT skill_id FROM USER_SKILL WHERE skill_type = 'Offering');"
    },
    {
        "title": "13. Derivation Join (Sessions with Learner, Teacher, Skill & Time)",
        "category": "Derivations",
        "sql": "SELECT s.session_id, s.session_date, s.start_time, s.end_time, s.status, lrn.name AS learner_name, tch.name AS teacher_name, sk.skill_name FROM `SESSION` s JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id JOIN `USER` lrn ON lr.requester_id = lrn.user_id JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id JOIN `USER` tch ON us.user_id = tch.user_id JOIN SKILL sk ON us.skill_id = sk.skill_id ORDER BY s.session_date DESC;"
    },
    {
        "title": "14. Verification Queue (Pending Verifications with Assigned Admin)",
        "category": "Administration",
        "sql": "SELECT sv.verification_id, u.name AS teacher_name, s.skill_name, sv.verification_status, adm.name AS assigned_admin FROM SKILL_VERIFICATION sv JOIN USER_SKILL us ON sv.user_skill_id = us.user_skill_id JOIN `USER` u ON us.user_id = u.user_id JOIN SKILL s ON us.skill_id = s.skill_id JOIN `USER` adm ON sv.admin_id = adm.user_id WHERE sv.verification_status = 'Pending';"
    },
    {
        "title": "15. UNION Example (User Activity Stream: Offerings vs Requests)",
        "category": "Set Operations",
        "sql": "SELECT u.name AS user_name, 'Offered Skill' AS activity_type, s.skill_name AS detail, us.user_skill_id AS ref_id FROM USER_SKILL us JOIN `USER` u ON us.user_id = u.user_id JOIN SKILL s ON us.skill_id = s.skill_id WHERE us.skill_type = 'Offering' UNION SELECT u.name AS user_name, 'Sent Request' AS activity_type, s.skill_name AS detail, lr.request_id AS ref_id FROM LEARNING_REQUEST lr JOIN `USER` u ON lr.requester_id = u.user_id JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id JOIN SKILL s ON us.skill_id = s.skill_id ORDER BY user_name ASC, activity_type ASC;"
    },
    {
        "title": "16. View-style Complex Aggregation (Learning Request Full Summary)",
        "category": "Complex Analytics",
        "sql": "SELECT lr.request_id, lr.request_date, lr.status AS request_status, req.name AS requester_name, tch.name AS teacher_name, sk.skill_name, sc.category_name, COUNT(s.session_id) AS total_sessions FROM LEARNING_REQUEST lr JOIN `USER` req ON lr.requester_id = req.user_id JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id JOIN `USER` tch ON us.user_id = tch.user_id JOIN SKILL sk ON us.skill_id = sk.skill_id JOIN SKILL_CATEGORY sc ON sk.category_id = sc.category_id LEFT JOIN `SESSION` s ON lr.request_id = s.request_id GROUP BY lr.request_id, lr.request_date, lr.status, req.name, tch.name, sk.skill_name, sc.category_name ORDER BY lr.request_id ASC;"
    },
    {
        "title": "17. Pattern Matching & Wildcards (LIKE % and _)",
        "category": "Filtering & Patterns",
        "sql": "SELECT user_id, name, email, phone FROM `USER` WHERE email LIKE '%@gmail.com' AND phone LIKE '91%' ORDER BY name ASC;"
    },
    {
        "title": "18. Conditional Logic (CASE WHEN THEN Teacher Tier)",
        "category": "Conditional Logic",
        "sql": "SELECT u.name AS teacher_name, ROUND(AVG(f.rating), 2) AS avg_rating, COUNT(f.feedback_id) AS total_reviews, CASE WHEN AVG(f.rating) >= 4.8 THEN 'Elite Master' WHEN AVG(f.rating) >= 4.0 THEN 'Proficient Mentor' ELSE 'Developing Tutor' END AS tutor_tier FROM FEEDBACK f JOIN `SESSION` s ON f.session_id = s.session_id JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id JOIN `USER` u ON us.user_id = u.user_id WHERE f.reviewer_id = lr.requester_id GROUP BY u.user_id, u.name ORDER BY avg_rating DESC;"
    },
    {
        "title": "19. Date & Time Arithmetic (Duration in Minutes with TIMEDIFF)",
        "category": "Date & Time Functions",
        "sql": "SELECT s.session_id, s.session_date, s.start_time, s.end_time, s.status, TIMESTAMPDIFF(MINUTE, s.start_time, s.end_time) AS duration_minutes, DATEDIFF(CURDATE(), s.session_date) AS days_since_session, sk.skill_name FROM `SESSION` s JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id JOIN SKILL sk ON us.skill_id = sk.skill_id ORDER BY s.session_date DESC;"
    },
    {
        "title": "20. Two-Way Matchmaking (Users who can Swap Skills Directly)",
        "category": "Relational Matchmaking",
        "sql": "SELECT u1.name AS user_a, s1.skill_name AS a_teaches_b, u2.name AS user_b, s2.skill_name AS b_teaches_a FROM USER_SKILL us1_off JOIN `USER` u1 ON us1_off.user_id = u1.user_id JOIN SKILL s1 ON us1_off.skill_id = s1.skill_id JOIN USER_SKILL us2_lrn ON us1_off.skill_id = us2_lrn.skill_id AND us2_lrn.skill_type = 'Learning' JOIN `USER` u2 ON us2_lrn.user_id = u2.user_id JOIN USER_SKILL us2_off ON u2.user_id = us2_off.user_id AND us2_off.skill_type = 'Offering' JOIN SKILL s2 ON us2_off.skill_id = s2.skill_id JOIN USER_SKILL us1_lrn ON us2_off.skill_id = us1_lrn.skill_id AND us1_lrn.user_id = u1.user_id AND us1_lrn.skill_type = 'Learning' WHERE us1_off.skill_type = 'Offering' AND u1.user_id < u2.user_id;"
    },
    {
        "title": "21. Window Functions (DENSE_RANK of Skills per Category)",
        "category": "Window Functions",
        "sql": "SELECT sc.category_name, s.skill_name, COUNT(us.user_skill_id) AS tutor_count, DENSE_RANK() OVER (PARTITION BY sc.category_id ORDER BY COUNT(us.user_skill_id) DESC) AS rank_in_category FROM SKILL_CATEGORY sc JOIN SKILL s ON sc.category_id = s.category_id LEFT JOIN USER_SKILL us ON s.skill_id = us.skill_id AND us.skill_type = 'Offering' GROUP BY sc.category_id, sc.category_name, s.skill_id, s.skill_name ORDER BY sc.category_name, rank_in_category;"
    },
    {
        "title": "22. N-th Highest Record (2nd Most Active Teacher by Sessions)",
        "category": "Subqueries",
        "sql": "SELECT u.user_id, u.name, COUNT(s.session_id) AS total_sessions FROM `USER` u JOIN USER_SKILL us ON u.user_id = us.user_id JOIN LEARNING_REQUEST lr ON us.user_skill_id = lr.user_skill_id JOIN `SESSION` s ON lr.request_id = s.request_id GROUP BY u.user_id, u.name ORDER BY total_sessions DESC LIMIT 1 OFFSET 1;"
    },
    {
        "title": "23. String Functions (CONCAT, UPPER, Character Length)",
        "category": "String Functions",
        "sql": "SELECT user_id, UPPER(name) AS uppercase_name, CONCAT(name, ' <', email, '>') AS formatted_contact, LENGTH(phone) AS phone_digit_count, role FROM `USER` ORDER BY name ASC;"
    },
    {
        "title": "24. Correlated Aggregate (Teachers Above Overall Platform Average)",
        "category": "Advanced Subqueries",
        "sql": "SELECT u.name AS teacher_name, ROUND(AVG(f.rating), 2) AS teacher_avg FROM FEEDBACK f JOIN `SESSION` s ON f.session_id = s.session_id JOIN LEARNING_REQUEST lr ON s.request_id = lr.request_id JOIN USER_SKILL us ON lr.user_skill_id = us.user_skill_id JOIN `USER` u ON us.user_id = u.user_id WHERE f.reviewer_id = lr.requester_id GROUP BY u.user_id, u.name HAVING AVG(f.rating) >= (SELECT AVG(rating) FROM FEEDBACK) ORDER BY teacher_avg DESC;"
    },
    {
        "title": "25. NULL Analysis (Unverified Offerings & Pending Admin Actions)",
        "category": "NULL Handling",
        "sql": "SELECT us.user_skill_id, u.name AS teacher_name, s.skill_name, sv.verification_status, CASE WHEN sv.verification_id IS NULL THEN 'Never Submitted' WHEN sv.verification_date IS NULL THEN 'Pending Admin Review' ELSE 'Reviewed and Decided' END AS audit_stage FROM USER_SKILL us JOIN `USER` u ON us.user_id = u.user_id JOIN SKILL s ON us.skill_id = s.skill_id LEFT JOIN SKILL_VERIFICATION sv ON us.user_skill_id = sv.user_skill_id WHERE us.skill_type = 'Offering' ORDER BY audit_stage, teacher_name;"
    }
]


@app.route("/sql")
@login_required
def sql_console():
    is_admin = session.get("role") == "Admin"
    conn = None
    cursor = None
    tables_schema = {}

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get list of tables in skill_swap_db
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name ASC
            """,
            (DB_NAME,)
        )
        table_rows = cursor.fetchall()

        for t in table_rows:
            tbl_name = t["TABLE_NAME"]
            cursor.execute(
                """
                SELECT c.column_name, c.column_type, c.is_nullable, c.column_key, c.column_default,
                       k.referenced_table_name, k.referenced_column_name
                FROM information_schema.columns c
                LEFT JOIN information_schema.key_column_usage k
                  ON c.table_schema = k.table_schema
                 AND c.table_name = k.table_name
                 AND c.column_name = k.column_name
                 AND k.referenced_table_name IS NOT NULL
                WHERE c.table_schema = %s AND c.table_name = %s
                ORDER BY c.ordinal_position ASC
                """,
                (DB_NAME, tbl_name)
            )
            tables_schema[tbl_name] = cursor.fetchall()

    except DBError as err:
        flash(f"Could not load schema explorer: {err.msg}", "warning")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "sql_console.html",
        is_admin=is_admin,
        tables_schema=tables_schema,
        sample_queries=SAMPLE_QUERIES
    )


@app.route("/sql/run", methods=["POST"])
@login_required
def sql_run():
    data = request.get_json(silent=True) or {}
    raw_sql = data.get("sql", "").strip()
    write_mode = bool(data.get("write_mode", False))
    is_admin = session.get("role") == "Admin"

    if not raw_sql:
        return jsonify({"success": False, "error": "No SQL statement provided."}), 400

    # Non-admins can NEVER use write mode
    if write_mode and not is_admin:
        return jsonify({"success": False, "error": "Write mode is restricted to administrators."}), 403

    statements = split_sql_statements(raw_sql)
    if not statements:
        return jsonify({"success": False, "error": "No valid SQL statements found."}), 400

    # Strictly forbidden keywords across ALL modes & roles
    BLOCKED_KEYWORDS = [
        "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
        "LOAD_FILE", "INTO OUTFILE", "INTO DUMPFILE", "RENAME",
        "CALL", "EXECUTE", "PREPARE"
    ]
    FORBIDDEN_DATABASES = ["mysql.", "sys.", "performance_schema."]

    ALLOWED_SAFE_VERBS = ("SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN")
    ALLOWED_WRITE_VERBS = ("INSERT", "UPDATE", "DELETE")

    parsed_statements = []
    for stmt in statements:
        clean_stmt = stmt.strip()
        if not clean_stmt:
            continue

        # Extract leading keyword
        tokens = re.findall(r'[A-Za-z_]+', clean_stmt)
        if not tokens:
            continue
        first_token = tokens[0].upper()

        # Check blocklist
        for kw in BLOCKED_KEYWORDS:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, clean_stmt, re.IGNORECASE):
                return jsonify({
                    "success": False,
                    "error": f"Security violation: The '{kw}' statement is strictly forbidden in the SQL Console.",
                    "statement": clean_stmt
                }), 400

        # Check external databases
        for fdb in FORBIDDEN_DATABASES:
            if fdb in clean_stmt.lower():
                return jsonify({
                    "success": False,
                    "error": f"Security violation: Access to system database '{fdb}' is prohibited.",
                    "statement": clean_stmt
                }), 400

        # Validate by mode
        if not write_mode:
            if first_token not in ALLOWED_SAFE_VERBS:
                return jsonify({
                    "success": False,
                    "error": f"Safe Mode only allows SELECT, SHOW, DESCRIBE, and EXPLAIN statements. Found '{first_token}'. Enable Write Mode (Admin only) to run DML statements.",
                    "statement": clean_stmt
                }), 400
        else:
            if first_token not in ALLOWED_SAFE_VERBS and first_token not in ALLOWED_WRITE_VERBS:
                return jsonify({
                    "success": False,
                    "error": f"Statement type '{first_token}' is not permitted.",
                    "statement": clean_stmt
                }), 400

        parsed_statements.append((clean_stmt, first_token))

    if not parsed_statements:
        return jsonify({"success": False, "error": "No executable statements."}), 400

    conn = None
    cursor = None
    results = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for stmt, verb in parsed_statements:
            start_t = time.perf_counter()
            cursor.execute(stmt)
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

            if verb in ALLOWED_SAFE_VERBS or cursor.with_rows:
                # Capped at 1000 rows
                rows_data = cursor.fetchmany(1001)
                capped = len(rows_data) > 1000
                if capped:
                    rows_data = rows_data[:1000]

                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                # Format JSON serializable rows
                formatted_rows = []
                for row in rows_data:
                    row_list = []
                    for val in row:
                        if val is None:
                            row_list.append(None)
                        elif isinstance(val, (date, datetime)):
                            row_list.append(val.isoformat())
                        elif isinstance(val, timedelta):
                            # Format time
                            total_secs = int(val.total_seconds())
                            hours = total_secs // 3600
                            minutes = (total_secs % 3600) // 60
                            seconds = total_secs % 60
                            row_list.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                        elif isinstance(val, Decimal):
                            row_list.append(float(val))
                        elif isinstance(val, bytes):
                            row_list.append(val.decode("utf-8", errors="replace"))
                        else:
                            row_list.append(val)
                    formatted_rows.append(row_list)

                results.append({
                    "statement": stmt,
                    "type": "select",
                    "columns": columns,
                    "rows": formatted_rows,
                    "row_count": len(formatted_rows),
                    "capped": capped,
                    "execution_time_ms": elapsed_ms
                })
            else:
                affected = cursor.rowcount
                last_id = cursor.lastrowid
                results.append({
                    "statement": stmt,
                    "type": "dml",
                    "affected_rows": affected,
                    "last_insert_id": last_id,
                    "execution_time_ms": elapsed_ms
                })

        if write_mode:
            conn.commit()

        return jsonify({"success": True, "results": results})

    except DBError as err:
        if conn and write_mode:
            conn.rollback()
        return jsonify({
            "success": False,
            "error": f"MySQL Error {err.errno} ({err.sqlstate}): {err.msg}",
            "statement": stmt
        }), 400
    except Exception as ex:
        if conn and write_mode:
            conn.rollback()
        return jsonify({
            "success": False,
            "error": f"Server Error: {str(ex)}"
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/sql/reset", methods=["POST"])
@admin_required
def sql_reset_database():
    """
    Restores the database by running schema.sql and seed.sql from scratch.
    Opens a connection WITHOUT selecting a database, as required.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection(use_database=False)
        cursor = conn.cursor()

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        # Read schema.sql
        with open(os.path.join(BASE_DIR, "schema.sql"), "r", encoding="utf-8") as f:
            schema_content = f.read()
        schema_stmts = split_sql_statements(schema_content)

        for stmt in schema_stmts:
            cursor.execute(stmt)
            if cursor.with_rows:
                cursor.fetchall()

        # Read seed.sql
        with open(os.path.join(BASE_DIR, "seed.sql"), "r", encoding="utf-8") as f:
            seed_content = f.read()
        seed_stmts = split_sql_statements(seed_content)

        for stmt in seed_stmts:
            cursor.execute(stmt)
            if cursor.with_rows:
                cursor.fetchall()

        conn.commit()
        return jsonify({
            "success": True,
            "message": "Database successfully reset to initial schema and seed data!"
        })

    except Exception as ex:
        if conn:
            conn.rollback()
        return jsonify({
            "success": False,
            "error": f"Failed to reset database: {str(ex)}"
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =====================================================
# ERROR HANDLERS
# =====================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("errors/500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
