from rest_framework import serializers
from django.db.models import Sum
from .models import *
from django.db import transaction
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

class BaseModelSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        fields = set(kwargs.pop("fields", []))
        exclude = set(kwargs.pop("exclude", []))
        super().__init__(*args, **kwargs)
        
        if fields:
            self.fields = {k: v for k, v in self.fields.items() if k in fields}
        
        if exclude:
            for field_name in exclude:
                self.fields.pop(field_name, None)



class Loginserializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        user = authenticate(username=   username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("The account is inactive.")
        attrs['user'] = user
        return attrs

class UserSerializer(BaseModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password","password2", "role"]
        extra_kwargs = {
            "password": {"write_only": True}
        }
    

    def validate(self, attrs):
        if "password" in attrs and "password2" in attrs:
            if attrs["password"] != attrs["password2"]:
                raise serializers.ValidationError({"password": "Password fields didn't match."})

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(**validated_data)
        return user
    
class UpadateUserPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate_current_password(self,value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Invalid current password")
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError("Passwords do not match")
        validate_password(attrs['password'], user)
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['password'])
        user.save()
        return user




class CourseSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField(read_only=True)
    instructors = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many = True, required = False)

    class Meta:
        model = Course
        fields = ["id", "name", "description", "instructors", "likes", "comments", "rating"]
        extra_kwargs = {
            "likes": {"read_only": True},
            "rating": {"read_only": True}
        }

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)
        if fields:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    def validate(self, attrs):
        if "instructors" in attrs:
            instructors = attrs["instructors"]
            valid_instructors = User.objects.filter(id__in=instructors, role="instructor")
            if len(instructors) != len(valid_instructors):
                raise serializers.ValidationError("Invalid instructor id")
        return attrs

    def get_comments(self, obj):
        comments = CourseComment.objects.filter(course=obj)
        return CourseCommentSerializer(comments, many=True).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if "instructors" in representation:
            representation["instructors"] = UserSerializer(instance.instructors, fields=["id", "username"], many=True).data
        return representation


class EnrollmentSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    instructor = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    

    def validate(self, attrs):
        instructor = attrs.get('instructor')
        if instructor and instructor.role != "instructor":
            raise serializers.ValidationError({"instructor":"The instructor must have the role 'instructor'."})
        return super().validate(attrs)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["student"] = UserSerializer(instance.student, fields=["id", "username"]).data
        representation["instructor"] = UserSerializer(instance.instructor, fields=["id", "username"]).data if instance.instructor else None
        representation["course"] = CourseSerializer(instance.course, fields=["id", "name"]).data
        return representation
    
    class Meta:
        model = Enrollment
        fields = "__all__"

    
    
class CourseVideoSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())

    class Meta:
        model = CourseVideo
        
        fields = ["id", "course", "title", "video", "order", "created_at", "updated_at"]
        extra_kwargs = {
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
            "order": {"required": False}
        }
    
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)
        if fields:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

class CourseCommentSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), write_only=True)
    user = UserSerializer(read_only=True)
    class Meta:
        model = CourseComment
        fields = "__all__"
        extra_kwargs = {
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        

class CourseLikeSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = CourseLike
        fields = "__all__"
        extra_kwargs = {
            "created_at": {"read_only": True},
        }

class CourseRatingSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = CourseRating
        fields = "__all__"
        extra_kwargs = {
            "created_at": {"read_only": True},
        }

class CourseProgressTrackingSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    completion_percentage = serializers.SerializerMethodField()
    remaining_videos = serializers.SerializerMethodField()

    class Meta:
        model = CourseProgressTracking
        fields = "__all__"
        extra_kwargs = {
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }
    
    def get_completion_percentage(self, obj):
        total_videos = obj.course.videos.count()
        completed_videos = obj.completed_videos.count()
        if total_videos == 0:
            return 0 
        return (completed_videos / total_videos) * 100

    def get_remaining_videos(self, obj):
        total_videos = obj.course.videos.all()
        completed_videos = obj.completed_videos.all()
        remaining_videos = total_videos.exclude(id__in=completed_videos.values_list('id', flat=True))
        return CourseVideoSerializer(remaining_videos, fields=["id", "title","video" "order"], many=True).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["course"] = CourseSerializer(instance.course, fields=["id", "name"]).data
        representation["student"] = UserSerializer(instance.student, fields=["id", "username"]).data
        representation["completed_videos"] = CourseVideoSerializer(instance.completed_videos.all(),fields=["id", "title", "video", "order",], many=True).data
        return representation


# class AnswerSerializer(serializers.ModelSerializer):
#     question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())

#     def __init__(self, *args, **kwargs):
#         fields = kwargs.pop("fields", None)
#         super().__init__(*args, **kwargs)
#         if fields:
#             allowed = set(fields)
#             existing = set(self.fields.keys())
#             for field_name in existing - allowed:
#                 self.fields.pop(field_name)

#     class Meta:
#         model = Answer
#         fields = "__all__"

class QuestionSerializer(serializers.ModelSerializer):
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)
        if fields:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    class Meta:
        model = Question
        fields = "__all__"

