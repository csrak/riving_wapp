# management_commands/management/commands/manage_schedules.py

from django.core.management.base import BaseCommand
from django_q.models import Schedule
from django.utils import timezone
import json


class Command(BaseCommand):
    """
    Management command to administer Django-Q scheduled tasks.

    This command provides utilities to list, clear, and reset scheduled tasks
    that are managed by Django-Q. It's particularly useful for maintaining
    price update schedules and other recurring database tasks.

    Usage:
        python manage.py manage_schedules --list
        python manage.py manage_schedules --clear
        python manage.py manage_schedules --reset
    """

    help = 'Manage Django-Q scheduled tasks for database updates'

    def add_arguments(self, parser):
        """
        Define command line arguments for the management command.

        Arguments:
            --list: Display all currently scheduled tasks
            --clear: Remove all scheduled tasks
            --reset: Recreate the SCL price update schedule
        """
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all scheduled tasks with their details'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all scheduled tasks from the database'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset the SCL exchange price update schedule'
        )

    def handle(self, *args, **options):
        """
        Main command handler that processes the specified action.

        This method determines which operation to perform based on the
        provided command line arguments.
        """
        if options['list']:
            self._list_schedules()
        elif options['clear']:
            self._clear_schedules()
        elif options['reset']:
            self._reset_scl_schedule()
        else:
            self.stdout.write(self.style.WARNING(
                'No action specified. Use --list, --clear, or --reset'
            ))
            self.stdout.write(self.style.NOTICE(
                'Example: python manage.py manage_schedules --list'
            ))

    def _list_schedules(self):
        """
        Display all scheduled tasks in the system with detailed information.

        This method outputs:
        - Task ID and name
        - Next scheduled run time
        - Function to be called
        - Arguments and keyword arguments
        - Schedule type and repetition settings
        """
        schedules = Schedule.objects.all()

        if not schedules.exists():
            self.stdout.write(self.style.NOTICE("No scheduled tasks found."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {schedules.count()} scheduled tasks:"))

        for schedule in schedules:
            # Format the next run time or show 'None' if not set
            next_run = schedule.next_run.strftime('%Y-%m-%d %H:%M:%S') if schedule.next_run else 'None'

            # Format kwargs as readable JSON if present
            kwargs_display = json.dumps(json.loads(schedule.kwargs)) if schedule.kwargs else 'None'

            # Display schedule information with clear formatting
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"Schedule: {schedule.name} (ID: {schedule.id})"
            ))
            self.stdout.write(f"  • Function: {schedule.func}")
            self.stdout.write(f"  • Args: {schedule.args}")
            self.stdout.write(f"  • Kwargs: {kwargs_display}")
            self.stdout.write(f"  • Schedule type: {schedule.schedule_type}")
            self.stdout.write(f"  • Next run: {next_run}")
            self.stdout.write(f"  • Repeats remaining: {schedule.repeats if schedule.repeats != -1 else 'Indefinite'}")
            self.stdout.write(f"  • Last run: {schedule.last_run or 'Never'}")
            self.stdout.write("")

    def _clear_schedules(self):
        """
        Remove all scheduled tasks from the database.

        This is useful when you need to reset all schedules or when
        troubleshooting scheduling issues.

        CAUTION: This will remove ALL scheduled tasks, including any
        that may have been set up for other parts of the application.
        """
        count, _ = Schedule.objects.all().delete()

        if count:
            self.stdout.write(self.style.SUCCESS(
                f"Successfully cleared {count} scheduled task(s)"
            ))
        else:
            self.stdout.write(self.style.NOTICE(
                "No scheduled tasks found to clear"
            ))

    def _reset_scl_schedule(self):
        """
        Reset the price update schedule for the SCL (Santiago) exchange.

        This method:
        1. Removes any existing SCL price update schedules
        2. Creates a fresh schedule to run daily
        3. Sets the next execution to occur immediately

        This is particularly useful when:
        - The schedule configuration needs to be updated
        - The schedule has stopped working correctly
        - You want to force an immediate price update
        """
        # First, identify and remove existing SCL price update schedules
        deleted_count, _ = Schedule.objects.filter(
            func='django.core.management.call_command',
            kwargs__contains='"exchange": "SCL"'
        ).delete()

        if deleted_count:
            self.stdout.write(f"Removed {deleted_count} existing SCL price update schedule(s)")

        # Create a new schedule with fresh settings
        new_schedule = Schedule.objects.create(
            name='Daily SCL Price Update',
            func='django.core.management.call_command',
            args='price_update',
            kwargs=json.dumps({"exchange": "SCL"}),
            schedule_type=Schedule.DAILY,
            repeats=-1,  # Repeat indefinitely
            next_run=timezone.now()  # Start immediately
        )

        self.stdout.write(self.style.SUCCESS(
            f"Successfully created new SCL price update schedule (ID: {new_schedule.id})"
        ))
        self.stdout.write(f"Next run scheduled for: {new_schedule.next_run.strftime('%Y-%m-%d %H:%M:%S')}")