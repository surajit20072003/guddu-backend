from django.contrib.auth.base_user import BaseUserManager

class CustomUserManager(BaseUserManager):
    """
    Ek custom manager jo email se user banata hai, username se nahi.
    """
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email zaroori hai')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser ke liye is_staff=True hona chahiye.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser ke liye is_superuser=True hona chahiye.')
            
        return self.create_user(email, password, **extra_fields)

