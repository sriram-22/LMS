from rest_framework.permissions import BasePermission
from .models import *

class IsAdminUserRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "admin"

class IsInstructorUserRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "instructor"

class IsStudentUserRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "student"

class IsAdminOrInstructor(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "admin" or request.user.role == "instructor"

class IsAdminOrStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "admin" or request.user.role == "student"
class IsUser(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj

class IsUserorAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj or request.user.role == "admin"

class IsAdminOrInstructorOrStudentRelatedToCourse(BasePermission):
    def has_object_permission(self, request, view, course):
        return ((request.user.role == "admin") or (request.user in course.instructor.all()) or (Enrollment.objects.filter(course=course, student = request.user, status = "approved").exists()))
                
class IsAdminOrInstructorRelatedToCourse(BasePermission):
    def has_object_permission(self, request, view, course):
        return ((request.user.role == "admin") or (request.user in course.instructor.all()))
                
class IsStudentRelatedToCourse(BasePermission):
    def has_object_permission(self, request, view, course):
        return (Enrollment.objects.filter(course=course, student = request.user, status = "approved").exists())

class IsInstructorRelatedToCourse(BasePermission):
    def has_object_permission(self, request, view, course):
        return (request.user in course.instructor.all())
    
# class IsInstructorCourseAndStudentAreRelated(BasePermission):
#     def has_object_permission(self, request, view, enrollment):
#         return (request.user in enrollment.course.instructor.all())
