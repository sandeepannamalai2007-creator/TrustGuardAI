from database import SessionLocal
import crud

db = SessionLocal()

student = crud.get_student(db, "22CS101")

if student is None:
    student = crud.create_student(
        db,
        student_id="22CS101",
        name="John Doe",
        email="john@example.com"
    )

print(student.student_id)
print(student.name)
print(student.email)

db.close()