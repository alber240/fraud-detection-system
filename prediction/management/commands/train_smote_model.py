from django.core.management.base import BaseCommand
from prediction.train_with_smote import train_with_smote


class Command(BaseCommand):
    help = 'Train fraud detection models with SMOTE class balancing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='ml_model/creditcard.csv',
            help='Path to CSV dataset file'
        )
    
    def handle(self, *args, **options):
        csv_path = options['csv']
        self.stdout.write(self.style.SUCCESS(f'Starting SMOTE training on {csv_path}'))
        
        try:
            trainer = train_with_smote(csv_path)
            self.stdout.write(self.style.SUCCESS('✅ Training completed successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Training failed: {e}'))