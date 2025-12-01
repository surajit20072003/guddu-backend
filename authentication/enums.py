from django.db import models

class AccountFor(models.TextChoices):
    SELF = 'SELF', 'Self'
    CHILD = 'CHILD', 'Child'

class ChildAge(models.TextChoices):
    AGE_2_0 = '2.0', '2.0 years'
    AGE_2_5 = '2.5', '2.5 years'
    AGE_3_0 = '3.0', '3.0 years'
    AGE_3_5 = '3.5', '3.5 years'
    AGE_4_0 = '4.0', '4.0 years'
    AGE_4_5 = '4.5', '4.5 years'
    AGE_5_0 = '5.0', '5.0 years'
    AGE_5_5 = '5.5', '5.5 years'
    AGE_6_0 = '6.0', '6.0 years'

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
    # Pre-school grades (used for pricing)
    NURSERY = 'NURSERY', 'Nursery'
    LKG = 'LKG', 'LKG'
    UKG = 'UKG', 'UKG'
    # School classes (kept for future use)
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


class SubscriptionDuration(models.TextChoices):
    MONTHLY = 'MONTHLY', 'Monthly'
    YEARLY = 'YEARLY', 'Yearly'


class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'
    PENDING = 'PENDING', 'Pending'
