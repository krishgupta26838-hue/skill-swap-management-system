-- =====================================================
-- SKILL SWAP MANAGEMENT SYSTEM - SEED DATA SCRIPT
-- =====================================================

USE skill_swap_db;

-- 1. USERS (2 Admins, 10 Users)
-- Admin passwords: Admin@123
-- User passwords:  User@123

INSERT INTO `USER` (user_id, name, email, password, phone, role, created_at) VALUES
(1, 'Aarav Sharma', 'aarav.admin@skillswap.com', 'scrypt:32768:8:1$Ju5LqPKKLwAp1Yqm$f5d57a5dd35873f97bd53d9efa0bb28585e95af47661bbc8303fc7b3314d12de5ee04854f83d990f3393e0db6193c2b4d35f310ded3daa6aec90d028a0ca583a', '9876543210', 'Admin', '2026-01-10 09:00:00'),
(2, 'Pooja Patel', 'pooja.admin@skillswap.com', 'scrypt:32768:8:1$Ju5LqPKKLwAp1Yqm$f5d57a5dd35873f97bd53d9efa0bb28585e95af47661bbc8303fc7b3314d12de5ee04854f83d990f3393e0db6193c2b4d35f310ded3daa6aec90d028a0ca583a', '9876543211', 'Admin', '2026-01-11 10:30:00'),
(3, 'Rahul Verma', 'rahul@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456780', 'User', '2026-01-15 11:00:00'),
(4, 'Ananya Iyer', 'ananya@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456781', 'User', '2026-01-16 12:15:00'),
(5, 'Rohan Mehta', 'rohan@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456782', 'User', '2026-01-18 14:20:00'),
(6, 'Sneha Reddy', 'sneha@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456783', 'User', '2026-01-20 15:45:00'),
(7, 'Vikram Singh', 'vikram@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456784', 'User', '2026-01-22 16:10:00'),
(8, 'Priya Nair', 'priya@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456785', 'User', '2026-01-25 17:00:00'),
(9, 'Amit Joshi', 'amit@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456786', 'User', '2026-02-01 10:00:00'),
(10, 'Divya Kapoor', 'divya@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456787', 'User', '2026-02-03 11:30:00'),
(11, 'Karan Malhotra', 'karan@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456788', 'User', '2026-02-05 13:40:00'),
(12, 'Meera Sen', 'meera@gmail.com', 'scrypt:32768:8:1$pcfiCTsnXuwkn2FA$cd60cb2f1345b94f8fbdefda3e9df48f425a42ed40e72fe3f342a825493dd77c9c012bd97488615d499964af89bc99f852593c0ded6d93d64c4997630e0d75c0', '9123456789', 'User', '2026-02-10 14:50:00');

-- 2. SKILL CATEGORIES (6 categories)
INSERT INTO SKILL_CATEGORY (category_id, category_name) VALUES
(1, 'Programming & Tech'),
(2, 'Design & Creative'),
(3, 'Languages & Communication'),
(4, 'Music & Audio'),
(5, 'Business & Marketing'),
(6, 'Health & Wellness');

-- 3. SKILLS (20 skills)
INSERT INTO SKILL (skill_id, skill_name, category_id) VALUES
(1, 'Python Programming', 1),
(2, 'Web Development (HTML/CSS/JS)', 1),
(3, 'MySQL Database Design', 1),
(4, 'Machine Learning Basics', 1),
(5, 'UI/UX Design with Figma', 2),
(6, 'Graphic Design (Photoshop/Illustrator)', 2),
(7, 'Video Editing (Premiere Pro)', 2),
(8, '3D Modeling & Blender', 2),
(9, 'Conversational Spanish', 3),
(10, 'Spoken & Business English', 3),
(11, 'French for Beginners', 3),
(12, 'Public Speaking & Presentation', 3),
(13, 'Acoustic Guitar', 4),
(14, 'Keyboard & Piano', 4),
(15, 'Vocal Training', 4),
(16, 'Music Production (FL Studio)', 4),
(17, 'Digital Marketing & SEO', 5),
(18, 'Financial Accounting Basics', 5),
(19, 'Hatha Yoga & Breathwork', 6),
(20, 'Strength & Fitness Training', 6);

