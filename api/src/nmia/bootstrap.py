"""
NMIA Bootstrap CLI
==================
Interactive first-run setup.  Creates roles, connector types, a default
enclave, and the initial GlobalAdmin user.

Usage:
    python -m nmia.bootstrap

The script refuses to run if any user already exists in the database
(i.e. bootstrap has already been performed).
"""

import getpass
import sys

from nmia.core.db import SessionLocal
from nmia.core.models import ConnectorType, Enclave
from nmia.auth.models import Role, User, UserRoleEnclave
from nmia.auth.security import hash_password


def main() -> None:
    print()
    print("=" * 60)
    print("  NMIA -- Non-Human Identity Authority")
    print("  First-Run Bootstrap")
    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        # ------------------------------------------------------------------
        # Guard: refuse to run if any user already exists
        # ------------------------------------------------------------------
        user_count = db.query(User).count()
        if user_count > 0:
            print("ERROR: Users already exist in the database.")
            print("Bootstrap has already been performed.")
            print("Use the API or direct database access to manage users.")
            sys.exit(1)

        # ------------------------------------------------------------------
        # [1/5] Seed RBAC roles
        # ------------------------------------------------------------------
        print("[1/5] Creating RBAC roles ...")
        default_roles = [
            {"name": "admin", "description": "Full administrative access across all enclaves."},
            {"name": "operator", "description": "Can manage connectors, run ingestion, and edit identities within assigned enclaves."},
            {"name": "viewer", "description": "Read-only access to data within assigned enclaves."},
            {"name": "auditor", "description": "Read-only access with visibility into audit logs and reports."},
        ]
        for r in default_roles:
            existing = db.query(Role).filter(Role.name == r["name"]).first()
            if existing is None:
                db.add(Role(**r))
                print(f"       + {r['name']}")
            else:
                print(f"       - {r['name']} (already exists)")
        db.flush()

        # ------------------------------------------------------------------
        # [2/5] Seed connector types
        # ------------------------------------------------------------------
        print("[2/5] Creating connector types ...")
        default_connector_types = [
            {
                "code": "ad_ldap",
                "name": "Active Directory (LDAP)",
                "description": "Connects to Active Directory via LDAP to discover service accounts and other non-human identities.",
            },
            {
                "code": "adcs_file",
                "name": "AD Certificate Services (File)",
                "description": "Ingests certificate data from exported CSV / JSON files produced by ADCS.",
            },
            {
                "code": "adcs_remote",
                "name": "AD Certificate Services (Remote)",
                "description": "Connects to a remote ADCS CA to enumerate issued certificates.",
            },
        ]
        for ct in default_connector_types:
            existing = db.query(ConnectorType).filter(ConnectorType.code == ct["code"]).first()
            if existing is None:
                db.add(ConnectorType(**ct))
                print(f"       + {ct['code']}")
            else:
                print(f"       - {ct['code']} (already exists)")
        db.flush()

        # ------------------------------------------------------------------
        # [3/5] Create default enclave
        # ------------------------------------------------------------------
        print("[3/5] Creating default enclave ...")
        default_enclave = db.query(Enclave).filter(Enclave.name == "Default").first()
        if default_enclave is None:
            default_enclave = Enclave(
                name="Default",
                description="Default enclave created during bootstrap.",
            )
            db.add(default_enclave)
            db.flush()
            print("       + Default")
        else:
            print("       - Default (already exists)")

        # ------------------------------------------------------------------
        # [4/5] Prompt for admin credentials
        # ------------------------------------------------------------------
        print("[4/5] Setting up GlobalAdmin account ...")
        print()
        username = input("  Admin username [admin]: ").strip() or "admin"

        while True:
            password = getpass.getpass("  Admin password: ")
            if len(password) < 8:
                print("  Password must be at least 8 characters. Try again.")
                continue
            confirm = getpass.getpass("  Confirm password: ")
            if password != confirm:
                print("  Passwords do not match. Try again.")
                continue
            break

        print()

        # ------------------------------------------------------------------
        # [5/5] Create admin user and assign role
        # ------------------------------------------------------------------
        print("[5/5] Creating admin user ...")
        admin_user = User(
            username=username,
            password_hash=hash_password(password),
            email=f"{username}@nmia.local",
        )
        db.add(admin_user)
        db.flush()

        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role is not None:
            assignment = UserRoleEnclave(
                user_id=admin_user.id,
                role_id=admin_role.id,
                enclave_id=default_enclave.id,
            )
            db.add(assignment)
        db.flush()

        print(f"       + User '{username}' created with admin role in 'Default' enclave.")

        # ------------------------------------------------------------------
        # Commit everything
        # ------------------------------------------------------------------
        db.commit()

        print()
        print("=" * 60)
        print("  Bootstrap complete!")
        print(f"  Username: {username}")
        print("  Login at: http://localhost:5173")
        print("=" * 60)
        print()

    except KeyboardInterrupt:
        print("\n\nBootstrap cancelled.")
        db.rollback()
        sys.exit(1)
    except SystemExit:
        db.rollback()
        raise
    except Exception as e:
        print(f"\nERROR: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
