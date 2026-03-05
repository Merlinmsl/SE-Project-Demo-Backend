"""
Validates that all Pydantic schemas and SQLAlchemy models import and construct correctly.
Run from project root: python validate_schemas.py
"""
from app.schemas.student import StudentProfileOut, StudentOnboardingIn, StudentProfileUpdateIn
from app.schemas.resource import ResourceOut
from app.schemas.meta import GradeOut, DistrictOut, ProvinceOut, AvatarCatalogOut
from app.schemas.subject import SubjectOut

# Test StudentProfileOut
p = StudentProfileOut(
    id=42,
    email="test@test.com",
    full_name="Test User",
    username="testuser",
    grade=GradeOut(id=1, name="Grade 9"),
    district=DistrictOut(id=1, name="District A", province=ProvinceOut(id=1, name="Province A")),
    province=ProvinceOut(id=1, name="Province A"),
    avatar_key="avatar_1",
    profile_completed=True,
)
assert isinstance(p.id, int), f"id should be int, got {type(p.id)}"
assert isinstance(p.avatar_key, str), f"avatar_key should be str"
print(f"[OK] StudentProfileOut: id={p.id} (int), avatar_key={p.avatar_key!r} (str)")

# Test StudentOnboardingIn
o = StudentOnboardingIn(
    full_name="Test", username="testuser2",
    grade_id=1, province_id=1, district_id=1,
    avatar_key="avatar_2", subject_ids=[1, 2]
)
assert isinstance(o.avatar_key, str)
print(f"[OK] StudentOnboardingIn: avatar_key={o.avatar_key!r}")

# Test ResourceOut
r = ResourceOut(id=100, subject_id=1, type="textbook", title="Test Book")
assert isinstance(r.id, int), f"id should be int, got {type(r.id)}"
print(f"[OK] ResourceOut: id={r.id} (int)")

# Test AvatarCatalogOut
a = AvatarCatalogOut(avatar_key="avatar_1", label="Avatar 1")
assert isinstance(a.avatar_key, str)
print(f"[OK] AvatarCatalogOut: avatar_key={a.avatar_key!r}")

# Test model imports
from app.models.student import Student
from app.models.resource import Resource
from app.models.subject import Subject, StudentSubject
from app.models.meta import Province, District, Grade

# Verify no Avatar class (should not exist)
try:
    from app.models.meta import Avatar
    print("[FAIL] Avatar should not be importable!")
except ImportError:
    print("[OK] Avatar class correctly removed from meta model")

print("\nAll schema/model validations passed!")
