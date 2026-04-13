"""
Ensure a bootstrap superuser exists (idempotent). Used by Docker entrypoint.

Environment:
  BOOTSTRAP_SUPERUSER_USERNAME (default: admin)
  BOOTSTRAP_SUPERUSER_PASSWORD (default: Gauss_246)
  BOOTSTRAP_SUPERUSER_EMAIL (default: admin@localhost)
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create or update bootstrap superuser (Docker default admin)."

    def handle(self, *args, **options):
        username = (os.environ.get("BOOTSTRAP_SUPERUSER_USERNAME") or "admin").strip()
        password = os.environ.get("BOOTSTRAP_SUPERUSER_PASSWORD", "Gauss_246")
        email = (os.environ.get("BOOTSTRAP_SUPERUSER_EMAIL") or "admin@localhost").strip()

        if not username:
            self.stderr.write("BOOTSTRAP_SUPERUSER_USERNAME is empty, skip.")
            return

        user = User.objects.filter(username=username).first()
        if user:
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.email = email or user.email
            if hasattr(user, "role"):
                user.role = "admin"
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    "Updated bootstrap superuser: %s (password reset)" % username
                )
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role="admin",
        )
        self.stdout.write(
            self.style.SUCCESS("Created bootstrap superuser: %s" % username)
        )
