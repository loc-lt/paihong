from django.core.management.base import BaseCommand

from core.constant import UserRoleEnum
from core.models import User


class Command(BaseCommand):
    help = "Seed the database with default users."

    def handle(self, *args, **kwargs):
        defaults = [
            ("admin", UserRoleEnum.ADMIN.value),
            ("designer", UserRoleEnum.DESIGNER.value),
            ("developer", UserRoleEnum.DEVELOPER.value),
        ]
        for username, role in defaults:
            if User.objects.filter(username=username).exists():
                continue
            User.objects.create_user(
                username=username,
                password="Defaultpassword@123",
                first_name=username.title(),
                last_name="User",
                role=role,
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded users."))
