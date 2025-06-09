import pandas as pd
from datetime import datetime

# Create a sample DataFrame based on the structure requested
data = [
    ["outputs", "monitor", "/var/log/*.log,c://fhf/erro.log", "host,source", "server1,mani", "2025-06-04 10:00:00"],
    ["inputs", "monitor", "/var/log/auth.log", "host", "server2", "2025-06-04 10:05:00"],
    ["inputs", "monitor", "/var/log/nginx.log", "host", "server3", "2025-06-04 10:10:00"],
    ["inputs", "monitor", "/var/log/custom.log", "host", "server4", "2025-06-04 10:45:00"],
    ["outputs", "forwarder", "10.0.0.1:9997", "disabled", "false", "2025-06-04 10:15:00"],
    ["outputs", "forwarder", "10.0.0.2:9998", "disabled", "false", "2025-06-04 10:20:00"],
    ["outputs", "forwarder", "10.0.0.3:9999", "disabled", "true", "2025-06-04 10:25:00"],
    ["transforms", "regex", "^ERROR.*", "action", "drop", "2025-06-04 10:30:00"],
    ["transforms", "regex", "^WARN.*", "action", "alert", "2025-06-04 10:35:00"],
    ["transforms", "regex", "^INFO.*", "action", "keep", "2025-06-04 10:40:00"],
    ["app", "install", "", "state", "enable", ""],
    ["app", "ui", "", "is_visible,label", "true,hello", ""]
]

# Define column names
columns = ["config_type", "stanza_type", "stanza_value", "key", "value", "created_time"]

# Create DataFrame
df = pd.DataFrame(data, columns=columns)

# Save to Excel
excel_path = "splunk_config_data.xlsx"
df.to_excel(excel_path, index=False)

excel_path
