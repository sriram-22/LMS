from django.urls import path
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView)

from .views import *

urlpatterns = [
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("user/", UserAPIView.as_view()),
    path("user/<int:pk>/", UserAPIView.as_view()),
    path("update_user_password/", UpdateUserPasswordAPIView.as_view()),
    path("course/", CourseAPIView.as_view()),
    path("course/<int:pk>/", CourseAPIView.as_view()),
    path("course_instructors/", CourseInstructorsAPIView.as_view()),
    path("course_instructors/<int:pk>/", CourseInstructorsAPIView.as_view()),
    path("Instructor_courses/", InstructorAssignedCoursesAPIView.as_view()),
    path("enrollment/", EnrollmentAPIView.as_view()),
    path("enrollment/<int:pk>/", EnrollmentAPIView.as_view()),
    path("student_enrollment/", StudentEnrollmentAPIView.as_view()),
    path("student_enrollment/<int:pk>/", StudentEnrollmentAPIView.as_view()),
    path("instructor_students/", InstructorStudentsAPIView.as_view()),
    path("course-videos/<int:pk>/", CourseVideoAPIView.as_view()),
    path("course-comments/<int:pk>/", CourseCommentAPIView.as_view()),
    path("course-likes/<int:pk>/", CourseLikeAPIView.as_view()),
    path("course-rating/<int:pk>/", CourseRatingAPIView.as_view()),
    path(
        "student_course_progress_tracking/<int:pk>/",
        StudentCourseProgressTrackingAPIView.as_view(),
    ),
    path(
        "instructor_students_course_progress_tracking/<int:pk>/",
        InstructorStudentsCourseProgressTrackingAPIView.as_view(),
    ),
    path("quiz/", QuizAPIView.as_view()),
    path("quiz/<int:pk>/", QuizAPIView.as_view()),
    path("quiz_question/", QuizQuestionAPIView.as_view()),
    path("quiz_question/<int:pk>/", QuizQuestionAPIView.as_view()),
    path("quiz_attempt/", QuizAttemptAPIView.as_view()),
    path("quiz_attempt/<int:pk>/", QuizAttemptAPIView.as_view()),
]
