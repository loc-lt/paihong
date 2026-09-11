from core.services.file_storage import store_uploaded_file


def assign_user_avatar(user, avatar_file, *, created_by):
    if not avatar_file:
        return user
    user.avatar = store_uploaded_file(avatar_file, created_by=created_by)
    user.save(update_fields=["avatar", "modified"])
    return user
