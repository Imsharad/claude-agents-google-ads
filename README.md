# Google Ads Automation Agent

This repository contains the source code for a Google Ads automation agent.

## Setup

### 1. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

*(Note: A `requirements.txt` file will be added in a future task.)*

### 2. Configure Google Ads API Credentials

To use this tool, you need to authenticate with the Google Ads API.

#### Prerequisites:
- A Google Ads manager account.
- A developer token from your manager account.
- An OAuth 2.0 client ID and client secret.

#### Steps:

1. **Copy the example configuration file:**

   ```bash
   cp google-ads.yaml.example google-ads.yaml
   ```

2. **Find your Developer Token:**
   - Log in to your Google Ads manager account.
   - Navigate to **Tools & Settings > API Center**.
   - Your developer token will be listed there.

3. **Generate OAuth 2.0 Credentials:**
   - Go to the [Google API Console](https://console.developers.google.com/).
   - Create a new project or select an existing one.
   - Enable the **Google Ads API**.
   - Go to **Credentials**, click **Create Credentials**, and choose **OAuth client ID**.
   - Select **Desktop app** as the application type.
   - Copy the **Client ID** and **Client Secret**.

4. **Generate a Refresh Token:**
   - The Google Ads Python client library includes a tool to generate a refresh token.
   - Download the `generate_refresh_token.py` script from the [google-ads-python repository](https://github.com/googleads/google-ads-python/blob/main/examples/authentication/generate_refresh_token.py).
   - Run the script with your client ID and client secret:
     ```bash
     python generate_refresh_token.py --client_id YOUR_CLIENT_ID --client_secret YOUR_CLIENT_SECRET
     ```
   - Follow the on-screen instructions to authorize the application. The script will output a refresh token.

5. **Update `google-ads.yaml`:**
   - Open the `google-ads.yaml` file and fill in the following values:
     - `developer_token`
     - `client_id`
     - `client_secret`
     - `refresh_token`
     - `login_customer_id`: This is the 10-digit customer ID of your manager account (without hyphens).

   **Important:** The `google-ads.yaml` file contains sensitive credentials and is included in `.gitignore` to prevent it from being committed to version control.

### 3. Test the Connection

Run the connection test script to verify that your configuration is correct:

```bash
python scripts/test_connection.py
```

If the connection is successful, you will see a "Connection Test: SUCCESS" message and a list of your accessible customer accounts.
