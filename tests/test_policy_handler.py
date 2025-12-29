# tests/test_policy_handler.py

import unittest
from unittest.mock import Mock, MagicMock

from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v22.common.types import PolicyValidationParameter
from google.ads.googleads.v22.common.types import PolicyTopicEntry
from google.ads.googleads.v22.errors.types import (
    ErrorCode,
    GoogleAdsError,
    GoogleAdsFailure,
    PolicyFindingDetails,
)

from src.handlers.policy_handler import (
    PolicyViolationError,
    create_exemption_parameter,
    extract_policy_topics,
    handle_policy_violation,
)


def create_mock_google_ads_exception(
    policy_topics: list[str] | None,
) -> GoogleAdsException:
    """Helper function to create a mock GoogleAdsException."""
    mock_failure = Mock(spec=GoogleAdsFailure)
    mock_error = Mock(spec=GoogleAdsError)
    mock_error_code = Mock(spec=ErrorCode)
    mock_details = Mock()

    if policy_topics:
        mock_error_code.policy_finding_error = True
        mock_policy_finding_details = Mock(spec=PolicyFindingDetails)
        mock_policy_topic_entries = [
            Mock(spec=PolicyTopicEntry, topic=topic) for topic in policy_topics
        ]
        mock_policy_finding_details.policy_topic_entries = mock_policy_topic_entries
        mock_details.policy_finding_details = mock_policy_finding_details
    else:
        mock_error_code.policy_finding_error = False
        mock_details.policy_finding_details = None

    mock_error.error_code = mock_error_code
    mock_error.details = mock_details
    mock_failure.errors = [mock_error]

    return GoogleAdsException(
        failure=mock_failure,
        call=Mock(),
        error=Mock(),
        request_id="test_request_id",
    )


class TestPolicyHandler(unittest.TestCase):
    def test_extract_policy_topics(self):
        """Test that policy topics are extracted correctly."""
        exception = create_mock_google_ads_exception(["topic1", "topic2"])
        topics = extract_policy_topics(exception)
        self.assertEqual(topics, ["topic1", "topic2"])

    def test_extract_policy_topics_no_policy_error(self):
        """Test that no topics are extracted if it's not a policy error."""
        exception = create_mock_google_ads_exception(None)
        topics = extract_policy_topics(exception)
        self.assertEqual(topics, [])

    def test_create_exemption_parameter(self):
        """Test that the exemption parameter is created correctly."""
        topics = ["topic1", "topic2"]
        parameter = create_exemption_parameter(topics)
        self.assertIsInstance(parameter, PolicyValidationParameter)
        self.assertEqual(parameter.ignorable_policy_topics, topics)

    def test_handle_policy_violation_success(self):
        """Test that the decorator returns the result on success."""
        mock_api_call = Mock(return_value="Success")

        @handle_policy_violation
        def decorated_call(**kwargs):
            return mock_api_call(**kwargs)

        result = decorated_call()
        self.assertEqual(result, "Success")
        mock_api_call.assert_called_once_with()

    def test_handle_policy_violation_retry_success(self):
        """Test the retry mechanism on policy violation."""
        policy_exception = create_mock_google_ads_exception(["topic1"])
        mock_api_call = MagicMock()
        mock_api_call.side_effect = [policy_exception, "Success on Retry"]

        @handle_policy_violation
        def decorated_call(**kwargs):
            return mock_api_call(**kwargs)

        result = decorated_call()
        self.assertEqual(result, "Success on Retry")
        self.assertEqual(mock_api_call.call_count, 2)

        # Check that the second call has the exemption parameter
        _, last_kwargs = mock_api_call.call_args
        self.assertIn("policy_validation_parameter", last_kwargs)
        exemption = last_kwargs["policy_validation_parameter"]
        self.assertEqual(exemption.ignorable_policy_topics, ["topic1"])

    def test_handle_policy_violation_retry_fails(self):
        """Test that PolicyViolationError is raised when retry fails."""
        policy_exception = create_mock_google_ads_exception(["topic1"])
        mock_api_call = Mock(side_effect=[policy_exception, policy_exception])

        @handle_policy_violation
        def decorated_call(**kwargs):
            return mock_api_call(**kwargs)

        with self.assertRaises(PolicyViolationError):
            decorated_call()
        self.assertEqual(mock_api_call.call_count, 2)

    def test_handle_policy_violation_other_exception(self):
        """Test that non-policy exceptions are re-raised."""
        other_exception = create_mock_google_ads_exception(None)
        mock_api_call = Mock(side_effect=other_exception)

        @handle_policy_violation
        def decorated_call(**kwargs):
            return mock_api_call(**kwargs)

        with self.assertRaises(GoogleAdsException) as context:
            decorated_call()

        self.assertIsNotNone(context.exception)
        self.assertEqual(mock_api_call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
