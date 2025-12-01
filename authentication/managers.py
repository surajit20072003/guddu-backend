from django.contrib.auth.base_user import BaseUserManager

class CustomUserManager(BaseUserManager):
    """
    Custom manager that creates users with either email or mobile.
    """
    def create_user(self, email=None, mobile=None, password=None, **extra_fields):
        if not email and not mobile:
            raise ValueError('Either email or mobile is required')
        
        if email:
            email = self.normalize_email(email)
            extra_fields['email'] = email
        
        if mobile:
            # Clean mobile number (remove spaces, dashes, etc.)
            mobile = ''.join(filter(str.isdigit, mobile))
            extra_fields['mobile'] = mobile
        
        user = self.model(**extra_fields)
        if password:
            user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email=None, mobile=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email=email, mobile=mobile, password=password, **extra_fields)

