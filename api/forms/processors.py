import logging

from django.utils import timezone

from sf.models.case import Case

logger = logging.getLogger('openstax')

# Registry of form processors keyed by form_type
PROCESSORS = {}


def register_processor(form_type):
    """Decorator to register a form processor function."""
    def decorator(func):
        PROCESSORS[form_type] = func
        return func
    return decorator


def process_submission(submission):
    """
    Process a FormSubmission by dispatching to the appropriate processor.
    Updates the submission status and sf_record_id.
    """
    processor = PROCESSORS.get(submission.form_type)
    if processor is None:
        submission.status = 'failed'
        submission.error_message = f'Unknown form type: {submission.form_type}'
        submission.processed_at = timezone.now()
        submission.save(update_fields=['status', 'error_message', 'processed_at'])
        return

    submission.status = 'processing'
    submission.save(update_fields=['status'])

    try:
        sf_record_id = processor(submission.data)
        submission.status = 'completed'
        submission.sf_record_id = sf_record_id or ''
        submission.processed_at = timezone.now()
        submission.save(update_fields=['status', 'sf_record_id', 'processed_at'])
    except Exception as e:
        logger.exception(f"Form processing failed for {submission.id}: {e}")
        submission.status = 'failed'
        submission.error_message = str(e)[:1000]
        submission.processed_at = timezone.now()
        submission.save(update_fields=['status', 'error_message', 'processed_at'])


@register_processor('web_to_case')
def process_web_to_case(data):
    """Create a Salesforce Case from form data."""
    case = Case.objects.create(
        subject=data.get('subject', ''),
        description=data.get('description', ''),
        product=data.get('product'),
        feature=data.get('feature'),
        issue=data.get('issue'),
    )
    return case.pk


@register_processor('contact_us')
def process_contact_us(data):
    """Create a Salesforce Case from a contact us form."""
    case = Case.objects.create(
        subject=f"Contact Us: {data.get('subject', 'General Inquiry')}",
        description=data.get('message', ''),
    )
    return case.pk
