"""NMIA interactive bootstrap CLI."""

from __future__ import annotations

import getpass

from nmia.auth.models import Role, User, UserRoleEnclave
from nmia.auth.security import hash_password
from nmia.core.db import SessionLocal

REQUIRED_ROLES: tuple[tuple[str, str], ...] = (
    ("GlobalAdmin", "Full administrative access across all enclaves."),
    ("EnclaveAdmin", "Administrative access scoped to one or more enclaves."),
    ("OwnerManager", "Manages identity ownership and stewardship assignments."),
    ("SecurityAnalyst", "Investigates identities and security findings."),
    ("Auditor", "Read-only access for audit and compliance reviews."),
)

MIN_PASSWORD_LENGTH = 12


def _prompt_admin_username() -> str:
    return input("Admin username [admin]: ").strip() or "admin"


def _prompt_admin_password() -> str:
    while True:
        password = getpass.getpass("Admin password: ")
        if len(password) < MIN_PASSWORD_LENGTH:
            print(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
            continue

        confirm = getpass.getpass("Confirm admin password: ")
        if password != confirm:
            print("Passwords do not match. Please try again.")
            continue

        return password


def _ensure_roles(db) -> Role:
    global_admin_role: Role | None = None
    for role_name, description in REQUIRED_ROLES:
        role = db.query(Role).filter(Role.name == role_name).first()
        if role is None:
            role = Role(name=role_name, description=description)
            db.add(role)
            db.flush()
            print(f"Created role: {role_name}")
        else:
            print(f"Role exists: {role_name}")

        if role_name == "GlobalAdmin":
            global_admin_role = role

    if global_admin_role is None:
        raise RuntimeError("GlobalAdmin role unavailable after role bootstrap.")

    return global_admin_role


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Bootstrap not required.")
            return

        username = _prompt_admin_username()
        password = _prompt_admin_password()

        global_admin_role = _ensure_roles(db)

        admin_user = User(
            username=username,
            password_hash=hash_password(password),
            email=f"{username}@nmia.local",
        )
        db.add(admin_user)
        db.flush()

        db.add(
            UserRoleEnclave(
                user_id=admin_user.id,
                role_id=global_admin_role.id,
                enclave_id=None,
            )
        )

        db.commit()

        print()
        print("Bootstrap complete.")
        print("Next steps:")
        print("  1) Start the UI (for example: cd ui && npm run dev)")
        print("  2) Log in with the admin credentials you just created")

    except KeyboardInterrupt:
        print("\nBootstrap cancelled.")
        db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
