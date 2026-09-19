from django.core.management.base import BaseCommand

from core.models import ColorDefinition

DEFAULT_COLORS = [
    (1, "#000000", "Black", 1),
    (2, "#FFFFFF", "White", 2),
    (3, "#FF0000", "Red", 3),
    (4, "#00FF00", "Green", 4),
    (5, "#0000FF", "Blue", 5),
    (6, "#FFFF00", "Yellow", 6),
    (7, "#FF00FF", "Magenta", 7),
    (8, "#00FFFF", "Cyan", 8),
    (9, "#808080", "Gray", 9),
    (10, "#C0C0C0", "Silver", 10),
    (11, "#800000", "Maroon", 11),
    (12, "#008000", "Dark Green", 12),
    (13, "#000080", "Navy", 13),
    (14, "#808000", "Olive", 14),
    (15, "#800080", "Purple", 15),
    (16, "#008080", "Teal", 16),
]


class Command(BaseCommand):
    help = "Seed system color palette definitions."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for code, hex_value, name, order in DEFAULT_COLORS:
            _obj, was_created = ColorDefinition.objects.update_or_create(
                code=code,
                defaults={
                    "hex_value": hex_value,
                    "name": name,
                    "default_order": order,
                    "is_system": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded system colors: {created} created, {updated} updated."
            )
        )
