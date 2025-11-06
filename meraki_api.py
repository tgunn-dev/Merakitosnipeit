import os
import logging
from dotenv import load_dotenv
import meraki

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Access and validate environment variables
API_KEY = os.getenv("MERAKI_API_KEY")
organization_id = os.getenv("ORGANIZATION_ID")

# Validate required environment variables exist
if not API_KEY:
    raise ValueError("MERAKI_API_KEY environment variable is not set")
if not organization_id:
    raise ValueError("ORGANIZATION_ID environment variable is not set")


def device_details():
    """
    Fetches all devices from the Meraki organization.

    Returns:
        list: A list of all devices in the organization with their details.

    Raises:
        Exception: If the API call fails.
    """
    try:
        logger.info("Fetching devices from Meraki Dashboard API...")
        # Initialize the Meraki Dashboard API client with the API key
        dashboard = meraki.DashboardAPI(API_KEY, suppress_logging=True)

        # Fetch all devices from the organization (all=True returns complete dataset)
        response = dashboard.organizations.getOrganizationDevices(
            organization_id, True
        )
        logger.info(f"Successfully fetched {len(response) if response else 0} devices from Meraki")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch devices from Meraki: {str(e)}")
        raise