-- 4. USER_SKILLS (26 rows: Offerings and Learnings)
INSERT INTO USER_SKILL (user_skill_id, user_id, skill_id, skill_type) VALUES
-- Rahul Verma (user 3): Offers Python & MySQL; Wants to Learn UI/UX & Spanish
(1, 3, 1, 'Offering'),
(2, 3, 3, 'Offering'),
(3, 3, 5, 'Learning'),
(4, 3, 9, 'Learning'),

-- Ananya Iyer (user 4): Offers UI/UX & Graphic Design; Wants to Learn Python
(5, 4, 5, 'Offering'),
(6, 4, 6, 'Offering'),
(7, 4, 1, 'Learning'),

-- Rohan Mehta (user 5): Offers Acoustic Guitar & Music Production; Wants to Learn Web Dev
(8, 5, 13, 'Offering'),
(9, 5, 16, 'Offering'),
(10, 5, 2, 'Learning'),

-- Sneha Reddy (user 6): Offers Conversational Spanish; Wants to Learn Acoustic Guitar
(11, 6, 9, 'Offering'),
(12, 6, 13, 'Learning'),

-- Vikram Singh (user 7): Offers Web Development & Machine Learning; Wants to Learn Piano
(13, 7, 2, 'Offering'),
(14, 7, 4, 'Offering'),
(15, 7, 14, 'Learning'),

-- Priya Nair (user 8): Offers Yoga & Nutrition; Wants to Learn Digital Marketing
(16, 8, 19, 'Offering'),
(17, 8, 17, 'Learning'),

-- Amit Joshi (user 9): Offers Digital Marketing & SEO; Wants to Learn Python
(18, 9, 17, 'Offering'),
(19, 9, 1, 'Learning'),

-- Divya Kapoor (user 10): Offers Keyboard & Piano; Wants to Learn Yoga
(20, 10, 14, 'Offering'),
(21, 10, 19, 'Learning'),

-- Karan Malhotra (user 11): Offers Video Editing; Wants to Learn French
(22, 11, 7, 'Offering'),
(23, 11, 11, 'Learning'),

-- Meera Sen (user 12): Offers French for Beginners; Wants to Learn Video Editing
(24, 12, 11, 'Offering'),
(25, 12, 7, 'Learning'),

-- Additional offerings for variety
(26, 3, 12, 'Offering'); -- Rahul also offers Public Speaking

-- 5. SKILL VERIFICATIONS (6 rows: Pending, Verified, Rejected)
-- Only for Offering user_skills. admin_id must belong to Admin (1 or 2).
INSERT INTO SKILL_VERIFICATION (verification_id, user_skill_id, admin_id, verification_status, verification_date) VALUES
(1, 1, 1, 'Verified', '2026-02-01 10:00:00'),   -- Rahul Python verified by Aarav
(2, 5, 1, 'Verified', '2026-02-02 11:30:00'),   -- Ananya UI/UX verified by Aarav
(3, 8, 2, 'Verified', '2026-02-03 14:00:00'),   -- Rohan Guitar verified by Pooja
(4, 11, 2, 'Rejected', '2026-02-04 16:00:00'),  -- Sneha Spanish rejected (needs cert)
(5, 13, 1, 'Pending', NULL),                    -- Vikram Web Dev pending verification
(6, 16, 2, 'Pending', NULL);                    -- Priya Yoga pending verification

-- 6. LEARNING REQUESTS (10 rows in all four statuses)
-- Only targets Offering user_skills. Requester != teacher.
INSERT INTO LEARNING_REQUEST (request_id, requester_id, user_skill_id, request_date, status) VALUES
-- Accepted requests (lead to sessions)
(1, 4, 1, '2026-02-05 10:00:00', 'Accepted'),   -- Ananya (4) requests Rahul's Python (1) -> Teacher: 3
(2, 3, 5, '2026-02-06 11:00:00', 'Accepted'),   -- Rahul (3) requests Ananya's UI/UX (5) -> Teacher: 4
(3, 6, 8, '2026-02-07 14:00:00', 'Accepted'),   -- Sneha (6) requests Rohan's Guitar (8) -> Teacher: 5
(4, 5, 13, '2026-02-08 15:30:00', 'Accepted'),  -- Rohan (5) requests Vikram's Web Dev (13) -> Teacher: 7
(5, 10, 16, '2026-02-09 16:00:00', 'Accepted'), -- Divya (10) requests Priya's Yoga (16) -> Teacher: 8

