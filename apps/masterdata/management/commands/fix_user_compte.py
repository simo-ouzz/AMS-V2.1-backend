"""Assign the first Compte to any user that has compte=NULL."""
from django.core.management.base import BaseCommand
from masterdata.models.user import UserWeb, Compte


class Command(BaseCommand):
    help = 'Assign a compte to users who have no compte set (e.g. superusers created via createsuperuser).'

    def handle(self, *args, **options):
        users_without_compte = UserWeb.objects.filter(compte__isnull=True)
        count = users_without_compte.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('All users already have a compte assigned.'))
            return

        first_compte = Compte.objects.first()
        if not first_compte:
            self.stdout.write(self.style.ERROR('No Compte exists in the database. Create one first.'))
            return

        users_without_compte.update(compte=first_compte)
        self.stdout.write(self.style.SUCCESS(
            f'Assigned compte "{first_compte.libelle}" (id={first_compte.id}) to {count} user(s).'
        ))
