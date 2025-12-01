"""
Django management command to seed initial plan data.
Run: python manage.py seed_plans
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from authentication.models import Plan, PlanPricing
from authentication import enums


class Command(BaseCommand):
    help = 'Seed initial plan data (FREE, JUNIOR, MASTER) and pricing'

    def handle(self, *args, **options):
        self.stdout.write('Seeding plan data...')
        
        # Create FREE plan
        free_plan, created = Plan.objects.get_or_create(
            name=enums.Plan.FREE,
            defaults={
                'display_name': 'Free Plan',
                'course_content_percentage': 60,
                'has_activities': False,
                'has_quizzes': False,
                'has_games': False,
                'shows_ads': True,
                'allows_multiple_profiles': False,
                'master_discount_amount': Decimal('0.00'),
                'yearly_discount_percentage': Decimal('0.00'),
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created FREE plan'))
        else:
            self.stdout.write(self.style.WARNING(f'→ FREE plan already exists'))
        
        # Create JUNIOR plan
        junior_plan, created = Plan.objects.get_or_create(
            name=enums.Plan.JUNIOR,
            defaults={
                'display_name': 'Junior Plan',
                'course_content_percentage': 100,
                'has_activities': True,
                'has_quizzes': True,
                'has_games': True,
                'shows_ads': False,
                'allows_multiple_profiles': False,
                'master_discount_amount': Decimal('0.00'),
                'yearly_discount_percentage': Decimal('0.00'),
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created JUNIOR plan'))
        else:
            self.stdout.write(self.style.WARNING(f'→ JUNIOR plan already exists'))
        
        # Create MASTER plan
        master_plan, created = Plan.objects.get_or_create(
            name=enums.Plan.MASTER,
            defaults={
                'display_name': 'Master Plan',
                'course_content_percentage': 100,
                'has_activities': True,
                'has_quizzes': True,
                'has_games': True,
                'shows_ads': False,
                'allows_multiple_profiles': True,
                'master_discount_amount': Decimal('20.00'),  # ₹20 discount
                'yearly_discount_percentage': Decimal('0.00'),
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created MASTER plan'))
        else:
            self.stdout.write(self.style.WARNING(f'→ MASTER plan already exists'))
        
        # Create PlanPricing for JUNIOR plan
        pricing_data = [
            {'grade': enums.Grade.NURSERY, 'monthly_price': Decimal('120.00')},
            {'grade': enums.Grade.LKG, 'monthly_price': Decimal('150.00')},
            {'grade': enums.Grade.UKG, 'monthly_price': Decimal('180.00')},
        ]
        
        for pricing_info in pricing_data:
            pricing, created = PlanPricing.objects.get_or_create(
                plan=junior_plan,
                grade=pricing_info['grade'],
                defaults={
                    'monthly_price': pricing_info['monthly_price'],
                    'yearly_price': pricing_info['monthly_price'] * Decimal('12'),
                    'yearly_discount_percentage': Decimal('0.00'),
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created pricing for JUNIOR - {pricing.get_grade_display()}: ₹{pricing.monthly_price}/month'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'→ Pricing for JUNIOR - {pricing.get_grade_display()} already exists'
                    )
                )
        
        self.stdout.write(self.style.SUCCESS('\n✓ Plan seeding completed successfully!'))