-- Pending requests
(6, 9, 1, '2026-02-12 09:30:00', 'Pending'),    -- Amit (9) requests Rahul's Python (1)
(7, 7, 20, '2026-02-13 10:15:00', 'Pending'),   -- Vikram (7) requests Divya's Piano (20)
(8, 12, 22, '2026-02-14 11:00:00', 'Pending'),  -- Meera (12) requests Karan's Video Editing (22)

-- Rejected request
(9, 8, 18, '2026-02-10 12:00:00', 'Rejected'),  -- Priya (8) requested Amit's SEO (18)

-- Cancelled request
(10, 11, 24, '2026-02-11 13:00:00', 'Cancelled'); -- Karan (11) requested Meera's French (24)

-- 7. SESSIONS (8 rows: Scheduled, Completed, Cancelled)
-- Sessions exist only for Accepted requests (requests 1, 2, 3, 4, 5).
-- check(end_time > start_time)
INSERT INTO `SESSION` (session_id, request_id, session_date, start_time, end_time, status) VALUES
-- Request 1 (Ananya learning Python from Rahul)
(1, 1, '2026-02-10', '10:00:00', '11:30:00', 'Completed'),
(2, 1, '2026-02-17', '10:00:00', '11:30:00', 'Completed'),
(3, 1, '2026-03-05', '10:00:00', '11:30:00', 'Scheduled'),

-- Request 2 (Rahul learning UI/UX from Ananya)
(4, 2, '2026-02-12', '14:00:00', '15:30:00', 'Completed'),
(5, 2, '2026-03-08', '14:00:00', '15:30:00', 'Scheduled'),

-- Request 3 (Sneha learning Guitar from Rohan)
(6, 3, '2026-02-15', '16:00:00', '17:00:00', 'Completed'),

-- Request 4 (Rohan learning Web Dev from Vikram)
(7, 4, '2026-02-16', '18:00:00', '19:30:00', 'Cancelled'),

-- Request 5 (Divya learning Yoga from Priya)
(8, 5, '2026-03-10', '07:00:00', '08:00:00', 'Scheduled');

-- 8. FEEDBACK (6 rows)
-- Only on Completed sessions (1, 2, 4, 6) from participant (learner or teacher).
-- Session 1: Request 1 (Learner: 4 [Ananya], Teacher: 3 [Rahul])
INSERT INTO FEEDBACK (feedback_id, session_id, reviewer_id, rating, comment, feedback_date) VALUES
(1, 1, 4, 5, 'Rahul is an incredible teacher! Explained Python data structures and loops clearly.', '2026-02-10 12:00:00'),
(2, 1, 3, 5, 'Ananya was very quick to grasp list comprehensions and asked great questions.', '2026-02-10 12:30:00'),

-- Session 2: Request 1 (Learner: 4, Teacher: 3)
(3, 2, 4, 5, 'Second session on functions and OOP was even better. Highly recommended tutor!', '2026-02-17 12:05:00'),

-- Session 4: Request 2 (Learner: 3 [Rahul], Teacher: 4 [Ananya])
(4, 4, 3, 5, 'Ananya taught wireframing and auto-layout in Figma super patiently. Loved it!', '2026-02-12 16:00:00'),
(5, 4, 4, 4, 'Rahul picked up Figma component design very fast.', '2026-02-12 16:30:00'),

-- Session 6: Request 3 (Learner: 6 [Sneha], Teacher: 5 [Rohan])
(6, 6, 6, 5, 'Rohan broke down chord transitions so easily. Playing my first song now!', '2026-02-15 17:30:00');
