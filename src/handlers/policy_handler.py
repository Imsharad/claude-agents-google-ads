# src/handlers/policy_handler.py

from functools import wraps
from typing import List, Callable, Any

from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v22.common.types import PolicyValidationParameter


class PolicyViolationError(Exception):
    """Custom exception for policy violation errors that persist after a retry."""

    pass


def extract_policy_topics(exception: GoogleAdsException) -> List[str]:
    """
    Extracts policy topic resource names from a GoogleAdsException.

    Args:
        exception: The GoogleAdsException instance.

    Returns:
        A list of policy topic strings.
    """
    policy_topics = []
    for error in exception.failure.errors:
        if error.error_code.policy_finding_error:
            if error.details.policy_finding_details:
                for entry in error.details.policy_finding_details.policy_topic_entries:
                    policy_topics.append(entry.topic)
    return policy_topics


def create_exemption_parameter(topics: List[str]) -> PolicyValidationParameter:
    """
    Creates a PolicyValidationParameter with ignorable policy topics.

    Args:
        topics: A list of policy topic strings to ignore.

    Returns:
        A PolicyValidationParameter instance.
    """
    return PolicyValidationParameter(ignorable_policy_topics=topics)


def handle_policy_violation(func: Callable) -> Callable:
    """
    A decorator that implements the Try-Catch-Exempt-Retry flow for Google Ads API calls.

    The decorated function is expected to accept a 'policy_validation_parameter' kwarg.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """
        Wrapper function that catches GoogleAdsException and retries with exemption.
        """
        try:
            return func(*args, **kwargs)
        except GoogleAdsException as ex:
            policy_topics = extract_policy_topics(ex)
            if policy_topics:
                # If policy topics are found, create an exemption and retry the operation.
                exemption = create_exemption_parameter(policy_topics)
                kwargs["policy_validation_parameter"] = exemption
                try:
                    return func(*args, **kwargs)
                except GoogleAdsException as retry_ex:
                    # If the retry also fails, raise a custom exception.
                    raise PolicyViolationError(
                        "Retry with exemption failed."
                    ) from retry_ex
            else:
                # If it's not a policy violation, re-raise the original exception.
                raise

    return wrapper
