import os
from dotenv import load_dotenv
import meraki

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


# Defining your API key as a variable in source code is discouraged.
# This API key is for a read-only docs-specific environment.
# In your own code, use an environment variable as shown under the Usage section
# @ https://github.com/meraki/dashboard-api-python/


def device_details():
    """
    Fetches all devices from the Meraki organization.

    Returns:
        list: A list of all devices in the organization with their details.
    """
    # Initialize the Meraki Dashboard API client with the API key
    dashboard = meraki.DashboardAPI(API_KEY)

    # Fetch all devices from the organization (all=True returns complete dataset)
    response = dashboard.organizations.getOrganizationDevices(
        organization_id, True
    )
    return response
