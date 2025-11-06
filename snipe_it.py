import os
import logging
import requests
import time
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Retrieve and validate Snipe-IT configuration from environment variables
SNIPE_IT_URL = os.getenv("SNIPE_IT_URL")
SNIPE_IT_API_KEY = os.getenv("SNIPE_IT_API_KEY")

# Validate required environment variables
if not SNIPE_IT_URL or not SNIPE_IT_API_KEY:
    raise ValueError("SNIPE_IT_URL and SNIPE_IT_API_KEY environment variables must be set")

# Global caches to minimize API calls
_entity_cache = {}  # Cache for models, categories, etc.
_cache_initialized = False


def _get_headers():
    """Helper function to create API headers with authentication. Used to avoid code duplication."""
    return {
        "accept": "application/json",
        "Authorization": f"Bearer {SNIPE_IT_API_KEY}",
        "Content-Type": "application/json"
    }


def _initialize_cache():
    """
    Pre-loads all categories and models into memory to minimize API calls.
    This is called once at startup before processing any devices.
    """
    global _entity_cache, _cache_initialized

    if _cache_initialized:
        return

    headers = _get_headers()
    logger.info("Initializing entity cache...")

    try:
        # Cache all categories
        logger.debug("Loading categories into cache...")
        response = requests.get(
            f"{SNIPE_IT_URL}/api/v1/categories?limit=500",
            headers=headers
        )
        if response.status_code == 200:
            for item in response.json().get("rows", []):
                cache_key = f"categories:{item['name']}"
                _entity_cache[cache_key] = item["id"]
            logger.debug(f"Cached {len([k for k in _entity_cache.keys() if k.startswith('categories:')])} categories")

        # Cache all models
        logger.debug("Loading models into cache...")
        response = requests.get(
            f"{SNIPE_IT_URL}/api/v1/models?limit=500",
            headers=headers
        )
        if response.status_code == 200:
            for item in response.json().get("rows", []):
                cache_key = f"models:{item['name']}"
                _entity_cache[cache_key] = item["id"]
            logger.debug(f"Cached {len([k for k in _entity_cache.keys() if k.startswith('models:')])} models")

        _cache_initialized = True
        logger.info("Entity cache initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize cache: {str(e)}. Will fall back to per-request lookups.")
        _cache_initialized = True


def find_asset_by_tag_or_serial(asset_tag=None, serial=None, max_retries=3):
    """
    Searches for an existing asset by asset tag or serial number.

    Args:
        asset_tag (str, optional): The asset tag to search for.
        serial (str, optional): The serial number to search for.
        max_retries (int): Maximum number of retry attempts for rate limiting.

    Returns:
        int: The asset ID if found, None otherwise.
    """
    headers = _get_headers()
    search_fields = []

    # Build list of search criteria to check
    if asset_tag:
        search_fields.append(("asset_tag", asset_tag))
    if serial:
        search_fields.append(("serial", serial))

    # Search for asset by each field
    for field_name, value in search_fields:
        logger.debug(f"Searching for asset by {field_name}: {value}")
        for attempt in range(max_retries):
            response = requests.get(
                f"{SNIPE_IT_URL}/api/v1/hardware",
                headers=headers,
                params={"search": value}
            )

            # Handle rate limiting with exponential backoff
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                else:
                    raise Exception(f"Rate limit exceeded after {max_retries} retries")

            # Search successful - check results
            if response.status_code == 200:
                for item in response.json().get("rows", []):
                    if item.get(field_name) == value:
                        logger.debug(f"Found existing asset with ID: {item['id']}")
                        return item["id"]
                break  # Found results but no match, don't retry
            else:
                raise Exception(f"Failed to search assets: {response.status_code} - {response.text}")

    return None


