from meraki_api import device_details
import snipe_it
import time

def map_meraki_to_snipeit(device):
    """
    Maps a Meraki device's data to Snipe-IT fields.

    Args:
        device (dict): A dictionary containing Meraki device details from the Meraki API.

    Returns:
        dict: A dictionary formatted and ready for Snipe-IT API.
    """
    # Extract device information from Meraki API response
    model_name = device.get("model")
    product_type = device.get('productType')

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
    This script is designed to be run periodically (hourly via cron in Docker).
    """
    try:
        # Fetch all devices from the Meraki organization
        print("Fetching devices from Meraki Dashboard API...")
        devices = device_details()

        if not devices:
            print("No devices found in Meraki organization.")
        else:
            print(f"Found {len(devices)} devices in Meraki. Starting sync to Snipe-IT...")

            # Process each device with a small delay to avoid overwhelming the API
            for index, device in enumerate(devices, 1):
                try:
                    # Add delay between requests to respect API rate limits
                    time.sleep(0.5)

                    device_name = device.get('name', 'Unknown')
                    print(f"\n[{index}/{len(devices)}] Processing device: {device_name}")

                    # Transform Meraki device data to Snipe-IT format
                    snipeit_data = map_meraki_to_snipeit(device)
                    print(f"Device info retrieved from Meraki")

                    # Post/update the device in Snipe-IT
                    response = snipe_it.post_hardware_to_snipe_it(snipeit_data)

                    if response["success"]:
                        print(f"✓ Successfully synced device: {device_name}")
                    else:
                        error_msg = response.get('error', 'Unknown error')
                        print(f"✗ Failed to sync device: {device_name}. Error: {error_msg}")

                except Exception as device_error:
                    print(f"✗ Error processing device {device.get('name', 'Unknown')}: {str(device_error)}")
                    # Continue with next device instead of stopping completely
                    continue

            print("\n" + "="*50)
            print("Device sync completed.")
            print("="*50)

    except Exception as e:
        print(f"Fatal error during sync: {str(e)}")
        exit(1)