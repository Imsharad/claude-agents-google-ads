import logging
from google.ads.googleads.client import GoogleAdsClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_google_ads_client(config_file: str = "google-ads.yaml"):
    """
    Initializes and returns a GoogleAdsClient instance.

    Args:
        config_file (str): The path to the Google Ads configuration file.

    Returns:
        GoogleAdsClient: An initialized Google Ads client, or None if initialization fails.
    """
    try:
        logging.info(
            f"Attempting to load Google Ads configuration from '{config_file}'"
        )
        # The load_from_storage method looks for the file in the current working directory
        # or in the user's home directory.
        google_ads_client = GoogleAdsClient.load_from_storage(config_file)
        logging.info("Successfully initialized Google Ads client.")
        return google_ads_client
    except FileNotFoundError:
        logging.error(
            f"Configuration file '{config_file}' not found. "
            "Please ensure the file exists and contains the necessary credentials."
        )
        return None
    except Exception as e:
        logging.error(
            f"An unexpected error occurred while initializing the Google Ads client: {e}"
        )
        return None
