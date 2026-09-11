from django.conf import settings


class PathFormatterMixin:
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if "path" in representation and representation["path"]:
            domain = getattr(settings, "BE_DOMAIN", "")
            if domain:
                representation["path"] = f"{domain}{representation['path']}"
        return representation
