# Vonage Integration Setup Guide

This guide will help you set up Vonage voice calling functionality for your Hiya Sales Agent.

## Prerequisites

1. **Vonage Account**: Sign up at [vonage.com](https://vonage.com)
2. **Python Environment**: Ensure you have Python 3.8+ installed
3. **ngrok**: For webhook handling during development

## Step 1: Vonage Account Setup

### 1.1 Create Vonage Account
1. Go to [vonage.com](https://vonage.com) and create an account
2. Verify your account and add payment method

### 1.2 Create Voice Application
1. Log into your Vonage dashboard
2. Navigate to "Applications" → "Create Application"
3. Fill in the application details:
   - **Name**: "Hiya Sales Agent"
   - **Type**: "Voice"
   - **Capabilities**: Enable "Voice" and "Webhooks"
4. Set webhook URLs:
   - **Answer URL**: `https://your-ngrok-url.ngrok.io/vonage/voice/input`
   - **Event URL**: `https://your-ngrok-url.ngrok.io/vonage/voice/status`
5. Save the application and note the **Application ID**

### 1.3 Generate Private Key
1. In your application settings, generate a private key
2. Download the `.pem` file
3. Place it in your project root directory (e.g., `vonage_private_key.pem`)

### 1.4 Purchase Phone Number
1. Go to "Numbers" → "Buy Numbers"
2. Search for available numbers in your region
3. Purchase a number and assign it to your application
4. Note the phone number (e.g., `+1234567890`)

## Step 2: Environment Configuration

### 2.1 Create .env File
Copy `env_sample.txt` to `.env` and fill in your Vonage credentials:

```bash
cp env_sample.txt .env
```

### 2.2 Configure Vonage Settings
Edit your `.env` file with your actual Vonage credentials:

```env
# Vonage Configuration
VONAGE_API_KEY=your_actual_api_key
VONAGE_API_SECRET=your_actual_api_secret
VONAGE_APPLICATION_ID=your_actual_application_id
VONAGE_PRIVATE_KEY_PATH=./vonage_private_key.pem
VONAGE_PHONE_NUMBER=+1234567890
VONAGE_WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io
```

**Important**: Replace `your-ngrok-url.ngrok.io` with your actual ngrok URL.

## Step 3: ngrok Setup (for Development)

### 3.1 Install ngrok
```bash
# Download from https://ngrok.com/download
# Or install via package manager
```

### 3.2 Start ngrok
```bash
# In a separate terminal
ngrok http 8000
```

### 3.3 Update Webhook URL
1. Copy the HTTPS URL from ngrok (e.g., `https://abc123.ngrok.io`)
2. Update `VONAGE_WEBHOOK_BASE_URL` in your `.env` file
3. Update the webhook URLs in your Vonage application dashboard

## Step 4: Testing the Integration

### 4.1 Run the Test Suite
```bash
python test_vonage_integration.py
```

This will test:
- ✅ Credential configuration
- ✅ Service initialization
- ✅ NCCO generation
- ✅ Webhook handler
- ✅ Call simulation

### 4.2 Test with Real Phone Number
```bash
python test_vonage_integration.py --call +1234567890
```

**Warning**: This will make an actual phone call!

### 4.3 Test via API
```bash
# Start the API server
python app/main.py

# Make a call via API
curl -X POST "http://localhost:8000/vonage/call" \
  -H "Content-Type: application/json" \
  -d '{
    "lead": {
      "id": "test",
      "name": "Test User",
      "phone": "+1234567890",
      "email": "test@example.com",
      "company": "Test Corp"
    }
  }'
```

## Step 5: Using the Streamlit UI

### 5.1 Start the Application
```bash
# Terminal 1: Start API server
python app/main.py

# Terminal 2: Start Streamlit UI
streamlit run app/streamlit_ui.py
```

### 5.2 Make Calls
1. Open the Streamlit UI at `http://localhost:8501`
2. Add a lead in the sidebar
3. Choose between:
   - **📞 Simulate**: Test the conversation flow
   - **📱 Real Call**: Make an actual phone call

## Step 6: Production Deployment

### 6.1 Webhook Configuration
For production, replace ngrok with a proper webhook URL:
```env
VONAGE_WEBHOOK_BASE_URL=https://your-production-domain.com
```

### 6.2 Security Considerations
- Store credentials securely (use environment variables)
- Use HTTPS for webhook URLs
- Implement proper authentication for webhook endpoints
- Monitor call usage and costs

## Troubleshooting

### Common Issues

1. **"Vonage client not initialized"**
   - Check that all environment variables are set
   - Verify the private key file exists and is readable

2. **"Webhook URL not configured"**
   - Ensure `VONAGE_WEBHOOK_BASE_URL` is set
   - Make sure ngrok is running and accessible

3. **"Failed to make call"**
   - Verify phone number format (include country code)
   - Check Vonage account balance
   - Ensure the application is properly configured

4. **Webhook not receiving events**
   - Check ngrok URL is correct
   - Verify webhook URLs in Vonage dashboard
   - Check firewall/network settings

### Debug Mode
Enable debug logging by setting:
```env
LOG_LEVEL=DEBUG
```

### Support
- Vonage Documentation: [developer.vonage.com](https://developer.vonage.com)
- Vonage Support: Available through your dashboard

## API Endpoints

### Make a Call
```http
POST /vonage/call
Content-Type: application/json

{
  "lead": {
    "id": "string",
    "name": "string", 
    "phone": "string",
    "email": "string",
    "company": "string"
  },
  "webhook_url": "string" // optional
}
```

### Response
```json
{
  "call_uuid": "string",
  "success": true,
  "message": "Call initiated successfully"
}
```

## Webhook Endpoints

The application automatically handles these Vonage webhooks:

- `POST /vonage/voice/input` - Handles speech input
- `POST /vonage/voice/status` - Handles call status updates
- `GET /vonage/calls` - Lists active calls (debug)

## Cost Considerations

- **Voice calls**: Charged per minute
- **SMS**: Charged per message (if used)
- **Phone numbers**: Monthly rental fee
- **Webhook calls**: Usually free

Monitor your usage in the Vonage dashboard to avoid unexpected charges.