class QuizSerializer(serializers.ModelSerializer):
    video = serializers.PrimaryKeyRelatedField(queryset=CourseVideo.objects.all())
    questions = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)
        if fields:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    class Meta:
        model = Quiz
        fields = "__all__"
    
    def get_questions(self, obj):
        questions = Question.objects.filter(quiz=obj)
        return QuestionSerializer(questions, fields=["id", "question", "marks"], many=True).data
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["video"] = CourseVideoSerializer(instance.video, fields=["id", "title"]).data
        return representation   
    

class AnswerAttemptSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    quiz_attempt = serializers.PrimaryKeyRelatedField(queryset=QuizAttempt.objects.all())
    
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)
        if fields:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    class Meta:
        model = AnswerAttempt
        fields = "__all__"
        extra_kwargs = {
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["question"] = QuestionSerializer(instance.question, fields=["id", "question", "marks"]).data
        return representation
    
class QuizAttemptSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)
        if fields:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    class Meta:
        model = QuizAttempt
        fields = "__all__"
        extra_kwargs = {
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def validate(self, data):
        answers = self.initial_data.get("answers", [])

        if self.instance:
            existing_answers = AnswerAttempt.objects.filter(quiz_attempt=self.instance)
            given_answers_ids = [answer["id"] for answer in answers]
            if existing_answers.count() != len(given_answers_ids):
                raise serializers.ValidationError({"error": "Invalid answer id"})
            given_quiz_answers = AnswerAttempt.objects.filter(id__in=given_answers_ids, quiz_attempt=self.instance)
            if given_quiz_answers.count() != len(given_answers_ids):
                raise serializers.ValidationError({"error": "Invalid answer id"})
            if not given_answers_ids:
                raise serializers.ValidationError({"error": "No answers found for this quiz attempt."})
        else:
            quiz_id = self.initial_data.get("quiz")
            quiz = Quiz.objects.get(id=quiz_id)
            if quiz.questions.all().count() != len(answers):
                raise serializers.ValidationError({"error": "Invalid question id 1"})
            
            given_quiz_questions_ids = [answer['question'] for answer in answers]
            given_quiz_questions = Question.objects.filter(id__in=given_quiz_questions_ids, quiz=quiz)
            if given_quiz_questions.count() != len(answers):
                raise serializers.ValidationError({"error": "Invalid question id 2"})
            if quiz.questions.all().count() == 0:
                raise serializers.ValidationError({"error": "No questions found for this quiz."})
            
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        answers = self.initial_data.pop("answers")
        quiz_attempt = QuizAttempt.objects.create(**validated_data)
        validated_answers = []
        for answer in answers:
            answer["quiz_attempt"] = quiz_attempt.id
            answer_serializer = AnswerAttemptSerializer(fields = ["quiz_attempt","question","answer"], data=answer)
            if answer_serializer.is_valid(raise_exception=True):
                validated_answers.append(AnswerAttempt(**answer_serializer.validated_data))
        AnswerAttempt.objects.bulk_create(validated_answers)
        return quiz_attempt

    @transaction.atomic
    def update(self, instance, validated_data):
        answers = self.initial_data.pop("answers")
        for answer in answers:
            answer_instance = AnswerAttempt.objects.get(id=answer["id"])
            answer_serializer = AnswerAttemptSerializer(answer_instance, fields = ["id","is_correct"], data=answer)
            if answer_serializer.is_valid():
                answer_serializer.save()
            else:
                raise serializers.ValidationError(answer_serializer.errors)
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["student"] = UserSerializer(instance.student, fields=["id", "username"]).data
        representation["quiz"] = QuizSerializer(instance.quiz, fields=["id", "name"]).data
        representation["answers"] = AnswerAttemptSerializer(instance.answers.all(), fields= ["id","question","answer","is_correct"], many=True).data
        return representation

