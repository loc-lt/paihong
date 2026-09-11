from django.contrib.auth.models import BaseUserManager
from django_softdelete.managers import DeletedManager, GlobalManager, SoftDeleteManager

from core.constant import UserRoleEnum, UserStatusEnum
from core.querysets import UserQuerySet


class SoftDeleteUserManager(SoftDeleteManager, BaseUserManager):
    use_in_migrations = True

    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)

    def create_user(self, username, password=None, **extra_fields):
        if not str(username or "").strip():
            raise ValueError("Username is required.")

        extra_fields.setdefault("role", UserRoleEnum.CUSTOMER.value)
        extra_fields.setdefault("status", UserStatusEnum.ACTIVE.value)

        user = self.model(username=username.strip(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRoleEnum.ADMIN.value)
        extra_fields.setdefault("status", UserStatusEnum.ACTIVE.value)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, password=password, **extra_fields)


class GlobalUserManager(GlobalManager):
    pass


class DeletedUserManager(DeletedManager):
    pass
