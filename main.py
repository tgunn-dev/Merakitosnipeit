import logging
import time
from datetime import datetime
from meraki_api import device_details
import snipe_it

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SyncStatistics:
    """Tracks sync statistics for reporting."""
    def __init__(self):
        self.total_devices = 0
        self.successful = 0
        self.failed = 0
        self.updated = 0
        self.created = 0
        self.start_time = None
        self.end_time = None
        self.api_calls = {
            "meraki": 1,  # One call to fetch all devices
            "snipe_it_searches": 0,
            "snipe_it_creates": 0,
            "snipe_it_updates": 0
        }

    def get_duration(self):
        """Returns sync duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def print_summary(self):
        """Prints a formatted summary of sync statistics."""
        logger.info("="*60)
        logger.info("SYNC SUMMARY")
        logger.info("="*60)
        logger.info(f"Total devices processed: {self.total_devices}")
        logger.info(f"  ✓ Successful: {self.successful}")
        logger.info(f"  ✗ Failed: {self.failed}")
        logger.info(f"  → Created: {self.created}")
        logger.info(f"  ↻ Updated: {self.updated}")
        logger.info(f"Duration: {self.get_duration():.2f} seconds")
        logger.info(f"Estimated API calls:")
        logger.info(f"  - Meraki: {self.api_calls['meraki']}")
        logger.info(f"  - Snipe-IT Searches: {self.api_calls['snipe_it_searches']}")
        logger.info(f"  - Snipe-IT Creates: {self.api_calls['snipe_it_creates']}")
        logger.info(f"  - Snipe-IT Updates: {self.api_calls['snipe_it_updates']}")
        logger.info(f"  Total Snipe-IT calls: {sum(self.api_calls[k] for k in self.api_calls if k.startswith('snipe_it'))}")
        logger.info("="*60)


def map_meraki_to_snipeit(device):
    """
    Maps a Meraki device's data to Snipe-IT fields.

    Args:
        device (dict): A dictionary containing Meraki device details from the Meraki API.

    Returns:
        dict: A dictionary formatted and ready for Snipe-IT API.

    Raises:
        ValueError: If required device fields are missing.
    """
    # Extract device information from Meraki API response
    model_name = device.get("model")
    product_type = device.get('productType')

    if not model_name or not product_type:
        raise ValueError(f"Device missing required fields: model={model_name}, productType={product_type}")

    # Get or create the asset category based on product type
    category = snipe_it.get_or_create_entity(
        "categories",
        product_type,
        {"category_type": "asset"}
    )

    # Get or create the device model with the category reference
    model_id = snipe_it.get_or_create_entity(
        "models",
        model_name,
        {"category_id": category}
    )

    if not model_id:
        raise Exception(f"Model ID could not be retrieved or created for model: {model_name}")

    # Transform Meraki device data into Snipe-IT hardware format
    return {
        "name": device.get("name"),
        "serial": device.get("serial"),
        "asset_tag": device.get("serial"),  # Use serial as the asset tag for deduplication
        "model_id": model_id,
        "category": category,
        "status_id": 2,  # Status ID 2 typically represents "Ready to Deploy"
        "purchase_date": device.get("purchase_date", None),
        "purchase_cost": device.get("purchase_cost", None),
        # Include original Meraki data in notes for reference
        "notes": f"Imported from Meraki. MAC: {device.get('mac')}, Network ID: {device.get('networkId')}"
    }


if __name__ == '__main__':
    """
    Main sync workflow: fetches devices from Meraki and syncs them to Snipe-IT.
    This script is designed to be run periodically (via cron, systemd timer, or APScheduler).
    """
    stats = SyncStatistics()
    stats.start_time = datetime.now()

    try:
        logger.info("Starting Meraki to Snipe-IT sync...")
        logger.info("Initializing caches...")

        # Initialize cache to minimize API calls
        snipe_it._initialize_cache()

        # Fetch all devices from the Meraki organization
        logger.info("Fetching devices from Meraki Dashboard API...")
        devices = device_details()

        if not devices:
            logger.warning("No devices found in Meraki organization.")
            stats.end_time = datetime.now()
            stats.print_summary()
        else:
            stats.total_devices = len(devices)
            logger.info(f"Found {len(devices)} devices in Meraki. Starting sync to Snipe-IT...")

            # Process each device with a small delay to avoid overwhelming the API
            for index, device in enumerate(devices, 1):
                try:
                    # Add delay between requests to respect API rate limits
                    time.sleep(0.5)

                    device_name = device.get('name', 'Unknown')
                    logger.info(f"[{index}/{len(devices)}] Processing device: {device_name}")

                    # Transform Meraki device data to Snipe-IT format
                    snipeit_data = map_meraki_to_snipeit(device)

                    # Post/update the device in Snipe-IT
                    response = snipe_it.post_hardware_to_snipe_it(snipeit_data)

                    if response["success"]:
                        stats.successful += 1
                        action = response.get("action", "unknown")

                        # Track API calls: 1 search + 1 update/create
                        stats.api_calls["snipe_it_searches"] += 1
                        if action == "update":
                            stats.updated += 1
                            stats.api_calls["snipe_it_updates"] += 1
                        elif action == "create":
                            stats.created += 1
                            stats.api_calls["snipe_it_creates"] += 1

                        logger.debug(f"✓ Successfully synced device: {device_name}")
                    else:
                        stats.failed += 1
                        error_msg = response.get('error', 'Unknown error')
                        logger.error(f"✗ Failed to sync device: {device_name}. Error: {error_msg}")

                except Exception as device_error:
                    stats.failed += 1
                    logger.error(f"✗ Error processing device {device.get('name', 'Unknown')}: {str(device_error)}", exc_info=True)
                    # Continue with next device instead of stopping completely
                    continue

            stats.end_time = datetime.now()
            stats.print_summary()

    except Exception as e:
        logger.fatal(f"Fatal error during sync: {str(e)}", exc_info=True)
        stats.end_time = datetime.now()
        stats.print_summary()
        exit(1)