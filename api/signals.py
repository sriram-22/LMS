from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import *
from django.db import transaction
from django.db.models import Sum

@receiver(pre_save, sender=User)
def ensure_single_admin(sender, instance, **kwargs):
    if instance.role == User.Role.ADMIN:
        existing_admins = User.objects.filter(role=User.Role.ADMIN).exclude(id=instance.id)
        if existing_admins.exists():
            raise ValidationError("There can only be one admin user.")

@receiver(post_save, sender=CourseLike)
def AddLike(sender, instance, created, **kwargs):
    if created:
        course = Course.objects.select_for_update().get(id=instance.course.id)
        course.likes += 1
        course.save()

@receiver(post_delete, sender=CourseLike)
def RemoveLike(sender, instance, **kwargs):
    course = Course.objects.select_for_update().get(id=instance.course.id)
    course.likes -= 1
    course.save()

@receiver(pre_save, sender=CourseRating)
def capture_old_rating(sender, instance, **kwargs):
    """Capture the old rating before updating."""
    if instance.id:
        old_rating = CourseRating.objects.get(id=instance.id).rating
        instance._old_rating = old_rating
    else:
        instance._old_rating = None

@receiver(post_save, sender=CourseRating)
def create_and_update_course_rating(sender, instance, created, **kwargs):
    """Signal receiver to update the course's average rating after a rating is added or updated."""
    with transaction.atomic():
        course = Course.objects.select_for_update().get(id=instance.course.id)
        new_rating = instance.rating
        sum_ratings = course.total_ratings * course.rating

        if created:
            course.total_ratings += 1
            new_avg_rating = (sum_ratings + instance.rating) / (course.total_ratings)
        else:
            old_rating = instance._old_rating
            new_avg_rating = (sum_ratings + instance.rating - old_rating) / course.total_ratings
         
            
        course.rating = new_avg_rating
        course.save()

@receiver(post_delete, sender=CourseRating)
def delete_course_rating(sender, instance, **kwargs):
    """Signal receiver to update the course's average rating after a rating is deleted."""
    with transaction.atomic():
        course = Course.objects.select_for_update().get(id=instance.course.id)
        sum_ratings = course.total_ratings * course.rating
        course.total_ratings -= 1
        if course.total_ratings <= 0:
            course.rating = 0
            course.total_ratings = 0
        else:
            course.rating = (sum_ratings - instance.rating) / course.total_ratings
        course.save()


#updating the total marks everytime a new question is added
@receiver(post_save, sender=Question)
def update_quiz_total_marks(sender, instance, created, **kwargs):
    with transaction.atomic():
        total_marks = Question.objects.filter(quiz=instance.quiz).aggregate(total_marks=models.Sum('marks'))['total_marks']
        instance.quiz.total_marks = total_marks
        instance.quiz.passing_marks = total_marks * 70/100
        instance.quiz.save()
    
@receiver(post_delete, sender=Question)
def update_quiz_total_marks(sender, instance, **kwargs):
    with transaction.atomic():
        total_marks = Question.objects.filter(quiz=instance.quiz).aggregate(total_marks=models.Sum('marks'))['total_marks']
        instance.quiz.total_marks = total_marks
        instance.quiz.passing_marks = total_marks * 70/100
        instance.quiz.save()

@receiver(post_save, sender=AnswerAttempt)
def update_quiz_attempt_marks_obtained(sender, instance, created, **kwargs):
    if not created:
        with transaction.atomic():
            marks_obtained = AnswerAttempt.objects.filter(quiz_attempt=instance.quiz_attempt, is_correct = True).aggregate(marks_obtained=Sum('question__marks'))['marks_obtained'] or 0
            instance.quiz_attempt.marks_obtained = marks_obtained
            if marks_obtained >= instance.quiz_attempt.quiz.passing_marks:
                instance.quiz_attempt.qualified_status = QuizAttempt.QualifiedStatus.PASSED
            else:
                instance.quiz_attempt.qualified_status = QuizAttempt.QualifiedStatus.FAILED
            instance.quiz_attempt.save()
    
