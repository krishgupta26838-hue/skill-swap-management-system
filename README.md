# Skill Swap Management System

A full-stack, demo-ready web application built for a Database Management Systems (DBMS) course project. It enables peer-to-peer knowledge exchange where students can offer skills they excel at, request to learn skills from others, schedule learning sessions, leave ratings and feedback, and have their proficiencies verified by administrators.

---

## Tech Stack & Architecture

- **Backend**: Python 3.11+ with **Flask** (`>=3.1.0,<4.0.0`)
- **Database**: **MySQL 8.0+** accessed using **mysql-connector-python** (`>=9.0.0,<10.0.0`)
- **Frontend**: Jinja2 Templates + **Bootstrap 5.3.3** (CDN) + Vanilla JavaScript
- **Security**: Password hashing via `werkzeug.security` (`generate_password_hash`, `check_password_hash`), session-based authentication with role-based access control (`User` and `Admin`).
- **Data Access**: **Raw SQL with parameterized queries (`%s`)**. No ORM (no SQLAlchemy) to ensure every relational query, join, and transaction is transparent and explainable during a DBMS project viva.
- **Reserved Keyword Handling**: The MySQL reserved words `` `USER` `` and `` `SESSION` `` are wrapped in backticks across all SQL queries.

---

## Relational Schema & Compliance

The database `skill_swap_db` adheres strictly to the 8-table relational model without modification:

1. **`USER`** (`user_id`, `name`, `email` [UNIQUE], `password`, `phone`, `created_at`, `role` [ENUM: 'User', 'Admin'])
2. **`SKILL_CATEGORY`** (`category_id`, `category_name` [UNIQUE])
3. **`SKILL`** (`skill_id`, `skill_name` [UNIQUE], `category_id` FK &rarr; `SKILL_CATEGORY`)
4. **`USER_SKILL`** (`user_skill_id`, `user_id` FK &rarr; `USER`, `skill_id` FK &rarr; `SKILL`, `skill_type` [ENUM: 'Offering', 'Learning'], `UNIQUE(user_id, skill_id, skill_type)`)
5. **`LEARNING_REQUEST`** (`request_id`, `requester_id` FK &rarr; `USER`, `user_skill_id` FK &rarr; `USER_SKILL`, `request_date`, `status` [ENUM: 'Pending', 'Accepted', 'Rejected', 'Cancelled'], `UNIQUE(requester_id, user_skill_id)`)
6. **`SESSION`** (`session_id`, `request_id` FK &rarr; `LEARNING_REQUEST`, `session_date`, `start_time`, `end_time`, `status` [ENUM: 'Scheduled', 'Completed', 'Cancelled'], `CHECK(end_time > start_time)`)
7. **`FEEDBACK`** (`feedback_id`, `session_id` FK &rarr; `SESSION`, `reviewer_id` FK &rarr; `USER`, `rating` [CHECK 1-5], `comment`, `feedback_date`, `UNIQUE(session_id, reviewer_id)`)
8. **`SKILL_VERIFICATION`** (`verification_id`, `user_skill_id` FK [UNIQUE], `admin_id` FK &rarr; `USER` [NOT NULL], `verification_status` [ENUM: 'Pending', 'Verified', 'Rejected'], `verification_date`)

### Strict ER Diagram Rules Enforced in Code:
- **Participant Derivation**: `SESSION` and `FEEDBACK` contain no redundant teacher/learner columns. The learner is derived from `LEARNING_REQUEST.requester_id` and the teacher is derived from `USER_SKILL.user_id`.
- **Target Offerings Only**: Learning requests can only target `USER_SKILL` entries with `skill_type = 'Offering'`. Users are blocked from requesting their own listings.
- **Re-requesting Logic**: Because of `UNIQUE(requester_id, user_skill_id)`, re-sending a request that was previously `Cancelled` or `Rejected` updates the existing row back to `Pending` and refreshes `request_date`.
- **Sessions on Accepted Swaps**: Sessions can only be scheduled for requests with status `Accepted`, enforcing `end_time > start_time` and ensuring dates are not in the past.
- **Feedback Integrity**: Feedback is only allowed on sessions marked `Completed`, submitted strictly by one of the two participants, capped at 1 feedback per `(session, reviewer)`.
- **Skill Verification Auto-Assignment**: `SKILL_VERIFICATION.admin_id` is `NOT NULL`. When a user requests verification for an offered skill, the system auto-assigns the Admin with the fewest pending verifications. Any admin who later reviews the request has their admin ID recorded as the acting reviewer.
- **No Cascade Deletion Safety**: Since `ON DELETE CASCADE` is intentionally omitted to maintain audit integrity, the application validates foreign key dependencies before deleting any user, skill, category, or listing, presenting a friendly message detailing any dependent records.

