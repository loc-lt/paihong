from django.core.management.base import BaseCommand

from core.constant import WORKFLOW_STEP_SEED
from core.models import TemplateStep, WorkflowStepDefinition, WorkflowTemplate


class Command(BaseCommand):
    help = "Seed workflow step definitions and default workflow template."

    def handle(self, *args, **options):
        created_steps = 0
        updated_steps = 0
        step_map = {}

        schema_keys = {
            "PICK_UPPER": "PICK_UPPER",
            "FIX_LINES_BY_ANCHOR": "FIX_LINES_BY_ANCHOR",
            "CHECK_COLORS": "CHECK_COLORS",
            "CANVAS_FRAME_MEASURE": "CANVAS_FRAME_MEASURE",
            "ENTER_SPECS": "ENTER_SPECS",
            "BUILD_GRID": "BUILD_GRID",
            "START_DESIGNING": "START_DESIGNING",
        }

        for sequence, code, name in WORKFLOW_STEP_SEED:
            step, created = WorkflowStepDefinition.objects.update_or_create(
                code=code,
                defaults={
                    "sequence": sequence,
                    "name": name,
                    "description": "",
                    "version": 1,
                    "is_active": True,
                    "settings_schema_key": schema_keys.get(code, ""),
                },
            )
            step_map[code] = step
            if created:
                created_steps += 1
            else:
                updated_steps += 1

        template, template_created = WorkflowTemplate.objects.update_or_create(
            code="STANDARD_SHOE",
            defaults={
                "name": "Standard shoe design workflow",
                "description": "Default workflow template seeded from system.",
                "is_active": True,
                "is_default": True,
            },
        )
        WorkflowTemplate.objects.exclude(id=template.id).update(is_default=False)

        if not template_created:
            template.template_steps.all().delete()

        for sequence, code, _name in WORKFLOW_STEP_SEED:
            TemplateStep.objects.create(
                template=template,
                step=step_map[code],
                sequence=sequence,
                is_required=True,
                settings_schema_version=1,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded steps: {created_steps} created, {updated_steps} updated. "
                f"Template '{template.code}' ready."
            )
        )
