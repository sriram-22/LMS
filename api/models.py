from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group, Permission
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=100, unique=True)
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role, default="student")
    groups = models.ManyToManyField(Group,related_name='custom_user_groups',blank=True,)
    user_permissions = models.ManyToManyField(Permission,related_name='custom_user_permissions',blank=True,)
    
    def __str__(self):
        return self.username
    

    
class CourseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

class CourseManager(models.Manager):
    def get_queryset(self):
        return CourseQuerySet(self.model, using=self._db).active()


class Course(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    instructors = models.ManyToManyField(User, related_name="courses",blank=True)
    description = models.TextField()
    likes = models.PositiveIntegerField(default=0)
    total_ratings = models.PositiveIntegerField(default=0) #count
    rating = models.FloatField(default=0.0) #average
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True,blank=True)

    #managers
    objects = CourseManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.name
    
    def delete(self, using = None, keep_parents = False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

   
class Enrollment(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_enrollments") 
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
    status = models.CharField(max_length=20, choices=Status, default="pending")

    class Meta:
        unique_together = ["course", "student"]

    def __str__(self):
        return f"{self.course.name} - {self.student.username}"
    

class CourseVideo(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="videos")
    title = models.CharField(max_length=100)
    video = models.FileField(upload_to="videos/")
    order = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order:
            last_video = CourseVideo.objects.filter(course=self.course).order_by("-order").first()
            if last_video:
                self.order = last_video.order + 1
            else:
                self.order = 1
        super().save(*args, **kwargs)
     

    def __str__(self):
        return f"{self.course.name} - {self.title}"
    
    class Meta:
        ordering = ["-created_at"]

class CourseComment(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null= True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.name} - {self.user.username}"
    
    class Meta:
        ordering = ["-created_at"]


     
class CourseLike(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["course", "user"]

    def __str__(self):
        return f"{self.course.name} - {self.user.username}"


class CourseRating(models.Model):
    class RatingChoices(models.IntegerChoices):
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4
        FIVE = 5

    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete= models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=RatingChoices.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["course", "user"]

class CourseProgressTracking(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    completed_videos = models.ManyToManyField(CourseVideo, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ["student", "course"]
    
    def __str__(self):
        return f"{self.student.username} - {self.course.name}"
    


class Quiz(models.Model):
    id = models.AutoField(primary_key=True)
    video = models.ForeignKey(CourseVideo, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=100)
    description = models.TextField()
    total_marks = models.PositiveIntegerField(default=0)
    passing_marks = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Question(models.Model):
    # class QuestionType(models.TextChoices):
    #     TRUE_FALSE = "TF", "True/False"
    #     MULTIPLE_CHOICE = "MCQ", "Multiple Choice"
    #     SINGLE_OPTION = "OPTION", "Single Option"
    #     Text = "Text", "Text"

    id = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE,related_name="questions")
    question = models.TextField()
    # question_type = models.CharField(max_length=20, choices=QuestionType, default=QuestionType.Text)
    marks = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# class Answer(models.Model):
#     id = models.AutoField(primary_key=True)
#     question = models.ForeignKey(Question, on_delete=models.CASCADE)
#     answer = models.TextField()
#     is_correct = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         unique_together = ["question", "answer"]

class QuizAttempt(models.Model):
    class QualifiedStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"

    id = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="quiz_attempts")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts")
    marks_obtained = models.PositiveIntegerField(default=0)
    qualified_status = models.CharField(max_length=20, choices=QualifiedStatus, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

class AnswerAttempt(models.Model):
    id = models.AutoField(primary_key=True)
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    answer = models.TextField()
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ["quiz_attempt", "question"]
