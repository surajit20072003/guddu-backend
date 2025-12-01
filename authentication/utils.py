"""
Utility functions for plan pricing and subscription management.
"""
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .models import Plan, PlanPricing, Subscription, ProfileSubscription, UserProfile
from . import enums


def calculate_subscription_price(plan_name, duration, grade=None, profile_ids=None):
    """
    Calculate subscription price based on plan, duration, and grade/profiles.
    
    Args:
        plan_name: Plan name (FREE, JUNIOR, MASTER)
        duration: Subscription duration (MONTHLY, YEARLY)
        grade: Grade for JUNIOR plan (Nursery, LKG, UKG)
        profile_ids: List of profile IDs for MASTER plan
    
    Returns:
        dict with 'monthly_amount', 'total_amount', 'breakdown'
    """
    try:
        plan = Plan.objects.get(name=plan_name, is_active=True)
    except Plan.DoesNotExist:
        raise ValueError(f"Plan '{plan_name}' not found or inactive")
    
    # FREE plan
    if plan_name == enums.Plan.FREE:
        return {
            'monthly_amount': Decimal('0.00'),
            'total_amount': Decimal('0.00'),
            'breakdown': {
                'plan': plan.display_name,
                'duration': duration,
                'base_monthly': Decimal('0.00'),
                'discount': Decimal('0.00'),
                'yearly_discount_percentage': Decimal('0.00'),
            }
        }
    
    # JUNIOR plan - grade-based pricing
    if plan_name == enums.Plan.JUNIOR:
        if not grade:
            raise ValueError("Grade is required for JUNIOR plan")
        
        if grade not in [enums.Grade.NURSERY, enums.Grade.LKG, enums.Grade.UKG]:
            raise ValueError(f"Invalid grade '{grade}' for JUNIOR plan. Must be Nursery, LKG, or UKG")
        
        try:
            pricing = PlanPricing.objects.get(plan=plan, grade=grade, is_active=True)
        except PlanPricing.DoesNotExist:
            raise ValueError(f"Pricing not found for {plan.display_name} - {grade}")
        
        monthly_amount = pricing.monthly_price
        
        if duration == enums.SubscriptionDuration.MONTHLY:
            total_amount = monthly_amount
        else:  # YEARLY
            yearly_base = pricing.yearly_price
            # Apply yearly discount if set
            discount_percentage = plan.yearly_discount_percentage
            if discount_percentage > 0:
                discount_amount = yearly_base * (discount_percentage / Decimal('100'))
                total_amount = yearly_base - discount_amount
            else:
                total_amount = yearly_base
        
        return {
            'monthly_amount': monthly_amount,
            'total_amount': total_amount,
            'breakdown': {
                'plan': plan.display_name,
                'grade': pricing.get_grade_display(),
                'duration': duration,
                'base_monthly': monthly_amount,
                'base_yearly': pricing.yearly_price if duration == enums.SubscriptionDuration.YEARLY else None,
                'yearly_discount_percentage': plan.yearly_discount_percentage,
                'discount_amount': total_amount - (monthly_amount * Decimal('12')) if duration == enums.SubscriptionDuration.YEARLY else Decimal('0.00'),
            }
        }
    
    # MASTER plan - sum of profile prices minus discount
    if plan_name == enums.Plan.MASTER:
        if not profile_ids:
            raise ValueError("Profile IDs are required for MASTER plan")
        
        if not isinstance(profile_ids, list) or len(profile_ids) == 0:
            raise ValueError("At least one profile ID is required for MASTER plan")
        
        # Get all profiles
        profiles = UserProfile.objects.filter(id__in=profile_ids)
        if profiles.count() != len(profile_ids):
            raise ValueError("One or more profile IDs are invalid")
        
        # Calculate sum of all profile prices
        total_monthly = Decimal('0.00')
        profile_breakdown = []
        
        for profile in profiles:
            if not profile.grade:
                raise ValueError(f"Profile '{profile.full_name}' does not have a grade set")
            
            if profile.grade not in [enums.Grade.NURSERY, enums.Grade.LKG, enums.Grade.UKG]:
                raise ValueError(f"Profile '{profile.full_name}' has invalid grade '{profile.grade}' for MASTER plan")
            
            try:
                # Use JUNIOR plan pricing for each profile
                junior_plan = Plan.objects.get(name=enums.Plan.JUNIOR, is_active=True)
                pricing = PlanPricing.objects.get(plan=junior_plan, grade=profile.grade, is_active=True)
                profile_monthly = pricing.monthly_price
                total_monthly += profile_monthly
                
                profile_breakdown.append({
                    'profile_id': profile.id,
                    'profile_name': profile.full_name,
                    'grade': pricing.get_grade_display(),
                    'monthly_price': profile_monthly,
                })
            except PlanPricing.DoesNotExist:
                raise ValueError(f"Pricing not found for grade '{profile.grade}'")
        
        # Apply MASTER discount
        discount_amount = plan.master_discount_amount
        monthly_amount = total_monthly - discount_amount
        
        if monthly_amount < 0:
            monthly_amount = Decimal('0.00')
        
        if duration == enums.SubscriptionDuration.MONTHLY:
            total_amount = monthly_amount
        else:  # YEARLY
            yearly_base = monthly_amount * Decimal('12')
            # Apply yearly discount if set
            discount_percentage = plan.yearly_discount_percentage
            if discount_percentage > 0:
                discount = yearly_base * (discount_percentage / Decimal('100'))
                total_amount = yearly_base - discount
            else:
                total_amount = yearly_base
        
        return {
            'monthly_amount': monthly_amount,
            'total_amount': total_amount,
            'breakdown': {
                'plan': plan.display_name,
                'duration': duration,
                'profiles': profile_breakdown,
                'total_profiles_monthly': total_monthly,
                'master_discount': discount_amount,
                'final_monthly': monthly_amount,
                'yearly_discount_percentage': plan.yearly_discount_percentage,
                'discount_amount': total_amount - (monthly_amount * Decimal('12')) if duration == enums.SubscriptionDuration.YEARLY else Decimal('0.00'),
            }
        }
    
    raise ValueError(f"Unsupported plan: {plan_name}")


