from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Course,
    CourseComment,
    CourseLike,
    CourseProgressTracking,
    CourseRating,
    CourseVideo,
    Enrollment,
    Question,
    Quiz,
    QuizAttempt,
    User,
)
from .permissions import (
    IsAdminOrInstructor,
    IsAdminOrInstructorOrStudentRelatedToCourse,
    IsAdminOrInstructorRelatedToCourse,
    IsAdminUserRole,
    IsInstructorRelatedToCourse,
    IsInstructorUserRole,
    IsStudentRelatedToCourse,
    IsStudentUserRole,
    IsUser,
    IsUserorAdmin,
)
from .serializer import (
    CourseCommentSerializer,
    CourseLikeSerializer,
    CourseProgressTrackingSerializer,
    CourseRatingSerializer,
    CourseSerializer,
    CourseVideoSerializer,
    EnrollmentSerializer,
    Loginserializer,
    QuestionSerializer,
    QuizAttemptSerializer,
    QuizSerializer,
    UpadateUserPasswordSerializer,
    UserSerializer,
)


class BaseAPIView(APIView):

    def handle_exception(self, exc):
        if isinstance(exc, exceptions.NotAuthenticated):
            return Response(
                {"error h_exception: Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if isinstance(exc, PermissionDenied):
            return Response(
                {
                    "error h_exception": "You do not have permission to perform this action"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if isinstance(exc, Http404):
            return Response(
                {f"error h_exception: {str(exc)}"}, status=status.HTTP_404_NOT_FOUND
            )

        return super().handle_exception(exc)


class RegisterAPIView(APIView):

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({"message": "User created"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    def post(self, request):
        serializer = Loginserializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "role": user.role,
                    },
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAPIView(BaseAPIView):
    def get_object(self, pk):
        user = get_object_or_404(User, pk=pk)
        self.check_object_permissions(self.request, user)
        return user

    def get_permissions(self):
        if self.request.method in ["GET"]:
            return [IsAuthenticated(), IsUserorAdmin()]
        if self.request.method in ["POST"]:
            return []
        if self.request.method in ["PUT", "PATCH"]:
            return [IsAuthenticated(), IsUser()]
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsUserorAdmin()]
        return [IsAuthenticated()]

    def get(self, request, pk=None):
        if pk:
            user = self.get_object(pk)
            serializer = UserSerializer(user, exclude=["id", "username"])
            return Response(serializer.data)
        else:
            if not (request.user.role == "admin"):
                return Response(
                    {"error": "You are not authorized to view all users"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            user = User.objects.all()
            serializer = UserSerializer(user, many=True)
            return Response(serializer.data)

    def patch(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = UserSerializer(
            user,
            data=request.data,
            fields=["id", "username", "email", "password", "password2", "role"],
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UpdateUserPasswordAPIView(APIView):
    def put(self, request):
        serializer = UpadateUserPasswordSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message: password updated successfully"},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseAPIView(BaseAPIView):

    def get_permissions(self):
        if self.request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated(), IsAdminUserRole()]
        return [IsAuthenticated()]

    def get(self, request, pk=None):
        if pk:
            course = get_object_or_404(Course, pk=pk)
            serializer = CourseSerializer(course)
            return Response(serializer.data)
        else:
            # Full Text Search
            q = request.query_params.get("search", None)
            if q:
                search_vector = SearchVector("name", "description")
                search_query = SearchQuery(q)
                course = (
                    Course.objects.annotate(
                        rank=SearchRank(search_vector, search_query)
                    )
                    .filter(rank__gte=0.01)
                    .order_by("-rank")
                )
            else:
                course = Course.objects.all()

            serializer = CourseSerializer(
                course, fields=["id", "name", "description"], many=True
            )
            return Response(serializer.data)

    def post(self, request):
        serializer = CourseSerializer(
            data=request.data, fields=["name", "description", "instructors"]
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            course = Course.objects.get(id=pk)
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = CourseSerializer(
            course, data=request.data,
            fields=["name", "description", "instructors"]
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            course = Course.objects.get(id=pk)
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstructorAssignedCoursesAPIView(APIView):
    permission_classes = [IsAuthenticated, IsInstructorUserRole]

    def get(self, request):
        instructor_courses = request.user.courses.all()
        serializer = CourseSerializer(instructor_courses, many=True)
        return Response(serializer.data)


class CourseInstructorsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request, pk):
        try:
            course = Course.objects.get(id=pk)
            serializer = CourseSerializer(
                course, fields=["id", "name", "description", "instructors"]
            )
            return Response(serializer.data)
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)


class StudentEnrollmentAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    def get(self, request, pk=None):
        try:
            student = User.objects.get(id=request.user.id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if pk:
            try:
                enrollment = Enrollment.objects.get(id=pk)
                if enrollment.student.id != student.id:
                    return Response(
                        {"error": "You are not authorized to view this enrollment"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                serializer = EnrollmentSerializer(enrollment)
                return Response(serializer.data)
            except Enrollment.DoesNotExist:
                return Response(
                    {"error": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND
                )

        enrollment = Enrollment.objects.filter(student=student)
        serializer = EnrollmentSerializer(enrollment, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        data["student"] = request.user.id
        serializer = EnrollmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            enrollment = Enrollment.objects.get(id=pk)
        except Enrollment.DoesNotExist:
            return Response(
                {"message": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if enrollment.student.id != request.user.id:
            return Response(
                {"error": "You are not authorized to delete this enrollment"},
                status=status.HTTP_403_FORBIDDEN,
            )
        enrollment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstructorStudentsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrInstructor]

    def get(self, request):
        try:
            instructor = User.objects.get(id=request.user.id)
            enrollment = Enrollment.objects.filter(instructor=instructor)
            serializer = EnrollmentSerializer(enrollment, many=True)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class EnrollmentAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request, pk=None):
        if pk:
            try:
                enrollment = Enrollment.objects.get(id=pk)
                serializer = EnrollmentSerializer(enrollment)
                return Response(serializer.data)
            except Enrollment.DoesNotExist:
                return Response(
                    {"error": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            enrollment = Enrollment.objects.all()
            serializer = EnrollmentSerializer(enrollment, many=True)
            return Response(serializer.data)

    def put(self, request, pk):
        try:
            enrollment = Enrollment.objects.get(id=pk)
        except Enrollment.DoesNotExist:
            return Response(
                {"message": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = EnrollmentSerializer(enrollment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Update the instuctor and status of an enrollment
    def patch(self, request, pk):
        try:
            enrollment = Enrollment.objects.get(id=pk)
        except Enrollment.DoesNotExist:
            return Response(
                {"message": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = EnrollmentSerializer(
            enrollment, data=request.data, fields=["instructor", "status"], partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            enrollment = Enrollment.objects.get(id=pk)
        except Enrollment.DoesNotExist:
            return Response(
                {"message": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND
            )
        enrollment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# methods should provide course id as pk
class CourseVideoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsAdminOrInstructorOrStudentRelatedToCourse()]
        if self.request.method in ["POST", "DELETE"]:
            return [IsAuthenticated(), IsAdminOrInstructorRelatedToCourse()]
        return Response(
            {"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def get_object(self, pk):
        try:
            course = Course.objects.get(id=pk)
        except Course.DoesNotExist:
            raise NotFound({"error": "Course not found"})
        except Exception as e:
            return APIException({"error": str(e)})
        self.check_object_permissions(self.request, course)
        return course

    def get(self, request, pk):
        if pk:
            course = self.get_object(pk)
            course_videos = CourseVideo.objects.filter(course=course)
            if not course_videos:
                return Response(
                    {"error": "CourseVideos not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = CourseVideoSerializer(course_videos, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"error": "Course id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    def post(self, request, pk):
        data = request.data
        course = self.get_object(pk)
        data["course"] = course.id
        serializer = CourseVideoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # specify the id's of the videos
    def delete(self, request, pk):
        course = self.get_object(pk)
        videos = request.data.get("videos", [])

        course_videos = CourseVideo.objects.filter(course=course, id__in=videos)
        if len(course_videos) == len(videos):
            course_videos.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"error": "Invalid video id"}, status=status.HTTP_400_BAD_REQUEST
        )


# course id should be provided as pk
class CourseCommentAPIView(APIView):
    def get_permissions(self):
        if self.request.method in ["POST", "DELETE", "PATCH", "GET"]:
            return [IsAuthenticated(), IsAdminOrInstructorOrStudentRelatedToCourse()]
        return Response(
            {"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def get_object(self, pk):
        try:
            course = Course.objects.get(id=pk)
        except Course.DoesNotExist:
            raise NotFound({"error": "Course not found"})
        except Exception as e:
            return APIException({"error": str(e)})
        self.check_object_permissions(self.request, course)
        return course

    def get(self, request, pk=None):
        if pk:
            course = self.get_object(pk)
            comments = CourseComment.objects.filter(course=course)
            serializer = CourseCommentSerializer(comments, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "Course id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    def post(self, request, pk):
        data = request.data
        course = self.get_object(pk)
        data["course"] = course.id
        serializer = CourseCommentSerializer(
            data=data, context={"request": request}
        )  # Pass context
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Expects single comment id
    def patch(self, request, pk):
        course = self.get_object(pk)
        try:
            comment = CourseComment.objects.get(
                id=request.data.get("id"), course=course, user=request.user
            )
        except CourseComment.DoesNotExist:
            return Response(
                {"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND
            )
        for key in request.data:
            if key not in ["content", "id"]:
                return Response(
                    {"error": "Invalid key"}, status=status.HTTP_400_BAD_REQUEST
                )
        serializer = CourseCommentSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Expects the id of the comments
    def delete(self, request, pk):
        course = self.get_object(pk)
        comments_id = request.data.get("id", [])
        try:
            comment = CourseComment.objects.get(
                id=comments_id, course=course, user=request.user
            )
        except CourseComment.DoesNotExist:
            return Response(
                {"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND
            )
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseLikeAPIView(APIView):

    permission_classes = [IsAuthenticated, IsAdminOrInstructorOrStudentRelatedToCourse]

    def get_object(self, pk):
        try:
            course = Course.objects.get(id=pk)
        except Course.DoesNotExist:
            raise NotFound({"error": "Course not found"})
        except Exception as e:
            return APIException({"error": str(e)})
        self.check_object_permissions(self.request, course)
        return course

    def post(self, request, pk):
        course = self.get_object(pk)
        data = request.data
        data["user"] = request.user.id
        data["course"] = course.id
        serializer = CourseLikeSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        course = self.get_object(pk)
        try:
            like = CourseLike.objects.get(course=course, user=request.user)
        except CourseLike.DoesNotExist:
            return Response(
                {"error": "Like not found"}, status=status.HTTP_404_NOT_FOUND
            )
        like.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseRatingAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrInstructorOrStudentRelatedToCourse]

    def get_object(self, pk):
        try:
            course = Course.objects.get(id=pk)
        except Course.DoesNotExist:
            raise NotFound({"error": "Course not found"})
        except Exception as e:
            return APIException({"error": str(e)})
        self.check_object_permissions(self.request, course)
        return course

    def post(self, request, pk):
        course = self.get_object(pk)
        data = request.data
        data["user"] = request.user.id
        data["course"] = course.id
        serializer = CourseRatingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        course = self.get_object(pk)
        data = request.data
        data["user"] = request.user.id
        data["course"] = course.id
        try:
            rating = CourseRating.objects.get(course=course, user=request.user)
        except CourseRating.DoesNotExist:
            return Response(
                {"error": "Rating not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = CourseRatingSerializer(rating, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        course = self.get_object(pk)
        try:
            rating = CourseRating.objects.get(course=course, user=request.user)
        except CourseRating.DoesNotExist:
            return Response(
                {"error": "Rating not found"}, status=status.HTTP_404_NOT_FOUND
            )
        rating.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# student user should send course id as pk
class StudentCourseProgressTrackingAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentRelatedToCourse]

    def get_object(self, pk):
        try:
            course = Course.objects.get(id=pk)
        except Course.DoesNotExist:
            raise NotFound({"error": "Course not found"})
        except Exception as e:
            return APIException({"error": str(e)})
        self.check_object_permissions(self.request, course)
        return course

    def get(self, request, pk):
        course = self.get_object(pk)
        try:
            course_progress = CourseProgressTracking.objects.get(
                course=course, student=request.user
            )
        except CourseProgressTracking.DoesNotExist:
            return Response(
                {"error": "CourseProgressTracking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CourseProgressTrackingSerializer(course_progress)
        return Response(serializer.data)

    def post(self, request, pk):
        course = self.get_object(pk)
        data = request.data
        data["student"] = request.user.id
        data["course"] = course.id
        serializer = CourseProgressTrackingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # to update the complete set of completed_videos
    def put(self, request, pk):
        course = self.get_object(pk)
        completed_videos_ids = request.data.get("completed_videos", False)
        if not completed_videos_ids:
            return Response(
                {"error": "completed_videos field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        completed_videos = CourseVideo.objects.filter(
            id__in=completed_videos_ids, course=course
        )
        if len(completed_videos_ids) != len(completed_videos):
            return Response(
                {"error": "Invalid video id"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            course_progress = CourseProgressTracking.objects.get(
                course=course, student=request.user
            )
        except CourseProgressTracking.DoesNotExist:
            return Response(
                {"error": "CourseProgressTracking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        course_progress.completed_videos.set(completed_videos)
        serializer = CourseProgressTrackingSerializer(
            course_progress, data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # to add one or more videos to the existing completed_videos
    def patch(self, request, pk):
        course = self.get_object(pk)
        completed_videos_ids = request.data.get("completed_videos", False)
        if not completed_videos_ids:
            return Response(
                {"error": "completed_videos field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        completed_videos = CourseVideo.objects.filter(
            id__in=completed_videos_ids, course=course
        )
        if len(completed_videos_ids) != len(completed_videos):
            return Response(
                {"error": "Invalid video id"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            course_progress = CourseProgressTracking.objects.get(
                course=course, student=request.user
            )
        except CourseProgressTracking.DoesNotExist:
            return Response(
                {"error": "CourseProgressTracking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        course_progress.completed_videos.add(*completed_videos)
        serializer = CourseProgressTrackingSerializer(
            course_progress, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # delete this method
    def delete(self, request, pk):
        course = self.get_object(pk)
        try:
            course_progress = CourseProgressTracking.objects.get(
                course=course, student=request.user
            )
        except CourseProgressTracking.DoesNotExist:
            return Response(
                {"error": "CourseProgressTracking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        course_progress.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstructorStudentsCourseProgressTrackingAPIView(APIView):
    permission_classes = [IsAuthenticated, IsInstructorRelatedToCourse]

    def get_object(self, pk):
        try:
            course = Course.objects.get(id=pk)
        except Course.DoesNotExist:
            raise NotFound({"error": "Course not found"})
        except Exception as e:
            return APIException({"error": str(e)})
        self.check_object_permissions(self.request, course)
        return course

    def get(self, request, pk):
        course = self.get_object(pk)
        try:
            instructor_students = Enrollment.objects.filter(
                course=course, instructor=request.user, status="approved"
            )
        except Enrollment.DoesNotExist:
            return Response(
                {"error": "user not found"}, status=status.HTTP_404_NOT_FOUND
            )

        students = [student.student for student in instructor_students]
        students_progress = CourseProgressTracking.objects.filter(
            course=course, student__in=students
        )
        serializer = CourseProgressTrackingSerializer(students_progress, many=True)
        return Response(serializer.data)


# Quiz id should be provided as pk
class QuizAPIView(APIView):
    def get_permissions(self):
        if self.request.method in ["GET"]:
            return [IsAuthenticated(), IsAdminOrInstructorOrStudentRelatedToCourse()]
        if self.request.method in ["POST", "PUT", "DELETE"]:
            return [IsAuthenticated(), IsAdminOrInstructorRelatedToCourse()]
        return Response(
            {"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def get_object(self, pk):
        try:
            quiz = Quiz.objects.get(id=pk)
            course = quiz.video.course
        except Quiz.DoesNotExist:
            raise NotFound({"error": "Quiz not found"})
        except Exception as e:
            return APIException({"error": str(e)})
        self.check_object_permissions(self.request, course)
        return quiz

    def get(self, request, pk=None):
        if pk:
            quiz = self.get_object(pk)
            serializer = QuizSerializer(quiz)
            return Response(serializer.data)
        quizzes = Quiz.objects.all()
        serializer = QuizSerializer(
            quizzes, fields=["id", "video", "title", "description"], many=True
        )
        return Response(serializer.data)

    def post(self, request):
        try:
            video = CourseVideo.objects.get(id=request.data.get("video"))
            course = video.course
        except CourseVideo.DoesNotExist:
            return Response(
                {"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(self.request, course)

        serializer = QuizSerializer(
            fields=["video", "title", "description"], data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        quiz = self.get_object(pk)
        serializer = QuizSerializer(
            quiz, fields=["video", "title", "description"], data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        quiz = self.get_object(pk)
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Question id provided as pk
class QuizQuestionAPIView(APIView):

    def get_permissions(self):
        if self.request.method in ["GET"]:
            return [IsAuthenticated(), IsAdminOrInstructorOrStudentRelatedToCourse()]
        if self.request.method in ["POST", "PUT", "DELETE"]:
            return [IsAuthenticated(), IsAdminOrInstructorRelatedToCourse()]

    def get_object(self, pk):
        try:
            question = Question.objects.get(id=pk)
            course = question.quiz.video.course
        except Question.DoesNotExist:
            raise NotFound({"error": "Question not found"})
        except Exception as e:
            return APIException({"error": str(e)})
        self.check_object_permissions(self.request, course)
        return question

    def get(self, request, pk=None):
        if pk:
            question = self.get_object(pk)
            serializer = QuestionSerializer(question)
            return Response(serializer.data)
        return Response(
            {"error": "Question id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    def post(self, request):
        try:
            quiz = Quiz.objects.get(id=request.data.get("quiz"))
            course = quiz.video.course
        except Quiz.DoesNotExist:
            return Response(
                {"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(self.request, course)

        serializer = QuestionSerializer(
            fields=["quiz", "question", "marks"], data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            question = self.get_object(pk)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = QuestionSerializer(
            question, fields=["question", "marks"], data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        question = self.get_object(pk)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# QuizAttempt id should be provided as pk
class QuizAttemptAPIView(APIView):
    def get_permissions(self):
        if self.request.method in ["GET", "PUT", "DELETE"]:
            return [IsAuthenticated(), IsInstructorRelatedToCourse()]
        if self.request.method in ["POST"]:
            return [IsAuthenticated(), IsStudentRelatedToCourse()]
        return Response(
            {"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def get_object(self, pk):
        try:
            quiz_attempt = QuizAttempt.objects.get(id=pk)
            course = quiz_attempt.quiz.video.course
        except QuizAttempt.DoesNotExist:
            raise QuizAttempt.DoesNotExist({"error": "QuizAttempt not found"})
        except Exception as e:
            return APIException({"error": str(e)})
        self.check_object_permissions(self.request, course)
        student = quiz_attempt.student
        if not (
            Enrollment.objects.filter(
                course=quiz_attempt.quiz.video.course,
                student=student,
                status="approved",
                instructor=self.request.user.id,
            ).exists()
        ):
            raise APIException(
                {"error": "You are not authorized for this quiz attempt"}
            )
        return quiz_attempt

    def get(self, request, pk):
        try:
            quiz_attempt = self.get_object(pk)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = QuizAttemptSerializer(quiz_attempt)
        return Response(serializer.data)

    # used for student to attempt the quiz
    # expects quiz id and all the ralated question id's with answers
    def post(self, request):
        try:
            quiz = Quiz.objects.get(id=request.data.get("quiz"))
            course = quiz.video.course
        except Quiz.DoesNotExist:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(self.request, course)

        request.data["student"] = request.user.id

        quiz_serializer = QuizAttemptSerializer(
            fields=["quiz", "student"], data=request.data
        )

        if not quiz_serializer.is_valid():
            return Response(quiz_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            quiz_serializer.save()
            return Response(
                {"message": "Your Quiz Attempt Saved Successfully"},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # used for Instructor to evaluate the quiz attempt
    # requires quiz_attempt id and list of answerattempt id's with is_correct field
    def put(self, request, pk):
        try:
            quiz_attempt = self.get_object(pk)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        quiz_attempt_serializer = QuizAttemptSerializer(
            quiz_attempt,
            data=request.data,
            fields=["answers", "qualified_status"],
            partial=True,
        )
        if not quiz_attempt_serializer.is_valid():
            return Response(
                quiz_attempt_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            quiz_attempt_serializer.save()
            return Response(quiz_attempt_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            quiz_attempt = self.get_object(pk)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        quiz_attempt.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
