"""Canonical security-related paths inside an Instagram JSON export."""

from __future__ import annotations

from export_inventory import FileGroup

LOGIN_ACTIVITY = FileGroup(
    key="login_activity",
    label="login history",
    relative_paths=(
        "security_and_login_information/login_and_profile_creation/login_activity.json",
        "security_and_login_information/login_and_account_creation/login_activity.json",
    ),
)

ACTIVE_SESSIONS = FileGroup(
    key="active_sessions",
    label="active sessions",
    relative_paths=(
        "security_and_login_information/login_and_profile_creation/active_sessions.json",
        "security_and_login_information/login_and_account_creation/active_sessions.json",
    ),
)

DEVICES = FileGroup(
    key="devices",
    label="login devices",
    relative_paths=(
        "security_and_login_information/login_and_profile_creation/login_activity.json",
        # Dedicated device files when Meta ships them:
        "security_and_login_information/login_and_profile_creation/your_devices.json",
        "security_and_login_information/login_and_account_creation/your_devices.json",
        "personal_information/device_information/devices.json",
        "personal_information/device_information/camera_information.json",
    ),
)

PASSWORD_CHANGES = FileGroup(
    key="password_changes",
    label="password change history",
    relative_paths=(
        "security_and_login_information/login_and_profile_creation/password_change_activity.json",
        "security_and_login_information/login_and_account_creation/password_change_activity.json",
    ),
)

EMAIL_CHANGES = FileGroup(
    key="email_changes",
    label="email change history",
    relative_paths=(
        "security_and_login_information/login_and_profile_creation/email_address_change.json",
        "security_and_login_information/login_and_account_creation/email_address_change.json",
        "security_and_login_information/login_and_profile_creation/email_change_activity.json",
    ),
)

LOGIN_PROTECTION = FileGroup(
    key="login_protection",
    label="login protection / 2FA signals",
    relative_paths=(
        "security_and_login_information/login_and_profile_creation/login_protection_data.json",
        "security_and_login_information/login_and_account_creation/login_protection_data.json",
        "security_and_login_information/login_and_profile_creation/two_factor_authentication.json",
        "security_and_login_information/authentication/two_factor_authentication.json",
    ),
)

# Devices group above double-counts login_activity for inventory aesthetics —
# use a dedicated inventory list without the login path duplication:
SECURITY_FILE_GROUPS: tuple[FileGroup, ...] = (
    LOGIN_ACTIVITY,
    ACTIVE_SESSIONS,
    FileGroup(
        key="devices",
        label="dedicated devices file",
        relative_paths=(
            "security_and_login_information/login_and_profile_creation/your_devices.json",
            "security_and_login_information/login_and_account_creation/your_devices.json",
            "personal_information/device_information/devices.json",
        ),
    ),
    PASSWORD_CHANGES,
    EMAIL_CHANGES,
    LOGIN_PROTECTION,
)
