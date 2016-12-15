from django.db.migrations.operations.base import Operation

from .schema import DatabaseTriggerEditor


class _TriggerEditorOperation(Operation):

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        super().database_forwards(app_label, DatabaseTriggerEditor(schema_editor), from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        super().database_backwards(app_label, DatabaseTriggerEditor(schema_editor), from_state, to_state)


def inject_trigger_operations(plan=None, **kwargs):

    if plan is None:
        return

    for migration, backward in plan:

        inserts = []
        for index, operation in enumerate(migration.operations):
            clsname, args, kwargs = operation.deconstruct()
            if clsname in ('CreateModel', 'DeleteModel', 'AddField', 'RemoveField', 'AlterField'):
                newop = type('TriggerEditorOperation', (_TriggerEditorOperation, operation.__class__), {})
                if clsname in ('DeleteModel', 'RemoveField'):
                    # inject operation ahead of the original as we
                    # need to introspect the not-yet-deleted field
                    inserts.append((index, newop(*args, **kwargs)))
                else:
                    # inject operation after the original as we
                    # need table and column to be created first
                    inserts.append((index + 1, newop(*args, **kwargs)))

        for inserted, (index, operation) in enumerate(inserts):
            migration.operations.insert(inserted + index, operation)


