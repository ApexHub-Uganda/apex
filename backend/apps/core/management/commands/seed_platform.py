"""Seed platform with super admin, Ugandan schools, plans, and dashboard sample data."""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.academics.models import AcademicYear, Class, Department, Subject, Term
from apps.accounts.models import User
from apps.attendance.models import AttendanceRecord
from apps.audit.models import AuditLog
from apps.core.constants import COLOR_ACCENT, COLOR_PRIMARY, COLOR_SECONDARY, PlanSlug, UserRole
from apps.finance.models import FeePayment, FeeStructure, Invoice
from apps.platform.models import GlobalSetting, PlatformBroadcast, PlatformMetrics, SystemHealthLog
from apps.staff.models import Staff, Teacher
from apps.students.models import Parent, Student
from apps.subscriptions.models import PaymentProvider, PaymentTransaction, Plan, Subscription
from apps.subscriptions.seed_features import seed_feature_catalog, seed_plan_defaults
from apps.tenants.models import Tenant


UGANDAN_SCHOOLS = [
    {
        "name": "Kampala Royal Academy",
        "code": "KRA",
        "email": "admin@kampalaroyal.ug",
        "city": "Kampala",
        "country": "Uganda",
        "phone": "+256700100001",
        "plan": PlanSlug.PREMIUM_PLUS,
        "status": "active",
        "students": 180,
        "staff": 22,
    },
    {
        "name": "Wakiso Green Valley School",
        "code": "WGV",
        "email": "admin@wakisogreen.ug",
        "city": "Wakiso",
        "country": "Uganda",
        "phone": "+256700100002",
        "plan": PlanSlug.PREMIUM,
        "status": "active",
        "students": 120,
        "staff": 15,
    },
    {
        "name": "Jinja Sunrise Secondary",
        "code": "JSS",
        "email": "admin@jinasunrise.ug",
        "city": "Jinja",
        "country": "Uganda",
        "phone": "+256700100003",
        "plan": PlanSlug.BASIC,
        "status": "active",
        "students": 85,
        "staff": 10,
    },
    {
        "name": "Mbarara Hills College",
        "code": "MHC",
        "email": "admin@mbararahills.ug",
        "city": "Mbarara",
        "country": "Uganda",
        "phone": "+256700100004",
        "plan": PlanSlug.FREE_TRIAL,
        "status": "active",
        "sub_status": "trial",
        "students": 45,
        "staff": 6,
    },
    {
        "name": "Gulu Northern Star Academy",
        "code": "GNS",
        "email": "admin@gulunorthern.ug",
        "city": "Gulu",
        "country": "Uganda",
        "phone": "+256700100005",
        "plan": PlanSlug.PREMIUM,
        "status": "active",
        "students": 95,
        "staff": 12,
    },
    {
        "name": "Mbale Elite School",
        "code": "MES",
        "email": "admin@mbaleelite.ug",
        "city": "Mbale",
        "country": "Uganda",
        "phone": "+256700100006",
        "plan": PlanSlug.FREE_TRIAL,
        "status": "pending",
        "sub_status": "trial",
        "students": 0,
        "staff": 2,
    },
    {
        "name": "Entebbe Lakeside International",
        "code": "ELI",
        "email": "admin@entebelakeside.ug",
        "city": "Entebbe",
        "country": "Uganda",
        "phone": "+256700100007",
        "plan": PlanSlug.PREMIUM_PLUS,
        "status": "active",
        "students": 210,
        "staff": 28,
    },
    {
        "name": "Fort Portal Highlands School",
        "code": "FPH",
        "email": "admin@forthighlands.ug",
        "city": "Fort Portal",
        "country": "Uganda",
        "phone": "+256700100008",
        "plan": PlanSlug.BASIC,
        "status": "active",
        "students": 70,
        "staff": 9,
    },
    {
        "name": "Lira City Academy",
        "code": "LCA",
        "email": "admin@liracity.ug",
        "city": "Lira",
        "country": "Uganda",
        "phone": "+256700100009",
        "plan": PlanSlug.BASIC,
        "status": "active",
        "is_suspended": True,
        "students": 55,
        "staff": 7,
    },
    {
        "name": "Masaka Unity School",
        "code": "MUS",
        "email": "admin@masakaunity.ug",
        "city": "Masaka",
        "country": "Uganda",
        "phone": "+256700100010",
        "plan": PlanSlug.PREMIUM,
        "status": "active",
        "sub_status": "grace_period",
        "students": 60,
        "staff": 8,
    },
]