def create_subscription(user, plan_name, duration, grade=None, profile_ids=None, start_date=None):
    """
    Create a new subscription for a user.
    
    Args:
        user: User instance
        plan_name: Plan name (FREE, JUNIOR, MASTER)
        duration: Subscription duration (MONTHLY, YEARLY)
        grade: Grade for JUNIOR plan (required for JUNIOR)
        profile_ids: List of profile IDs for MASTER plan (required for MASTER)
        start_date: Optional start date (defaults to now)
    
    Returns:
        Subscription instance
    """
    # Calculate price
    price_info = calculate_subscription_price(plan_name, duration, grade, profile_ids)
    
    # Get plan
    plan = Plan.objects.get(name=plan_name, is_active=True)
    
    # Set start date
    if not start_date:
        start_date = timezone.now()
    
    # Calculate end date
    if duration == enums.SubscriptionDuration.MONTHLY:
        end_date = start_date + timedelta(days=30)
    else:  # YEARLY
        end_date = start_date + timedelta(days=365)
    
    # Deactivate any existing active subscriptions
    Subscription.objects.filter(
        user=user,
        status=enums.SubscriptionStatus.ACTIVE
    ).update(status=enums.SubscriptionStatus.CANCELLED)
    
    # Create subscription
    subscription = Subscription.objects.create(
        user=user,
        plan=plan,
        duration=duration,
        status=enums.SubscriptionStatus.ACTIVE,
        start_date=start_date,
        end_date=end_date,
        renewal_date=end_date,  # Set renewal date for auto-renewal
        is_auto_renew=True,  # Default on
        monthly_amount=price_info['monthly_amount'],
        total_amount_paid=price_info['total_amount'],
        pricing_grade=grade if plan_name == enums.Plan.JUNIOR else None,
    )
    
    # For MASTER plan, create ProfileSubscription entries
    if plan_name == enums.Plan.MASTER and profile_ids:
        profiles = UserProfile.objects.filter(id__in=profile_ids)
        for profile in profiles:
            # Get pricing for this profile's grade
            junior_plan = Plan.objects.get(name=enums.Plan.JUNIOR, is_active=True)
            pricing = PlanPricing.objects.get(plan=junior_plan, grade=profile.grade, is_active=True)
            
            ProfileSubscription.objects.create(
                subscription=subscription,
                profile=profile,
                grade=profile.grade,
                monthly_price=pricing.monthly_price,
            )
            
            # Link profile to subscription
            profile.subscription = subscription
            profile.save()
    
    return subscription


def validate_profile_limits(user, plan_name):
    """
    Validate if user can create more profiles based on their plan.
    
    Args:
        user: User instance
        plan_name: Plan name to check
    
    Returns:
        dict with 'can_create', 'current_count', 'max_allowed', 'message'
    """
    current_profiles_count = UserProfile.objects.filter(user=user).count()
    
    if plan_name == enums.Plan.FREE:
        max_allowed = 1
        can_create = current_profiles_count < max_allowed
        return {
            'can_create': can_create,
            'current_count': current_profiles_count,
            'max_allowed': max_allowed,
            'message': 'FREE plan allows only 1 profile' if not can_create else 'You can create 1 profile',
        }
    
    # Check if user has active subscription
    try:
        active_subscription = Subscription.objects.get(
            user=user,
            status=enums.SubscriptionStatus.ACTIVE,
            end_date__gt=timezone.now()
        )
        
        if active_subscription.plan.name != plan_name:
            return {
                'can_create': False,
                'current_count': current_profiles_count,
                'max_allowed': None,
                'message': f'You have an active {active_subscription.plan.display_name} subscription. Cannot create profiles for {plan_name} plan.',
            }
    except Subscription.DoesNotExist:
        return {
            'can_create': False,
            'current_count': current_profiles_count,
            'max_allowed': None,
            'message': f'You need an active {plan_name} subscription to create profiles.',
        }
    
    if plan_name == enums.Plan.JUNIOR:
        max_allowed = 1
        can_create = current_profiles_count < max_allowed
        return {
            'can_create': can_create,
            'current_count': current_profiles_count,
            'max_allowed': max_allowed,
            'message': 'JUNIOR plan allows only 1 profile' if not can_create else 'You can create 1 profile',
        }
    
    if plan_name == enums.Plan.MASTER:
        # MASTER plan allows unlimited profiles (no hard limit)
        return {
            'can_create': True,
            'current_count': current_profiles_count,
            'max_allowed': None,  # Unlimited
            'message': 'MASTER plan allows multiple profiles',
        }
    
    return {
        'can_create': False,
        'current_count': current_profiles_count,
        'max_allowed': None,
        'message': f'Unknown plan: {plan_name}',
    }

