import os
import logging
from app import app
import config

# Set up logging
logging.basicConfig(level=logging.INFO if config.IS_DEPLOYED else logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Only use debug mode in development, not in production
    debug_mode = not config.IS_DEPLOYED
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)
