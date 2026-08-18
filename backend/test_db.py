import crud
from database import Base, SessionLocal, engine


def test_db_operations():
    # Guarantee schema is initialized in the test session SQLite
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        student = crud.get_student(db, "22CS101")
        if student is None:
            student = crud.create_student(
                db,
                student_id="22CS101",
                name="John Doe",
                email="john@example.com"
            )
        assert student.student_id == "22CS101"
        assert student.name == "John Doe"
        assert student.email == "john@example.com"
    finally:
        db.close()