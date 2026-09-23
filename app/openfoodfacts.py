# references
# https://openfoodfacts.github.io/openfoodfacts-server/api/  
# https://openfoodfacts.github.io/openfoodfacts-server/api/ref-v2/  (v2 product endpoint and the fields parameter)
# https://www.python-httpx.org/advanced/clients/    
# https://www.python-httpx.org/advanced/timeouts/    

# error fallback references
# https://docs.python.org/3/tutorial/errors.html#user-defined-exceptions
# https://docs.python.org/3/tutorial/errors.html#exception-chaining
# https://www.python-httpx.org/exceptions/
# https://www.python-httpx.org/advanced/timeouts/  
# https://docs.python.org/3/howto/logging.html

import logging
import httpx

logger = logging.getLogger(__name__)

base_url = "https://world.openfoodfacts.org"
fields = "code,product_name,categories_tags"
timeout = httpx.Timeout(5.0)

client = httpx.Client(
    base_url=base_url,
    timeout=timeout
)

# error fallbacks 
class BarcodeError(Exception):
    pass
class BarcodeNotFoundError(BarcodeError):
    pass
class BarcodeOverloadedError(BarcodeError):
    pass
class BarcodeTimeoutError(BarcodeError):
    pass
class BarcodeUpstreamError(BarcodeError):
    pass


# method to fetch the product from the barcode
def fetch_product(barcode: str) -> dict:

    try: 
        response = client.get(
            f"/api/v2/product/{barcode}.json",
            params={"fields": fields},
        )
    except httpx.TimeoutException as e:
        logger.warning("OFF timed out for barcode %s", barcode)
        raise BarcodeTimeoutError(barcode) from e
    
    except httpx.RequestError as e:
        logger.warning("OFF request failed for barcode %s: %s", barcode, e)
        raise BarcodeUpstreamError(barcode) from e

    # checking for other error codes 
    if response.status_code == 404:
        logger.info("OFF has no product for barcode %s", barcode)
        raise BarcodeNotFoundError(barcode)

    if response.status_code in (429, 503):
        logger.warning("OFF throttled us (%s) for barcode %s", response.status_code, barcode)
        raise BarcodeOverloadedError(barcode)

    if response.status_code != 200:
        logger.warning("OFF returned %s for barcode %s", response.status_code, barcode)
        raise BarcodeUpstreamError(barcode)


    # when the product from the barcode is retrieved (200)
    try:
        payload = response.json()
    except ValueError as e:
        logger.warning("OFF returned non-JSON for barcode %s", barcode)
        raise BarcodeUpstreamError(barcode) from e

    # if the product from the barcode is not retrieved
    product = payload.get("product")
    if payload.get("status") != 1 or not product:
        logger.info("OFF returned status 0 for barcode %s", barcode)
        raise BarcodeNotFoundError(barcode)
    
    return product
