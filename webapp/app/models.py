from django.db import models

# Create your models here.
class Login(models.Model):
    username = models.CharField(max_length=255)
    email = models.EmailField()
    password = models.CharField(max_length=255)

class Features(models.Model):
    sleeperType = models.CharField(max_length=255)
    PersonalityType = models.CharField(max_length=255)
    CleanlinessTolerance = models.CharField(max_length=255)
    studyEnvironment = models.CharField(max_length=255)
    

