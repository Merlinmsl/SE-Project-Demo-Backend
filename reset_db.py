"""Reset DB to new schema using SQLAlchemy. Run from project root."""
from app.db.session import engine
from sqlalchemy import text

# SQL to drop all old tables and recreate with new schema
sql_drop = """
DROP TABLE IF EXISTS student_subjects CASCADE;
DROP TABLE IF EXISTS resources CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS subjects CASCADE;
DROP TABLE IF EXISTS grades CASCADE;
DROP TABLE IF EXISTS districts CASCADE;
DROP TABLE IF EXISTS provinces CASCADE;
DROP TABLE IF EXISTS avatars CASCADE;
DROP TYPE IF EXISTS resource_type CASCADE;
"""

sql_create = """
CREATE TYPE resource_type AS ENUM ('textbook','past_paper','answers','notes','other');

CREATE TABLE provinces (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE districts (
  id SERIAL PRIMARY KEY,
  province_id INT NOT NULL REFERENCES provinces(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  UNIQUE (province_id, name)
);

CREATE TABLE grades (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE students (
  id BIGSERIAL PRIMARY KEY,
  clerk_user_id TEXT UNIQUE NOT NULL,
  email VARCHAR(255),
  full_name VARCHAR(150),
  username VARCHAR(50) UNIQUE,
  avatar_key VARCHAR(30),
  grade_id SMALLINT REFERENCES grades(id) ON DELETE SET NULL,
  district_id SMALLINT REFERENCES districts(id) ON DELETE SET NULL,
  profile_completed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE subjects (
  id SERIAL PRIMARY KEY,
  grade_id INT NOT NULL REFERENCES grades(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (grade_id, name)
);

CREATE TABLE student_subjects (
  student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  subject_id BIGINT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (student_id, subject_id)
);

CREATE TABLE resources (
  id BIGSERIAL PRIMARY KEY,
  subject_id INT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  type resource_type NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT,
  file_url TEXT,
  storage_path TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_students_clerk_user_id ON students(clerk_user_id);
CREATE INDEX idx_subjects_grade_id ON subjects(grade_id);
CREATE INDEX idx_resources_subject_id ON resources(subject_id);
"""

# Seed provinces from the seed file
with open("sql/seed_provinces_districts.sql") as f:
    sql_seed_pd = f.read()

sql_seed_grades = """
INSERT INTO grades (name, is_active) VALUES
  ('Grade 9', true),
  ('Grade 10', true),
  ('Grade 11', true)
ON CONFLICT (name) DO NOTHING;

INSERT INTO subjects (grade_id, name)
SELECT g.id, s.name
FROM grades g, (VALUES
  ('English'), ('History'), ('Civic'), ('Science'), ('Mathematics')
) AS s(name)
WHERE g.name = 'Grade 9'
ON CONFLICT (grade_id, name) DO NOTHING;
"""

with engine.connect() as conn:
    conn.execute(text(sql_drop))
    conn.commit()
    print("[OK] Dropped old tables")

    conn.execute(text(sql_create))
    conn.commit()
    print("[OK] Created new schema")

    conn.execute(text(sql_seed_pd))
    conn.commit()
    print("[OK] Seeded provinces/districts")

    conn.execute(text(sql_seed_grades))
    conn.commit()
    print("[OK] Seeded grades/subjects")

    # Verify
    provinces = conn.execute(text("SELECT COUNT(*) FROM provinces")).scalar()
    districts = conn.execute(text("SELECT COUNT(*) FROM districts")).scalar()
    grades = conn.execute(text("SELECT COUNT(*) FROM grades")).scalar()
    subjects = conn.execute(text("SELECT COUNT(*) FROM subjects")).scalar()
    
    print(f"\nDB ready: {provinces} provinces, {districts} districts, {grades} grades, {subjects} subjects")
    print("All integer IDs, avatar_key VARCHAR(30)")
