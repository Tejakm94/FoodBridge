# Product roadmap

## Phase 1 — Admin + Donor MVP (current)
- Donor registration/login.
- Verified ashrama directory.
- Donation request with food details and safe-consumption deadline.
- Admin dashboard, donor directory, ashrama verification and donation status management.
- Donor tracking timeline.

## Phase 2 — Delivery partner
- Partner registration, identity verification and admin approval.
- Assignment, pickup confirmation, live location (opt-in), route and delivery proof.
- Notifications to donor and receiving ashrama.
- Exception handling for rejected pickup, delays and cancellation.

## Phase 3 — Ashrama portal
- Ashrama user accounts and role-scoped access.
- View assigned incoming donations and accept/reject based on capacity and dietary needs.
- Confirm received quantity, condition, receipt time and optional photo proof.
- Report discrepancies and close delivery.

## Phase 4 — Production readiness
- Phone/email OTP, password reset, rate limiting, audit exports and backups.
- Consent and privacy policy, retention schedule, secure file uploads.
- Food safety SOPs, partner verification and operational escalation.
- Integration tests, accessibility, monitoring and deployment automation.

## Important domain rules
- A listing must be verified by an admin before donors can select it.
- Record prepared-at and safe-consumption deadline; reject expired windows.
- Keep an append-only status event history.
- Collect only necessary personal data and restrict it by role.
- Demo ashramas are sample data, not actual partner confirmations.