---

## Demo Login Credentials

All passwords have been securely hashed using Werkzeug (`scrypt`/`pbkdf2`):

| Role | Name | Email | Password | Details |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | Aarav Sharma | `aarav.admin@skillswap.com` | `Admin@123` | Lead Administrator |
| **Admin** | Pooja Patel | `pooja.admin@skillswap.com` | `Admin@123` | Secondary Administrator |
| **User (Teacher)** | Rahul Verma | `rahul@gmail.com` | `User@123` | Offers Python & MySQL (Verified) |
| **User (Teacher)** | Ananya Iyer | `ananya@gmail.com` | `User@123` | Offers UI/UX & Graphic Design (Verified) |
| **User (Teacher)** | Rohan Mehta | `rohan@gmail.com` | `User@123` | Offers Acoustic Guitar (Verified) |
| **User** | Sneha Reddy | `sneha@gmail.com` | `User@123` | Offers Conversational Spanish |
| **User** | Vikram Singh | `vikram@gmail.com` | `User@123` | Offers Web Dev & Machine Learning |
| **User** | Priya Nair | `priya@gmail.com` | `User@123` | Offers Hatha Yoga |
| **User** | Amit Joshi | `amit@gmail.com` | `User@123` | Offers Digital Marketing & SEO |
| **User** | Divya Kapoor | `divya@gmail.com` | `User@123` | Offers Keyboard & Piano |
| **User** | Karan Malhotra | `karan@gmail.com` | `User@123` | Offers Video Editing |
| **User** | Meera Sen | `meera@gmail.com` | `User@123` | Offers French for Beginners |

---

## Setup & Installation

### 1. Prerequisites
- Python 3.11+
- MySQL Server 8.0+ running locally (default port: `3306`)

### 2. Clone / Open Project Directory
```bash
cd skill_swap_project
```

### 3. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Initialize the Database & Seed Sample Data

Run the database scripts using the MySQL command line client:

**Windows (PowerShell / Command Prompt):**
```powershell
Get-Content schema.sql | mysql -u root -p
Get-Content seed.sql | mysql -u root -p
```
*Or using standard cmd:*
```cmd
mysql -u root -p < schema.sql
mysql -u root -p < seed.sql
```

**macOS / Linux:**
```bash
mysql -u root -p < schema.sql
mysql -u root -p < seed.sql
```

### 6. Environment Configuration

Create or update the `.env` file in the project root directory:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=skill_swap_db
FLASK_SECRET_KEY=dev-skillswap-secret-key-course-project-2026
```

*(Alternatively, set environment variables directly in your terminal):*

**Windows (PowerShell):**
```powershell
$env:DB_HOST="localhost"
$env:DB_USER="root"
$env:DB_PASSWORD="your_mysql_password"
$env:DB_NAME="skill_swap_db"
$env:FLASK_SECRET_KEY="dev-skillswap-secret-key-course-project-2026"
```

**macOS / Linux:**
```bash
export DB_HOST="localhost"
export DB_USER="root"
export DB_PASSWORD="your_mysql_password"
export DB_NAME="skill_swap_db"
export FLASK_SECRET_KEY="dev-skillswap-secret-key-course-project-2026"
```

### 7. Run the Application
```bash
python app.py
```

Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Standout Feature: SQL Query Console

Located in the top navigation bar (`/sql`), this interactive query console is built specifically for DBMS project demonstrations and oral examinations (vivas):

1. **Interactive Code Editor**: Syntax-highlighted SQL textarea powered by CodeMirror 5 with `Ctrl+Enter` execution shortcut.
2. **Schema Explorer**: Real-time inspection of all 8 tables reading directly from `information_schema.columns` and `information_schema.key_column_usage` showing primary keys (`PK`) and foreign keys (`FK`). Clicking any table inserts `SELECT * FROM \`table\` LIMIT 10;`.
3. **16 Pre-configured Viva Sample Queries**:
   - Simple `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`
   - `INNER JOIN` across 4 tables (`USER`, `USER_SKILL`, `SKILL`, `SKILL_CATEGORY`)
   - `LEFT JOIN` (Skills with tutor counts, including 0-tutor skills)
   - `RIGHT JOIN` (All categories with skill counts)
   - `GROUP BY` with `HAVING` (Teachers offering &ge; 2 skills)
   - Aggregate functions (`COUNT`, `AVG`, `MIN`, `MAX` rating summaries)
   - Subqueries with `IN` and correlated subqueries with `NOT EXISTS`
   - Self-join / intersection queries ("Users who both offer and learn skills")
   - Leaderboard analytics ("Top-rated teachers")
   - Derivation queries ("Session details with learner, teacher, and skill names")
   - `UNION` set operations ("Activity stream combining offerings and sent requests")
   - View-style aggregated analytics
