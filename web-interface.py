from flask import Flask, request, render_template_string, redirect
import json
import os
import logging
import sys

from snmp_server import octet_string, integer, counter32, ip_address, timeticks

# Configure logging to output to console
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,  # Force override any existing logger configuration
)

# Also add werkzeug logger configuration
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.DEBUG)

# And add a handler to ensure we see the output
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
werkzeug_logger.addHandler(handler)

app = Flask(__name__)


# Add a basic route to test if Flask is working
@app.route("/test")
def test():
    logger.debug("Test route called")
    return "Flask server is running!"


# Add a basic route to show all registered routes
@app.route("/routes")
def show_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")
    return "<br>".join(routes)


# Update the DEFAULT_CONFIG to use only basic Python types
DEFAULT_CONFIG = """# SNMP Server Configuration

# Example OID configurations - these will be converted to proper SNMP types by the server
DATA = {
    # Simple string OID - System Description
    '1.3.6.1.2.1.1.1.0': 'Example SNMP Server',  # Will be converted to OCTET_STRING

    # System uptime
    '1.3.6.1.2.1.1.3.0': 123456,  # Will be converted to TIMETICKS

    # Simple integer value
    '1.3.6.1.2.1.1.4.0': 42,  # Will be converted to INTEGER

    # Basic counter
    '1.3.6.1.2.1.2.1.0': 1000,  # Will be converted to COUNTER32

    # IP address as string
    '1.3.6.1.2.1.3.1.0': '192.168.1.1',  # Will be converted to IPADDRESS

    # Function that returns dynamic value
    '1.3.6.1.2.1.4.1.0': lambda oid: len(oid),  # Function return value will be converted appropriately
}

# Note: The SNMP server will automatically convert these values to the appropriate SNMP types
# - Strings will become OCTET_STRING
# - Integers will become INTEGER
# - Functions must take one argument (the OID) and return a basic Python type
"""

# HTML template for the configuration page
CONFIG_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SNMP Server Configuration</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        textarea {
            width: 100%;
            height: 400px;
            margin: 20px 0;
            font-family: monospace;
            font-size: 14px;
            padding: 10px;
        }
        .button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .success { background-color: #dff0d8; color: #3c763d; }
        .error { background-color: #f2dede; color: #a94442; }
        .help {
            background-color: #f8f9fa;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>SNMP Server Configuration</h1>
        <div class="help">
            <h3>Configuration Help:</h3>
            <p>1. The configuration must define a DATA dictionary containing OID mappings.</p>
            <p>2. Each OID can map to:</p>
            <ul>
                <li>Strings (e.g., 'Example Server')</li>
                <li>Numbers (e.g., 42, 1000)</li>
                <li>IP addresses as strings (e.g., '192.168.1.1')</li>
                <li>Functions that return values (must take one argument)</li>
            </ul>
            <p>3. The SNMP server will automatically convert values to appropriate SNMP types.</p>
            <p>4. Changes will be automatically detected by the SNMP server.</p>
        </div>
        {% if status %}
        <div class="status {{ status_type }}">{{ status }}</div>
        {% endif %}
        <form method="POST">
            <textarea name="config" spellcheck="false">{{ config }}</textarea>
            <br>
            <input type="submit" value="Update Configuration" class="button">
        </form>
    </div>
</body>
</html>
"""


def read_config():
    """Read the current configuration file"""
    try:
        logger.debug("Attempting to read config.py")
        with open("config.py", "r") as f:
            content = f.read()
            logger.debug(
                f"Successfully read config.py: {content[:100]}..."
            )  # Log first 100 chars
            return content
    except FileNotFoundError:
        logger.warning("Config file not found, creating with default template")
        try:
            with open("config.py", "w") as f:
                f.write(DEFAULT_CONFIG)
                logger.info("Successfully created default config.py")
            return DEFAULT_CONFIG
        except Exception as e:
            logger.error(f"Error creating default config: {e}")
            return "# Error creating configuration file"
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return "# Error reading configuration file"


def write_config(config_content):
    """Write the configuration to file"""
    try:
        # Backup existing config
        if os.path.exists("config.py"):
            try:
                with open("config.py.bak", "w") as f:
                    f.write(read_config())
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")

        with open("config.py", "w") as f:
            f.write(config_content)
        logger.info("Configuration updated successfully")
        return True, "Configuration updated successfully"
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False, f"Error saving configuration: {str(e)}"


@app.route("/", methods=["GET", "POST"])
def config_editor():
    logger.debug(">>> config_editor route called <<<")
    try:
        logger.debug("Starting config_editor route handler")
        status = None
        status_type = None

        if request.method == "POST":
            logger.debug("Handling POST request")
            config_content = request.form["config"]
            logger.debug(f"Received config content: {config_content[:100]}...")
            try:
                # Create a temporary file to test the configuration
                with open("temp_config.py", "w") as f:
                    f.write(config_content)
                logger.debug("Wrote temporary config file")

                # Try to execute the config to verify it's valid Python
                temp_globals = {
                    "octet_string": octet_string,
                    "integer": integer,
                    "counter32": counter32,
                    "ip_address": ip_address,
                    "timeticks": timeticks,
                }
                with open("temp_config.py", "r") as f:
                    exec(f.read(), temp_globals)
                logger.debug(
                    f"Successfully executed config, globals: {list(temp_globals.keys())}"
                )

                # Check if DATA dictionary is defined
                if "DATA" not in temp_globals:
                    raise Exception("Configuration must define a DATA dictionary")

                # Validate DATA dictionary structure
                if not isinstance(temp_globals["DATA"], dict):
                    raise Exception("DATA must be a dictionary")

                # If we get here, the config is valid - save it
                success, message = write_config(config_content)
                status = message
                status_type = "success" if success else "error"

            except Exception as e:
                logger.error(f"Error processing configuration: {e}")
                status = f"Invalid configuration: {str(e)}"
                status_type = "error"
            finally:
                # Clean up temporary file
                if os.path.exists("temp_config.py"):
                    os.remove("temp_config.py")
                    logger.debug("Cleaned up temporary config file")

        current_config = read_config()
        logger.debug(f"Current config length: {len(current_config)}")
        logger.debug("Rendering template")

        rendered = render_template_string(
            CONFIG_TEMPLATE,
            config=current_config,
            status=status,
            status_type=status_type,
        )
        logger.debug(f"Template rendered, length: {len(rendered)}")
        return rendered
    except Exception as e:
        logger.error(f"Unexpected error in config_editor: {e}")
        return f"Error: {str(e)}", 500


if __name__ == "__main__":
    # Enable Flask debug mode
    app.debug = True
    logger.info("Starting Flask application on port 8080")

    # Print all registered routes at startup
    logger.info("Registered routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f"{rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")

    # Run the Flask application
    app.run(host="0.0.0.0", port=9999, use_reloader=True)
