-- =====================================================
-- SKILL SWAP MANAGEMENT SYSTEM
-- FINAL DATABASE SCRIPT
-- =====================================================

-- 1. CREATE DATABASE
DROP DATABASE IF EXISTS skill_swap_db;
CREATE DATABASE skill_swap_db;
USE skill_swap_db;

-- =====================================================
-- 2. USER TABLE
-- =====================================================

CREATE TABLE `USER` (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(15),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    role ENUM('User', 'Admin') NOT NULL DEFAULT 'User'
);

-- =====================================================
-- 3. SKILL_CATEGORY TABLE
-- =====================================================

CREATE TABLE SKILL_CATEGORY (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) UNIQUE NOT NULL
);

-- =====================================================
-- 4. SKILL TABLE
-- =====================================================

CREATE TABLE SKILL (
    skill_id INT PRIMARY KEY AUTO_INCREMENT,
    skill_name VARCHAR(100) UNIQUE NOT NULL,
    category_id INT NOT NULL,

    CONSTRAINT fk_skill_category
        FOREIGN KEY (category_id)
        REFERENCES SKILL_CATEGORY(category_id)
);

-- =====================================================
-- 5. USER_SKILL TABLE
-- =====================================================

CREATE TABLE USER_SKILL (
    user_skill_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    skill_id INT NOT NULL,
    skill_type ENUM('Offering', 'Learning') NOT NULL,

    CONSTRAINT uq_user_skill_type
        UNIQUE (user_id, skill_id, skill_type),

    CONSTRAINT fk_user_skill_user
        FOREIGN KEY (user_id)
        REFERENCES `USER`(user_id),

    CONSTRAINT fk_user_skill_skill
        FOREIGN KEY (skill_id)
        REFERENCES SKILL(skill_id)
);

-- =====================================================
-- 6. LEARNING_REQUEST TABLE
-- =====================================================

CREATE TABLE LEARNING_REQUEST (
    request_id INT PRIMARY KEY AUTO_INCREMENT,
    requester_id INT NOT NULL,
    user_skill_id INT NOT NULL,
    request_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM(
        'Pending',
        'Accepted',
        'Rejected',
        'Cancelled'
    ) NOT NULL DEFAULT 'Pending',

    CONSTRAINT uq_requester_listing
        UNIQUE (requester_id, user_skill_id),

    CONSTRAINT fk_request_requester
        FOREIGN KEY (requester_id)
        REFERENCES `USER`(user_id),

    CONSTRAINT fk_request_user_skill
        FOREIGN KEY (user_skill_id)
        REFERENCES USER_SKILL(user_skill_id)
);

-- =====================================================
-- 7. SESSION TABLE
-- =====================================================

CREATE TABLE `SESSION` (
    session_id INT PRIMARY KEY AUTO_INCREMENT,
    request_id INT NOT NULL,
    session_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status ENUM(
        'Scheduled',
        'Completed',
        'Cancelled'
    ) NOT NULL DEFAULT 'Scheduled',

    CONSTRAINT chk_session_time
        CHECK (end_time > start_time),

    CONSTRAINT fk_session_request
        FOREIGN KEY (request_id)
        REFERENCES LEARNING_REQUEST(request_id)
);

-- =====================================================
-- 8. FEEDBACK TABLE
-- =====================================================

CREATE TABLE FEEDBACK (
    feedback_id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    reviewer_id INT NOT NULL,
    rating INT NOT NULL,
    comment TEXT,
    feedback_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_rating
        CHECK (rating BETWEEN 1 AND 5),

    CONSTRAINT uq_session_reviewer
        UNIQUE (session_id, reviewer_id),

    CONSTRAINT fk_feedback_session
        FOREIGN KEY (session_id)
        REFERENCES `SESSION`(session_id),

    CONSTRAINT fk_feedback_reviewer
        FOREIGN KEY (reviewer_id)
        REFERENCES `USER`(user_id)
);

-- =====================================================
-- 9. SKILL_VERIFICATION TABLE
-- =====================================================

CREATE TABLE SKILL_VERIFICATION (
    verification_id INT PRIMARY KEY AUTO_INCREMENT,
    user_skill_id INT NOT NULL UNIQUE,
    admin_id INT NOT NULL,
    verification_status ENUM(
        'Pending',
        'Verified',
        'Rejected'
    ) NOT NULL DEFAULT 'Pending',
    verification_date TIMESTAMP NULL DEFAULT NULL,

    CONSTRAINT fk_verification_user_skill
        FOREIGN KEY (user_skill_id)
        REFERENCES USER_SKILL(user_skill_id),

    CONSTRAINT fk_verification_admin
        FOREIGN KEY (admin_id)
        REFERENCES `USER`(user_id)
);

-- =====================================================
-- 10. DISPLAY ALL TABLES
-- =====================================================

SHOW TABLES;

-- =====================================================
-- 11. CHECK TABLE STRUCTURES
-- =====================================================

DESCRIBE `USER`;
DESCRIBE SKILL_CATEGORY;
DESCRIBE SKILL;
DESCRIBE USER_SKILL;
DESCRIBE LEARNING_REQUEST;
DESCRIBE `SESSION`;
DESCRIBE FEEDBACK;
DESCRIBE SKILL_VERIFICATION;

-- =====================================================
-- END OF DATABASE SCRIPT
-- =====================================================