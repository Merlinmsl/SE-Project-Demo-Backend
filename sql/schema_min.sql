-- Minimal schema subset for Sprint 1 profile/subjects/resources
-- Updated: UUID -> BIGSERIAL for students and resources; avatar_key VARCHAR(30); no avatars table

create type if not exists resource_type as enum ('textbook','past_paper','answers','notes','other');

create table if not exists provinces (
  id serial primary key,
  name varchar(100) unique not null
);

create table if not exists districts (
  id serial primary key,
  province_id int not null references provinces(id) on delete cascade,
  name varchar(100) not null,
  unique (province_id, name)
);

create table if not exists grades (
  id serial primary key,
  name varchar(100) unique not null,
  is_active boolean default true,
  created_at timestamp default current_timestamp
);

create table if not exists students (
  id bigserial primary key,
  clerk_user_id text unique not null,
  email varchar(255),
  full_name varchar(150),
  username varchar(50) unique,
  avatar_key varchar(30),
  grade_id smallint references grades(id) on delete set null,
  district_id smallint references districts(id) on delete set null,
  profile_completed boolean not null default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists subjects (
  id serial primary key,
  grade_id int not null references grades(id) on delete cascade,
  name varchar(255) not null,
  created_at timestamp default current_timestamp,
  unique (grade_id, name)
);

create table if not exists student_subjects (
  student_id bigint not null references students(id) on delete cascade,
  subject_id bigint not null references subjects(id) on delete cascade,
  selected_at timestamp default current_timestamp,
  primary key (student_id, subject_id)
);

create table if not exists resources (
  id bigserial primary key,
  subject_id int not null references subjects(id) on delete cascade,
  type resource_type not null,
  title varchar(200) not null,
  description text,
  file_url text,
  storage_path text,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_students_clerk_user_id on students(clerk_user_id);
create index if not exists idx_subjects_grade_id on subjects(grade_id);
create index if not exists idx_resources_subject_id on resources(subject_id);
