from django.db import models

class MotherTongue(models.TextChoices):
    ENGLISH = 'EN', 'English'
    HINDI = 'HI', 'Hindi'
    TAMIL = 'TA', 'Tamil'
    TELUGU = 'TE', 'Telugu'
    MALAYALAM = 'ML', 'Malayalam'
    KANNADA = 'KN', 'Kannada'
    BENGALI = 'BN', 'Bengali'
    MARATHI = 'MR', 'Marathi'
    GUJARATI = 'GU', 'Gujarati'
    URDU = 'UR', 'Urdu'
    ODIA = 'OR', 'Odia'
    OTHERS = 'OT', 'Others'

class SchoolType(models.TextChoices):
    PRIVATE = 'PRIVATE', 'Private'
    GOVERNMENT = 'GOVERNMENT', 'Government'

class Grade(models.TextChoices):
    CLASS_1 = '1', 'Class 1'
    CLASS_2 = '2', 'Class 2'
    CLASS_3 = '3', 'Class 3'
    CLASS_4 = '4', 'Class 4'
    CLASS_5 = '5', 'Class 5'
    CLASS_6 = '6', 'Class 6'
    CLASS_7 = '7', 'Class 7'
    CLASS_8 = '8', 'Class 8'
    CLASS_9 = '9', 'Class 9'
    CLASS_10 = '10', 'Class 10'
    CLASS_11 = '11', 'Class 11'
    CLASS_12 = '12', 'Class 12'
    BELOW_CLASS_5 = 'BC5', 'Below Class 5th'

class Plan(models.TextChoices):
    FREE = 'FREE', 'Free'
    JUNIOR = 'JUNIOR', 'Junior'
    MASTER = 'MASTER', 'Master'
