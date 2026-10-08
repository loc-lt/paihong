from django.core.management.base import BaseCommand

from core.models import ColorDefinition

# First 8 colors are the SVG palette (also available as pixels).
# The next 8 are pixel-only.
DEFAULT_COLORS = [
    (1, "#000000", "Black", 1, True, True),
    (2, "#FFFFFF", "White", 2, True, True),
    (3, "#FF0000", "Red", 3, True, True),
    (4, "#00FF00", "Green", 4, True, True),
    (5, "#0000FF", "Blue", 5, True, True),
    (6, "#FFFF00", "Yellow", 6, True, True),
    (7, "#FF00FF", "Magenta", 7, True, True),
    (8, "#00FFFF", "Cyan", 8, True, True),
    (9, "#808080", "Gray", 9, False, True),
    (10, "#C0C0C0", "Silver", 10, False, True),
    (11, "#800000", "Maroon", 11, False, True),
    (12, "#008000", "Dark Green", 12, False, True),
    (13, "#000080", "Navy", 13, False, True),
    (14, "#808000", "Olive", 14, False, True),
    (15, "#800080", "Purple", 15, False, True),
    (16, "#008080", "Teal", 16, False, True),
]


class Command(BaseCommand):
    help = "Seed system color palette definitions."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for code, hex_value, name, order, is_svg, is_pixel in DEFAULT_COLORS:
            _obj, was_created = ColorDefinition.objects.update_or_create(
                code=code,
                defaults={
                    "hex_value": hex_value,
                    "name": name,
                    "display_order": order,
                    "is_system": True,
                    "is_svg": is_svg,
                    "is_pixel": is_pixel,
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