def get_or_create_entity(entity_type, name, additional_fields=None, max_retries=3):
    """
    Gets or creates an entity by name from Snipe-IT. This function is idempotent.
    Uses cache first to minimize API calls.

    Args:
        entity_type (str): The type of entity (e.g., "models", "categories", "statuses").
        name (str): The name of the entity.
        additional_fields (dict, optional): Additional fields required to create the entity.
        max_retries (int): Maximum number of retry attempts for rate limiting.

    Returns:
        int: The ID of the entity.

    Raises:
        Exception: If the entity cannot be retrieved or created.
    """
    headers = _get_headers()
    entity_singular = entity_type.rstrip('s')  # Convert plural to singular form

    # Check cache first
    cache_key = f"{entity_type}:{name}"
    if cache_key in _entity_cache:
        logger.debug(f"Found {entity_singular} '{name}' in cache with ID: {_entity_cache[cache_key]}")
        return _entity_cache[cache_key]

    logger.debug(f"Searching for {entity_singular} with name: {name}")
    # Search for the entity by name
    for attempt in range(max_retries):
        response = requests.get(
            f"{SNIPE_IT_URL}/api/v1/{entity_type}",
            headers=headers,
            params={"search": name}
        )

        # Handle rate limiting with exponential backoff
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 10))
            if attempt < max_retries - 1:
                logger.warning(f"Rate limit hit on search. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            else:
                raise Exception(f"Rate limit exceeded after {max_retries} retries during search")

        # Process search results
        if response.status_code == 200:
            results = response.json().get("rows", [])
            for result in results:
                if result.get("name") == name:
                    entity_id = result.get("id")
                    _entity_cache[cache_key] = entity_id
                    logger.debug(f"Found {entity_singular} with ID: {entity_id}")
                    return entity_id
            # Entity not found - proceed to creation
            break
        else:
            raise Exception(f"Failed to search {entity_type}: {response.status_code} - {response.text}")

    # Create the entity if not found
    payload = {"name": name}
    if additional_fields:
        payload.update(additional_fields)

    logger.info(f"Creating new {entity_singular} with name: {name}")
    for attempt in range(max_retries):
        post_response = requests.post(
            f"{SNIPE_IT_URL}/api/v1/{entity_type}",
            headers=headers,
            json=payload
        )

        # Handle rate limiting during creation
        if post_response.status_code == 429:
            retry_after = int(post_response.headers.get("Retry-After", 10))
            if attempt < max_retries - 1:
                logger.warning(f"Rate limit hit on create. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            else:
                raise Exception(f"Rate limit exceeded after {max_retries} retries during creation")

        # Success on creation
        if post_response.status_code in [200, 201]:
            entity_id = post_response.json()["payload"]["id"]
            _entity_cache[cache_key] = entity_id
            logger.info(f"Successfully created {entity_singular} with ID: {entity_id}")
            return entity_id
        else:
            raise Exception(f"Failed to create {entity_singular} '{name}': {post_response.status_code} - {post_response.text}")

    raise Exception(f"Failed to create {entity_singular} '{name}' after {max_retries} attempts")

def post_hardware_to_snipe_it(hardware_data, max_retries=3):
    """
    Posts hardware (asset) data to Snipe-IT. Creates new asset or updates existing one.
    This function is idempotent - safe to call multiple times with the same data.

    Args:
        hardware_data (dict): The hardware data to post (must include name, serial, asset_tag, etc.).
        max_retries (int): Maximum number of retry attempts for rate limiting.

    Returns:
        dict: A dictionary with "success" boolean and either "data" or "error" key.
    """
    headers = _get_headers()

    # Check if asset already exists by tag or serial number
    asset_id = find_asset_by_tag_or_serial(
        asset_tag=hardware_data.get("asset_tag"),
        serial=hardware_data.get("serial")
    )

    # Prepare data for API call (make a copy to avoid modifying original)
    data_to_send = hardware_data.copy()

    if asset_id:
        # Asset exists - update it via PUT request
        logger.info(f"Updating existing asset ID: {asset_id}")
        endpoint = f"{SNIPE_IT_URL}/api/v1/hardware/{asset_id}"

        # Remove fields that cannot be updated or are not applicable for PUT
        data_to_send.pop("serial", None)
        data_to_send.pop("status_id", None)

        # Attempt update with retry logic
        for attempt in range(max_retries):
            response = requests.put(endpoint, json=data_to_send, headers=headers)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                else:
                    return {
                        "success": False,
                        "status_code": 429,
                        "error": f"Rate limit exceeded after {max_retries} retries"
                    }

            if response.status_code in [200, 201]:
                logger.debug(f"Asset updated successfully")
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Failed to update asset: {response.status_code}")
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }

    else:
        # Asset does not exist - create it via POST request
        logger.info(f"Creating new asset: {hardware_data.get('name')}")

        # Attempt creation with retry logic
        for attempt in range(max_retries):
            response = requests.post(
                f"{SNIPE_IT_URL}/api/v1/hardware",
                json=data_to_send,
                headers=headers
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                else:
                    return {
                        "success": False,
                        "status_code": 429,
                        "error": f"Rate limit exceeded after {max_retries} retries"
                    }

            if response.status_code in [200, 201]:
                logger.debug(f"Asset created successfully")
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Failed to create asset: {response.status_code}")
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }

# Example usage
if __name__ == "__main__":
    model_name = "Example Model"
    status_name = "Ready to Deploy"
    company_name = "Example Company"

    try:
        model_id = get_or_create_entity("models", model_name, {"name": model_name})

        hardware_data = {
            "name": "Example Hardware",
            "serial": "123456789",
            "model_id": model_id,
            "status_id": 2,
            "company_id": 1
        }

        result = post_hardware_to_snipe_it(hardware_data)
        if result["success"]:
            print("Hardware information posted successfully:", result["data"])
        else:
            print("Failed to post hardware information:", result["status_code"], result["error"])
    except Exception as e:
        print("Error:", str(e))