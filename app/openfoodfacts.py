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
            params={"fields", fields},
        )
    except httpx.TimeoutException as e:
        return 
    except httpx.RequestError as e:
        return

    
    return
