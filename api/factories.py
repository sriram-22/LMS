import factory
from faker import Faker
from api.models import User, Course
from django.contrib.auth.hashers import make_password

facker = Faker()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    role = factory.LazyFunction(lambda : User.Role.INSTRUCTOR)
    password = factory.LazyAttribute(lambda x: make_password("password"))

class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    name = factory.Faker('sentence', nb_words=4) 
    description = factory.Faker('paragraph', nb_sentences = 5)
    likes = factory.LazyAttribute(lambda x: facker.random_int())
    total_ratings = factory.LazyAttribute(lambda x: facker.random_int())
    rating = factory.LazyAttribute(lambda x: round(facker.random_int(1,5), 1))


    @factory.post_generation
    def instructor(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.instructor.set(extracted)
        else:
            self.instructor.set(UserFactory.create_batch(3))