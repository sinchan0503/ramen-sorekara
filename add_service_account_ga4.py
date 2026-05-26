"""GA4にサービスアカウントを閲覧者として追加するスクリプト（一回だけ実行）"""
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.analytics import admin

BASE_DIR = Path(__file__).parent
TOKEN_FILE = BASE_DIR / "blog_token.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"

GA4_PROPERTY_ID = "535135265"
SERVICE_ACCOUNT_EMAIL = "ramen-analytics@ramen-sorekara.iam.gserviceaccount.com"

SCOPES = [
    "https://www.googleapis.com/auth/analytics.manage.users",
]

# OAuth認証（管理者権限が必要）
creds = None
if TOKEN_FILE.exists():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

client = admin.AnalyticsAdminServiceClient(credentials=creds)

binding = admin.AccessBinding(
    user=SERVICE_ACCOUNT_EMAIL,
    roles=["predefinedRoles/viewer"],
)

result = client.create_access_binding(
    parent=f"properties/{GA4_PROPERTY_ID}",
    access_binding=binding,
)

print(f"✅ 追加完了: {result.user} → {result.roles}")
