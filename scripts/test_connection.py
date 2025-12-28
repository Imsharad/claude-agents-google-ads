import sys
import os
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from config.google_ads_client import get_google_ads_client
from google.ads.googleads.errors import GoogleAdsException

def main():
    """
    Tests the connection to the Google Ads API.
    """
    logging.info("--- Starting Google Ads API Connection Test ---")

    # Attempt to get the Google Ads client
    # This assumes a google-ads.yaml file is in the root directory
    google_ads_client = get_google_ads_client()

    if not google_ads_client:
        logging.error("Failed to initialize Google Ads client. Please check your configuration.")
        print("\nConnection Test: FAILED")
        return

    try:
        # Get the CustomerService client
        customer_service = google_ads_client.get_service("CustomerService")

        # Retrieve the list of accessible customer accounts
        accessible_customers = customer_service.list_accessible_customers()

        logging.info("Successfully connected to the Google Ads API.")
        print("\nConnection Test: SUCCESS")
        print("Accessible customer accounts:")
        for resource_name in accessible_customers.resource_names:
            print(f"- {resource_name}")

    except GoogleAdsException as ex:
        logging.error(f"Request with ID '{ex.request_id}' failed with status "
                      f"'{ex.error.code().name}' and includes the following errors:")
        for error in ex.failure.errors:
            logging.error(f"\tError with message '{error.message}'.")
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    logging.error(f"\t\tOn field: {field_path_element.field_name}")
        print("\nConnection Test: FAILED")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        print("\nConnection Test: FAILED")

if __name__ == "__main__":
    main()
