#!/bin/bash
# Setup YouTube OAuth 2.0 Credentials
# This script provides instructions and opens the Google Cloud Console

PROJECT_ID="change-agent-ai"
PROJECT_NUMBER="859417228841"
CLIENT_NAME="YouTube OAuth Client"
REDIRECT_URI="http://localhost:8000/api/v1/auth/youtube/callback"

echo "============================================================"
echo "YouTube OAuth 2.0 Setup for Video Shorts Generator"
echo "============================================================"
echo ""
echo "Project: $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
echo ""

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated. Please run: gcloud auth login"
    exit 1
fi

echo "✅ Authenticated as: $(gcloud config get-value account)"
echo ""

# Check if project is set
CURRENT_PROJECT=$(gcloud config get-value project)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "Setting project to $PROJECT_ID..."
    gcloud config set project $PROJECT_ID
fi

# Check if YouTube API is enabled
echo "Checking YouTube Data API v3..."
if gcloud services list --enabled --filter="name:youtube.googleapis.com" --format="value(name)" | grep -q youtube; then
    echo "✅ YouTube Data API v3 is enabled"
else
    echo "Enabling YouTube Data API v3..."
    gcloud services enable youtube.googleapis.com
    echo "✅ YouTube Data API v3 enabled"
fi

echo ""
echo "============================================================"
echo "OAuth Client Creation"
echo "============================================================"
echo ""
echo "⚠️  Note: OAuth 2.0 clients must be created via the web console."
echo "   Google Cloud doesn't provide a CLI command for this."
echo ""
echo "Follow these steps:"
echo ""
echo "1. OAuth Consent Screen (if not configured):"
echo "   URL: https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"
echo "   - User Type: External (or Internal for Workspace)"
echo "   - App name: Video Shorts Generator"
echo "   - User support email: $(gcloud config get-value account)"
echo "   - Developer contact: $(gcloud config get-value account)"
echo "   - Scopes: Add 'https://www.googleapis.com/auth/youtube.upload'"
echo "   - Save and Continue through all steps"
echo ""
echo "2. Create OAuth Client:"
echo "   URL: https://console.cloud.google.com/apis/credentials/oauthclient?project=$PROJECT_ID"
echo "   - Click '+ CREATE CREDENTIALS' > 'OAuth client ID'"
echo "   - Application type: Web application"
echo "   - Name: $CLIENT_NAME"
echo "   - Authorized redirect URIs:"
echo "     $REDIRECT_URI"
echo "   - Click 'Create'"
echo ""
echo "3. Copy the credentials:"
echo "   - Client ID (copy this)"
echo "   - Client Secret (copy this - shown only once!)"
echo ""
echo "4. Add to .env file:"
echo "   YOUTUBE_CLIENT_ID=<paste_client_id_here>"
echo "   YOUTUBE_CLIENT_SECRET=<paste_client_secret_here>"
echo ""

# Ask if user wants to open the console
read -p "Open OAuth credentials page in browser? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Opening browser..."
    open "https://console.cloud.google.com/apis/credentials/oauthclient?project=$PROJECT_ID"
fi

echo ""
echo "============================================================"
echo "Quick Reference"
echo "============================================================"
echo ""
echo "OAuth Consent Screen:"
echo "  https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"
echo ""
echo "Create OAuth Client:"
echo "  https://console.cloud.google.com/apis/credentials/oauthclient?project=$PROJECT_ID"
echo ""
echo "Redirect URI to add:"
echo "  $REDIRECT_URI"
echo ""

