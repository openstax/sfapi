import time


# Minimum time (in seconds) between form load and submission — submissions faster than this are likely bots
MIN_SUBMISSION_TIME = 3

DISPOSABLE_EMAIL_DOMAINS = frozenset([
    'mailinator.com', 'guerrillamail.com', 'tempmail.com', 'throwaway.email',
    'yopmail.com', 'sharklasers.com', 'grr.la', 'guerrillamailblock.com',
    'trashmail.com', 'dispostable.com',
])


class FormPipeline:
    """Validates form submissions and detects spam."""

    def validate(self, payload, request_time=None):
        """
        Run validation checks on a form submission.
        Returns (is_valid, errors) where errors is a list of strings.
        Spam submissions return is_valid=False with error='spam'.
        """
        errors = []

        # Check honeypot field — should be empty
        if payload.honeypot:
            return False, ['spam']

        # Check submission timing
        if payload.submitted_at is not None:
            elapsed = (request_time or time.time()) - (payload.submitted_at / 1000)
            if elapsed < MIN_SUBMISSION_TIME:
                return False, ['spam']

        # Check for disposable email in form data
        email = payload.data.get('email', '')
        if email and '@' in email:
            domain = email.split('@')[-1].lower()
            if domain in DISPOSABLE_EMAIL_DOMAINS:
                return False, ['spam']

        # Basic data validation
        if not payload.form_type:
            errors.append('form_type is required')

        if not payload.data:
            errors.append('data is required')

        if errors:
            return False, errors

        return True, []