class Command(BaseCommand):
    help = "Seed Apex Hub platform with default data"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Re-run even if data exists")

    @transaction.atomic
    def handle(self, *args, **options):
        force = options["force"]
        self.stdout.write("Seeding Apex Hub platform...")

        if force:
            self._clear_data()

        self._seed_plans(force)
        super_admin = self._seed_super_admin(force)
        provider = self._seed_payment_provider(force)
        tenants = self._seed_schools(force)
        self._seed_platform_metrics(tenants)
        self._seed_system_health()
        self._seed_payment_transactions(tenants, provider)
        self._seed_audit_logs(super_admin, tenants)
        self._seed_platform_settings()
        self._seed_broadcasts()
        self._seed_demo_school_extras(tenants[0] if tenants else None)

        self.stdout.write(self.style.SUCCESS("\nSeed completed successfully!"))
        self.stdout.write(self.style.WARNING("\nDefault credentials:"))
        self.stdout.write("  Super Admin: superadmin@apexhub.io / ApexHub@2026")
        self.stdout.write("  School Admin: admin@kampalaroyal.ug / School@2026")

    def _clear_data(self) -> None:
        PaymentTransaction.objects.all().delete()
        Subscription.objects.all().delete()
        Tenant.objects.all().delete()
        AuditLog.objects.all().delete()
        SystemHealthLog.objects.all().delete()
        PlatformMetrics.objects.all().delete()
        PaymentProvider.objects.all().delete()
        self.stdout.write("  Cleared existing tenant and dashboard data.")

    def _seed_plans(self, force: bool) -> None:
        if Plan.objects.exists() and not force:
            self.stdout.write("  Plans already exist, skipping.")
            return

        seed_feature_catalog()

        plans_data = [
            {
                "name": "Free Trial",
                "slug": PlanSlug.FREE_TRIAL,
                "price_monthly": Decimal("0"),
                "price_yearly": Decimal("0"),
                "max_students": 50,
                "max_staff": 10,
                "max_parents": 100,
                "max_branches": 1,
                "max_sms_monthly": 0,
                "max_emails_monthly": 200,
                "trial_days": 14,
                "grace_period_days": 7,
                "sort_order": 0,
            },
            {
                "name": "Basic",
                "slug": PlanSlug.BASIC,
                "price_monthly": Decimal("49.00"),
                "price_yearly": Decimal("490.00"),
                "max_students": 200,
                "max_staff": 30,
                "max_parents": 400,
                "max_branches": 1,
                "max_sms_monthly": 100,
                "max_emails_monthly": 500,
                "trial_days": 14,
                "grace_period_days": 7,
                "sort_order": 1,
            },
            {
                "name": "Premium",
                "slug": PlanSlug.PREMIUM,
                "price_monthly": Decimal("99.00"),
                "price_yearly": Decimal("990.00"),
                "max_students": 500,
                "max_staff": 75,
                "max_parents": 1000,
                "max_branches": 3,
                "max_sms_monthly": 500,
                "max_emails_monthly": 2000,
                "trial_days": 14,
                "grace_period_days": 10,
                "sort_order": 2,
            },
            {
                "name": "Premium Plus",
                "slug": PlanSlug.PREMIUM_PLUS,
                "price_monthly": Decimal("199.00"),
                "price_yearly": Decimal("1990.00"),
                "max_students": 2000,
                "max_staff": 200,
                "max_parents": 5000,
                "max_branches": 10,
                "max_sms_monthly": 2000,
                "max_emails_monthly": 10000,
                "trial_days": 14,
                "grace_period_days": 14,
                "sort_order": 3,
            },
        ]

        for data in plans_data:
            Plan.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    **data,
                    "description": f"{data['name']} plan for schools",
                    "is_active": True,
                    "is_public": True,
                },
            )
        seed_plan_defaults()
        self.stdout.write(self.style.SUCCESS(f"  Created {len(plans_data)} subscription plans"))

    def _seed_super_admin(self, force: bool):
        email = "superadmin@apexhub.io"
        if User.objects.filter(email=email).exists() and not force:
            self.stdout.write("  Super admin already exists, skipping.")
            return User.objects.get(email=email)

        user = User.objects.create_superuser(
            email=email,
            password="ApexHub@2026",
            first_name="Super",
            last_name="Admin",
        )
        user.is_email_verified = True
        user.last_login_at = timezone.now()
        user.save()
        self.stdout.write(self.style.SUCCESS(f"  Created super admin: {email}"))
        return user

    def _seed_payment_provider(self, force: bool) -> PaymentProvider:
        if PaymentProvider.objects.exists() and not force:
            return PaymentProvider.objects.first()
        card_providers = [
            {"slug": "stripe", "name": "Stripe", "method_type": "card"},
            {"slug": "paypal", "name": "PayPal", "method_type": "card"},
        ]
        mobile_providers = [
            {"slug": "mpesa", "name": "M-Pesa", "method_type": "mobile_money"},
            {"slug": "mtn_momo", "name": "MTN MoMo", "method_type": "mobile_money"},
            {"slug": "airtel_money", "name": "Airtel Money", "method_type": "mobile_money"},
        ]
        provider = None
        for entry in [*card_providers, *mobile_providers]:
            obj, _ = PaymentProvider.objects.update_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["name"],
                    "method_type": entry["method_type"],
                    "is_active": entry["method_type"] == "card",
                    "is_sandbox": True,
                },
            )
            if entry["slug"] == "stripe":
                provider = obj
        self.stdout.write(self.style.SUCCESS("  Created payment providers (card + mobile money)"))
        return provider

    def _seed_schools(self, force: bool) -> list[Tenant]:
        if Tenant.objects.exists() and not force:
            self.stdout.write("  Schools already exist, skipping.")
            return list(Tenant.objects.all())

        tenants: list[Tenant] = []
        now = timezone.now()

        for idx, school in enumerate(UGANDAN_SCHOOLS):
            months_ago = len(UGANDAN_SCHOOLS) - idx
            created_at = now - timedelta(days=months_ago * 28 + random.randint(1, 10))

            tenant = Tenant.objects.create(
                name=school["name"],
                code=school["code"],
                email=school["email"],
                phone=school["phone"],
                address=f"{school['city']} District",
                city=school["city"],
                country=school["country"],
                timezone="Africa/Kampala",
                primary_color=COLOR_PRIMARY,
                secondary_color=COLOR_SECONDARY,
                accent_color=COLOR_ACCENT,
                tagline="Excellence in Education",
                status=school["status"],
                is_verified=school["status"] == "active",
                verified_at=created_at if school["status"] == "active" else None,
                is_suspended=school.get("is_suspended", False),
            )
            Tenant.objects.filter(pk=tenant.pk).update(created_at=created_at)

            admin = User.objects.create_user(
                email=school["email"],
                password="School@2026",
                first_name="School",
                last_name="Admin",
                role=UserRole.SCHOOL_ADMIN,
                tenant=tenant,
                is_email_verified=True,
                last_login_at=now - timedelta(hours=random.randint(1, 48)),
            )

            plan = Plan.objects.get(slug=school["plan"])
            sub_status = school.get("sub_status", "active")
            sub = Subscription.objects.create(
                tenant=tenant,
                plan=plan,
                status=sub_status,
                billing_cycle="monthly",
            )
            if sub_status == "active":
                sub.activate(period_days=30)
            Subscription.objects.filter(pk=sub.pk).update(
                created_at=created_at,
                started_at=created_at,
            )

            self._seed_school_people(tenant, admin, school)
            tenants.append(tenant)

        self.stdout.write(self.style.SUCCESS(f"  Created {len(tenants)} Ugandan schools"))
        return tenants

    def _seed_school_people(self, tenant: Tenant, admin: User, school: dict) -> None:
        if school["staff"] == 0 and school["students"] == 0:
            return

        year = AcademicYear.objects.create(
            tenant=tenant,
            name="2025/2026",
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            is_current=True,
            created_by=admin,
            updated_by=admin,
        )
        term = Term.objects.create(
            tenant=tenant,
            academic_year=year,
            name="Term 1",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
            is_current=True,
            created_by=admin,
            updated_by=admin,
        )
        dept = Department.objects.create(
            tenant=tenant,
            name="Sciences",
            code="SCI",
            created_by=admin,
            updated_by=admin,
        )
        Subject.objects.create(
            tenant=tenant, name="Mathematics", code="MATH", department=dept,
            created_by=admin, updated_by=admin,
        )

        school_class = Class.objects.create(
            tenant=tenant,
            name="S.1",
            code="S1",
            academic_year=year,
            capacity=50,
            room="Block A",
            created_by=admin,
            updated_by=admin,
        )

        for s in range(school["staff"]):
            Staff.objects.create(
                tenant=tenant,
                employee_id=f"{tenant.code}-EMP{s + 1:03d}",
                first_name=f"Staff{s + 1}",
                last_name=tenant.code,
                email=f"staff{s + 1}@{tenant.code.lower()}.ug",
                phone=f"+256700{random.randint(200000, 999999)}",
                designation="Teacher",
                date_joined=date(2024, 1, 1),
                status="active",
                created_by=admin,
                updated_by=admin,
            )

        parent = Parent.objects.create(
            tenant=tenant,
            first_name="Parent",
            last_name=tenant.code,
            email=f"parent@{tenant.code.lower()}.ug",
            phone=f"+256700{random.randint(200000, 999999)}",
            created_by=admin,
            updated_by=admin,
        )

        enrollment_base = timezone.now() - timedelta(days=150)
        for i in range(school["students"]):
            enrolled = enrollment_base + timedelta(days=random.randint(0, 140))
            student = Student.objects.create(
                tenant=tenant,
                admission_number=f"{tenant.code}-{i + 1:04d}",
                first_name=f"Student{i + 1}",
                last_name=tenant.code,
                date_of_birth=date(2010, 1, min(i + 1, 28)),
                gender="male" if i % 2 else "female",
                school_class=school_class,
                enrollment_date=enrolled.date(),
                status="active",
                created_by=admin,
                updated_by=admin,
            )
            Student.objects.filter(pk=student.pk).update(created_at=enrolled)
            if i == 0:
                student.parents.add(parent)

        fee_structure = FeeStructure.objects.create(
            tenant=tenant,
            name="Term 1 Tuition",
            school_class=school_class,
            term=term,
            amount=Decimal("500000"),
            due_date=date(2025, 10, 15),
            created_by=admin,
            updated_by=admin,
        )

        students = Student.objects.filter(tenant=tenant, is_deleted=False)[: min(5, school["students"])]
        for student in students:
            pay_date = date.today() - timedelta(days=random.randint(1, 60))
            FeePayment.objects.create(
                tenant=tenant,
                student=student,
                fee_structure=fee_structure,
                amount_paid=Decimal("250000"),
                payment_date=pay_date,
                payment_method="bank",
                status="completed",
                received_by=admin,
                created_by=admin,
                updated_by=admin,
            )
            Invoice.objects.create(
                tenant=tenant,
                student=student,
                invoice_number=f"INV-{tenant.code}-{student.admission_number}",
                issue_date=date(2025, 9, 1),
                due_date=date(2025, 10, 15),
                total_amount=Decimal("500000"),
                amount_paid=Decimal("250000"),
                status="sent",
                created_by=admin,
                updated_by=admin,
            )

    def _seed_platform_metrics(self, tenants: list[Tenant]) -> None:
        total_students = Student.objects.filter(is_deleted=False).count()
        total_staff = Staff.objects.filter(is_deleted=False).count()
        storage_used = total_students * 2 + total_staff * 1 + len(tenants) * 50
        storage_cap = max(len(tenants) * 2048, 10240)

        PlatformMetrics.objects.update_or_create(
            pk=1,
            defaults={
                "storage_used_mb": storage_used,
                "storage_cap_mb": storage_cap,
                "failed_jobs_24h": 0,
                "uptime_percent": Decimal("99.950"),
                "customer_satisfaction_percent": Decimal("94.50"),
                "feature_adoption_percent": Decimal("78.20"),
                "support_resolution_percent": Decimal("91.80"),
            },
        )
        self.stdout.write(self.style.SUCCESS("  Seeded platform metrics"))

    def _seed_system_health(self) -> None:
        if SystemHealthLog.objects.exists():
            return
        now = timezone.now()
        for days_ago in range(30, -1, -1):
            checked_at = now - timedelta(days=days_ago, hours=random.randint(0, 12))
            status = "healthy" if random.random() > 0.02 else "degraded"
            log = SystemHealthLog.objects.create(
                status=status,
                database_ok=True,
                redis_ok=status == "healthy",
                celery_ok=status == "healthy",
                response_time_ms=random.randint(12, 85),
            )
            SystemHealthLog.objects.filter(pk=log.pk).update(created_at=checked_at)
        self.stdout.write(self.style.SUCCESS("  Seeded system health logs"))

    def _seed_payment_transactions(self, tenants: list[Tenant], provider: PaymentProvider) -> None:
        if PaymentTransaction.objects.exists():
            return

        now = timezone.now()
        amounts = {
            PlanSlug.BASIC: Decimal("49.00"),
            PlanSlug.PREMIUM: Decimal("99.00"),
            PlanSlug.PREMIUM_PLUS: Decimal("199.00"),
        }

        for tenant in tenants:
            sub = tenant.subscriptions.first()
            if not sub or sub.plan.slug == PlanSlug.FREE_TRIAL:
                continue
            base_amount = amounts.get(sub.plan.slug, Decimal("49.00"))
            for month_offset in range(5, -1, -1):
                paid_at = now - timedelta(days=month_offset * 30 + random.randint(1, 5))
                ref = f"pay_{tenant.code}_{month_offset}_{uuid.uuid4().hex[:8]}"
                txn = PaymentTransaction.objects.create(
                    tenant=tenant,
                    subscription=sub,
                    provider=provider,
                    amount=base_amount,
                    currency="USD",
                    status="completed",
                    reference=ref,
                )
                PaymentTransaction.objects.filter(pk=txn.pk).update(created_at=paid_at)

        for i in range(3):
            tenant = random.choice([t for t in tenants if t.subscriptions.exists()])
            sub = tenant.subscriptions.first()
            failed_at = now - timedelta(days=random.randint(1, 25))
            ref = f"fail_{tenant.code}_{uuid.uuid4().hex[:8]}"
            txn = PaymentTransaction.objects.create(
                tenant=tenant,
                subscription=sub,
                provider=provider,
                amount=Decimal("99.00"),
                status="failed",
                reference=ref,
            )
            PaymentTransaction.objects.filter(pk=txn.pk).update(created_at=failed_at)

        self.stdout.write(self.style.SUCCESS("  Seeded payment transactions"))

    def _seed_audit_logs(self, super_admin: User, tenants: list[Tenant]) -> None:
        if AuditLog.objects.exists():
            return

        now = timezone.now()
        login_log = AuditLog.objects.create(
            user=super_admin,
            action="login",
            resource_type="auth",
            description="Super admin logged into platform dashboard",
            ip_address="102.68.12.44",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            request_method="POST",
            request_path="/api/v1/auth/login/",
            status_code=200,
            changes={"event": "login_success"},
        )
        AuditLog.objects.filter(pk=login_log.pk).update(created_at=now - timedelta(hours=2))

        for idx, tenant in enumerate(tenants[:6]):
            admin = User.objects.filter(tenant=tenant, role=UserRole.SCHOOL_ADMIN).first()
            reg_log = AuditLog.objects.create(
                tenant=tenant,
                user=admin,
                action="create",
                resource_type="tenant",
                resource_id=str(tenant.id),
                description=f"School registered: {tenant.name}",
                ip_address="102.68.10.10",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                request_method="POST",
                request_path="/api/v1/tenants/",
                status_code=201,
                changes={"status": {"from": None, "to": tenant.status}},
            )
            AuditLog.objects.filter(pk=reg_log.pk).update(
                created_at=now - timedelta(days=idx + 1, hours=3),
            )

        for tenant in tenants[:3]:
            sub = tenant.active_subscription
            if sub:
                sub_log = AuditLog.objects.create(
                    tenant=tenant,
                    action="update",
                    resource_type="subscription",
                    resource_id=str(sub.id),
                    description=f"Subscription active on {sub.plan.name} plan",
                    ip_address="102.68.11.20",
                    request_method="PATCH",
                    request_path=f"/api/v1/subscriptions/{sub.id}/",
                    status_code=200,
                    changes={"status": {"from": "trial", "to": sub.status}},
                )
                AuditLog.objects.filter(pk=sub_log.pk).update(
                    created_at=now - timedelta(days=random.randint(2, 10)),
                )

        AuditLog.objects.create(
            user=super_admin,
            action="export",
            resource_type="platform",
            description="Platform audit logs exported to PDF",
            ip_address="102.68.12.44",
            request_method="GET",
            request_path="/api/v1/audit/logs/export-pdf/",
            status_code=200,
        )
        AuditLog.objects.create(
            action="login",
            resource_type="auth",
            description="Failed login attempt — invalid credentials",
            ip_address="41.210.15.88",
            request_method="POST",
            request_path="/api/v1/auth/login/",
            status_code=401,
            changes={"event": "login_failed"},
        )

        self.stdout.write(self.style.SUCCESS("  Seeded audit logs"))

    def _seed_platform_settings(self) -> None:
        GlobalSetting.objects.update_or_create(
            key="platform_config",
            defaults={"value": {
                "platform_name": "Apex Hub",
                "platform_tagline": "The Easy Way",
                "support_email": "support@apexhub.io",
                "default_plan": "premium",
                "max_upload_size": 10,
                "default_timezone": "Africa/Kampala",
                "default_country": "Uganda",
            }},
        )
        GlobalSetting.objects.update_or_create(
            key="maintenance_mode",
            defaults={"value": {"enabled": False}},
        )
        self.stdout.write(self.style.SUCCESS("  Seeded platform settings"))

    def _seed_broadcasts(self) -> None:
        if PlatformBroadcast.objects.exists():
            return
        now = timezone.now()
        broadcasts = [
            {
                "title": "Welcome to Apex Hub",
                "message": "Your school management platform is ready. Explore the dashboard to get started.",
                "audience": "all",
                "status": "sent",
                "severity": "info",
                "starts_at": now - timedelta(days=5),
                "sent_at": now - timedelta(days=5),
            },
            {
                "title": "Scheduled Maintenance",
                "message": "Platform maintenance is scheduled this weekend. Expect brief downtime.",
                "audience": "all",
                "status": "sent",
                "severity": "warning",
                "starts_at": now - timedelta(days=2),
                "sent_at": now - timedelta(days=2),
            },
            {
                "title": "Premium Features Update",
                "message": "New analytics and reporting tools are now available for Premium plans.",
                "audience": "premium",
                "status": "draft",
                "severity": "info",
                "starts_at": now + timedelta(days=3),
            },
        ]
        for item in broadcasts:
            PlatformBroadcast.objects.create(**item)
        self.stdout.write(self.style.SUCCESS("  Seeded platform broadcasts"))

    def _seed_demo_school_extras(self, tenant: Tenant | None) -> None:
        if not tenant:
            return
        if AttendanceRecord.objects.filter(tenant=tenant).exists():
            return

        admin = User.objects.filter(tenant=tenant, role=UserRole.SCHOOL_ADMIN).first()
        students = Student.objects.filter(tenant=tenant, is_deleted=False)
        today = timezone.now().date()

        for offset in range(4, -1, -1):
            day = today - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            for student in students:
                status = "present" if random.random() > 0.08 else "absent"
                AttendanceRecord.objects.create(
                    tenant=tenant,
                    attendee_type="student",
                    student=student,
                    date=day,
                    status=status,
                    marked_by=admin,
                    created_by=admin,
                    updated_by=admin,
                )

        self.stdout.write(self.style.SUCCESS(f"  Seeded attendance for {tenant.name}"))