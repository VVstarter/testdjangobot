from django.core.management.base import BaseCommand

from testbot.bot import TestBot


class Command(BaseCommand):
    help = 'Telegram bot'

    def handle(self, *args, **options):
        tb = TestBot()
        tb.run()