4. **Execution Safety**:
   - Safe Mode (default for all users): Allows only `SELECT`, `SHOW`, `DESCRIBE`, and `EXPLAIN`.
   - Admin Write Mode: Protected by a confirmation dialog, allows `INSERT`, `UPDATE`, and `DELETE`.
   - Hardcoded Security Guard: Blocks `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `LOAD_FILE`, `INTO OUTFILE`, etc.
   - Result capping at 1,000 rows.
5. **Real-Time Client-Side Table Rendering**:
   - AJAX `/sql/run` rendering on the same page without reloads.
   - Millisecond execution timers and affected row counters.
   - Distinguishes SQL `NULL` values in styled italics.
   - One-click **Export to CSV**.
   - Query history stored in `localStorage` (last 20 queries).
6. **One-Click Database Reset**:
   - Dedicated Admin-only button that re-runs `schema.sql` and `seed.sql` on a fresh connection to instantly restore the demonstration dataset.

---

## Project Structure

```
skill_swap_project/
├── app.py                      # Flask backend, DB connection, routes, business logic
├── schema.sql                  # Exact relational schema (8 normalized tables)
├── seed.sql                    # Seed dataset (12 users, 20 skills, 26 listings, requests, sessions, feedback, verifications)
├── requirements.txt            # Python dependencies (Flask, mysql-connector-python, python-dotenv)
├── .env                        # Database connection environment configuration
├── README.md                   # Full documentation, setup instructions, and demo credentials
├── static/
│   ├── css/
│   │   └── style.css           # Modern custom stylesheet, responsive cards, status badges
│   └── js/
│       ├── main.js             # General UI interactivity (star rating picker, auto-dismiss alerts, confirmation modals)
│       └── sql_console.js      # CodeMirror controller, AJAX query runner, schema explorer, CSV export, history
└── templates/
    ├── base.html               # Shared layout, navbar, notification badges, flash messages, footer
    ├── sql_console.html        # Interactive SQL query console page
    ├── auth/
    │   ├── login.html          # Login page with demo credentials helper
    │   └── register.html       # User registration page
    ├── user/
    │   ├── dashboard.html      # User dashboard with metric cards and recent activity
    │   ├── profile.html        # Profile viewer/editor and student testimonials
    │   ├── my_skills.html      # Portfolio of offered and learning skills + verification requests
    │   ├── browse.html         # Search & filter tutors, skill cards, verified badges
    │   ├── requests.html       # Sent & received swap request management
    │   └── sessions.html       # Session scheduling, completion, and feedback modal
    ├── admin/
    │   ├── dashboard.html      # Admin dashboard with Chart.js analytics
    │   ├── users.html          # User account management & safe deletion checks
    │   ├── categories.html     # Category CRUD
    │   ├── skills.html         # Skill CRUD
    │   └── verifications.html  # Skill verification queue (approve / reject)
    └── errors/
        ├── 404.html            # Custom 404 Not Found error page
        └── 500.html            # Custom 500 Internal Server Error page
```
