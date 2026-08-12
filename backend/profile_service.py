from sqlalchemy.orm import Session

import crud


def update_student_profile(
    db: Session,
    student_id: int,
    avg_dwell_time: float,
    avg_flight_time: float,
    typing_speed: float,
    mouse_velocity: float
):
    """
    Create a new behaviour profile if it doesn't exist,
    otherwise update the existing one.
    """

    profile = crud.get_behavior_profile(db, student_id)

    if profile is None:

        return crud.create_behavior_profile(
            db=db,
            student_id=student_id,
            avg_dwell_time=avg_dwell_time,
            avg_flight_time=avg_flight_time,
            typing_speed=typing_speed,
            mouse_velocity=mouse_velocity
        )

    return crud.update_behavior_profile(
        db=db,
        profile=profile,
        avg_dwell_time=avg_dwell_time,
        avg_flight_time=avg_flight_time,
        typing_speed=typing_speed,
        mouse_velocity=mouse_velocity
    )