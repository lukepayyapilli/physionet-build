from django.db import models
from django.utils import timezone


class UploadAgreement(models.Model):
    """
    Model to track upload agreements for projects.
    Each project can have one active upload agreement.
    """
    project = models.ForeignKey(
        'project.ActiveProject',
        on_delete=models.CASCADE,
        related_name='upload_agreements'
    )

    # User who accepted the agreement
    accepted_by = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='The user who accepted this upload agreement'
    )

    # Agreement acceptance
    accepted = models.BooleanField(
        default=False,
        help_text='Whether the upload agreement has been accepted'
    )

    accepted_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the upload agreement was accepted'
    )

    # Data type options (at least one must be selected)
    no_human_subjects = models.BooleanField(
        default=False,
        help_text='This project does not contain any data derived from human subjects'
    )

    derived_data = models.BooleanField(
        default=False,
        help_text='This project contains data derived from other de-identified datasets'
    )

    human_subjects_deidentified = models.BooleanField(
        default=False,
        help_text=(
            'This project contains data obtained from human subjects, and all '
            'personally identifiable information has been removed'
        )
    )

    # Metadata
    created_datetime = models.DateTimeField(auto_now_add=True)
    updated_datetime = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_uploadagreement'
        verbose_name = 'Upload Agreement'
        verbose_name_plural = 'Upload Agreements'
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(no_human_subjects=True)
                    | models.Q(derived_data=True)
                    | models.Q(human_subjects_deidentified=True)
                ),
                name='at_least_one_data_type_selected'
            )
        ]

    def __str__(self):
        return (
            f"Upload Agreement for {self.project.title} - "
            f"{'Accepted' if self.accepted else 'Pending'}"
        )

    def save(self, *args, **kwargs):
        # If this is being marked as accepted, set the timestamp
        if self.accepted and not self.accepted_datetime:
            self.accepted_datetime = timezone.now()
        super().save(*args, **kwargs)

    @classmethod
    def get_active_agreement(cls, project):
        """
        Get the active (accepted) upload agreement for a project, if it exists.
        The agreement is only considered active if it was signed by the current submitting author.
        """
        try:
            submitting_author = project.authors.get(is_submitting=True)
        except project.authors.model.DoesNotExist:
            return None
        except project.authors.model.MultipleObjectsReturned:
            raise project.authors.model.MultipleObjectsReturned(
                f"Multiple submitting authors found for project {project.id}. "
                "This indicates a data integrity issue."
            )

        try:
            return cls.objects.get(
                project=project,
                accepted=True,
                accepted_by=submitting_author.user
            )
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            raise cls.MultipleObjectsReturned(
                f"Multiple active upload agreements found for project {project.id} "
                f"and user {submitting_author.user.id}. This indicates a data integrity issue."
            )
