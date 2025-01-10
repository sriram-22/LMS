from api.serializer import CourseSerializer
from api.models import User, Course
from api.factories import UserFactory, CourseFactory
import random
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Generate dummy data'

    def handle(self, *args, **options):
        instructors = UserFactory.create_batch(3)
        for _ in range(10):
            course = CourseFactory(instructor=random.sample(instructors, 3))

    # data = {
    #     'name': faker.sentence(nb_words=4),
    #     'description': faker.paragraph(nb_sentences=5),
    #     'likes': faker.random_int(min=0, max=1000),
    #     'total_ratings': faker.random_int(min=0, max=500),
    #     'rating': round(faker.random.uniform(1, 5), 1),
    #     'instructor': [instructor.id for instructor in instructors[:3]]  # Take first 3 instructors
    # }

