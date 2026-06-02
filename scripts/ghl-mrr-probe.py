#!/usr/bin/env python3
"""
GHL MRR API Probe
-----------------
Checks whether GoHighLevel exposes per-client recurring amount + billing cadence
so we can compute true MRR from GHL (system of record).

Usage:
    GHL_TOKEN=<private_integration_token> GHL_LOCATION_ID=<location_id> python3 scripts/ghl-mrr-probe.py

Scopes required (read-only):
    payments/subscriptions.readonly
    payments/transactions.readonly
    invoices/schedule.readonly
    invoices.readonly
    contacts.readonly   (single-ID lookups only — no enumeration)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

BASE_URL = "https://services.leadconnectorhq.com"
TOKEN = os.environ.get("GHL_TOKEN", "")
LOCATION_ID = os.environ.get("GHL_LOCATION_ID", "")
SAMPLE_SIZE = 5  # max records to inspect per endpoint


def die(msg):
    print(f"\nFATAL: {msg}", file=sys.stderr)
    sys.exit(1)


if not TOKEN:
    die("GHL_TOKEN env var not set. Export your private integration token first.")
if not LOCATION_ID:
    die("GHL_LOCATION_ID env var not set. Export your sub-account location ID first.")


def ghl_get(path, params=None):
    """GET from GHL API, return parsed JSON body."""
    qs = ""
    if params:
        qs = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE_URL}{path}{qs}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"_error": e.code, "_body": body}
    except Exception as e:
        return {"_error": str(e)}


def extract_cadence_fields(record):
    """Pull out every cadence/billing-cycle field we can find in a record."""
    keys_of_interest = [
        "interval", "intervalCount", "interval_count", "billing_cycle",
        "billingCycle", "frequency", "period", "cadence",
        "recurring", "recurringAmount", "recurring_amount",
        "amount", "price", "total", "subtotal",
        "currency", "status", "entityId", "entityType",
        "contactId", "contact_id", "customerId",
        "nextBillingDate", "next_billing_date", "nextPaymentDate",
        "startDate", "start_date", "endDate", "end_date",
        "planId", "plan_id", "priceId", "price_id",
        "scheduleId", "subscriptionId",
    ]
    result = {}
    def _walk(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
                if any(k.lower() == ki.lower() for ki in keys_of_interest):
                    result[full_key] = v
                if isinstance(v, (dict, list)):
                    _walk(v, full_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:3]):
                _walk(item, f"{prefix}[{i}]")
    _walk(record)
    return result


def contact_name(contact_id):
    """Fetch a contact's display name by ID — single lookup, no enumeration."""
    if not contact_id:
        return "(no contact id)"
    r = ghl_get(f"/contacts/{contact_id}")
    if "_error" in r:
        return f"(lookup failed: {r['_error']})"
    c = r.get("contact", r)
    first = c.get("firstName") or c.get("first_name") or ""
    last = c.get("lastName") or c.get("last_name") or ""
    name = f"{first} {last}".strip()
    return name or f"(no name, id={contact_id})"


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def probe_subscriptions():
    section("1. SUBSCRIPTIONS  /payments/subscriptions/")
    params = {"locationId": LOCATION_ID, "status": "active", "limit": SAMPLE_SIZE}
    r = ghl_get("/payments/subscriptions/", params)

    if "_error" in r:
        print(f"  LIST ERROR: {r['_error']} — {r.get('_body','')[:300]}")
        return [], False, False

    subs = r.get("data", r.get("subscriptions", r.get("list", [])))
    if not isinstance(subs, list):
        # try unwrapping one level
        for v in r.values():
            if isinstance(v, list):
                subs = v
                break

    print(f"  Records returned: {len(subs)}")
    if not subs:
        print("  (empty — no active subscriptions found)")
        return [], False, False

    has_amount = False
    has_cadence = False
    rows = []

    for sub in subs[:SAMPLE_SIZE]:
        sub_id = sub.get("id") or sub.get("subscriptionId") or "(unknown)"
        contact_id = sub.get("contactId") or sub.get("contact_id") or sub.get("customerId")

        # Fetch full record for detail
        detail = ghl_get(f"/payments/subscriptions/{sub_id}")
        if "_error" in detail:
            detail = sub  # fall back to list record

        fields = extract_cadence_fields(detail)

        amount = (
            fields.get("amount") or fields.get("recurringAmount") or
            fields.get("recurring_amount") or fields.get("price") or
            fields.get("subtotal") or fields.get("total")
        )
        interval = (
            fields.get("interval") or fields.get("billing_cycle") or
            fields.get("billingCycle") or fields.get("frequency") or
            fields.get("cadence") or fields.get("period")
        )
        interval_count = (
            fields.get("intervalCount") or fields.get("interval_count")
        )
        currency = fields.get("currency", "")
        status = fields.get("status", sub.get("status", ""))

        if amount is not None:
            has_amount = True
        if interval is not None:
            has_cadence = True

        name = contact_name(contact_id) if contact_id else "(no contact)"

        cadence_str = str(interval) if interval else "(missing)"
        if interval_count and interval_count != 1:
            cadence_str += f" x{interval_count}"

        rows.append({
            "id": sub_id,
            "name": name,
            "amount": amount,
            "currency": currency,
            "cadence": cadence_str,
            "status": status,
            "source": "subscriptions endpoint",
            "_raw_fields": fields,
        })

        print(f"\n  [{sub_id}] {name}")
        print(f"    amount   : {amount} {currency}")
        print(f"    cadence  : {cadence_str}")
        print(f"    status   : {status}")
        print(f"    all_fields: {json.dumps(fields, indent=6)}")

    return rows, has_amount, has_cadence


def probe_invoice_schedules():
    section("2. INVOICE SCHEDULES  /invoices/schedule/")
    params = {"locationId": LOCATION_ID, "limit": SAMPLE_SIZE}
    r = ghl_get("/invoices/schedule/", params)

    if "_error" in r:
        print(f"  LIST ERROR: {r['_error']} — {r.get('_body','')[:300]}")
        return [], False, False

    schedules = r.get("data", r.get("list", r.get("schedules", [])))
    if not isinstance(schedules, list):
        for v in r.values():
            if isinstance(v, list):
                schedules = v
                break

    print(f"  Records returned: {len(schedules)}")
    if not schedules:
        print("  (empty)")
        return [], False, False

    has_amount = False
    has_cadence = False
    rows = []

    for sched in schedules[:SAMPLE_SIZE]:
        sched_id = sched.get("id") or sched.get("scheduleId") or "(unknown)"
        contact_id = sched.get("contactId") or sched.get("contact_id") or sched.get("customerId")

        detail = ghl_get(f"/invoices/schedule/{sched_id}")
        if "_error" in detail:
            detail = sched

        fields = extract_cadence_fields(detail)

        amount = (
            fields.get("amount") or fields.get("recurringAmount") or
            fields.get("total") or fields.get("subtotal") or fields.get("price")
        )
        interval = (
            fields.get("frequency") or fields.get("interval") or
            fields.get("billingCycle") or fields.get("billing_cycle") or
            fields.get("cadence") or fields.get("period")
        )
        interval_count = fields.get("intervalCount") or fields.get("interval_count")
        currency = fields.get("currency", "")
        status = fields.get("status", sched.get("status", ""))

        if amount is not None:
            has_amount = True
        if interval is not None:
            has_cadence = True

        name = contact_name(contact_id) if contact_id else "(no contact)"
        cadence_str = str(interval) if interval else "(missing)"
        if interval_count and interval_count != 1:
            cadence_str += f" x{interval_count}"

        rows.append({
            "id": sched_id,
            "name": name,
            "amount": amount,
            "currency": currency,
            "cadence": cadence_str,
            "status": status,
            "source": "invoice-schedule endpoint",
            "_raw_fields": fields,
        })

        print(f"\n  [{sched_id}] {name}")
        print(f"    amount   : {amount} {currency}")
        print(f"    cadence  : {cadence_str}")
        print(f"    status   : {status}")
        print(f"    all_fields: {json.dumps(fields, indent=6)}")

    return rows, has_amount, has_cadence


def probe_transactions():
    section("3. TRANSACTIONS  /payments/transactions/")
    params = {"locationId": LOCATION_ID, "limit": SAMPLE_SIZE}
    r = ghl_get("/payments/transactions/", params)

    if "_error" in r:
        print(f"  LIST ERROR: {r['_error']} — {r.get('_body','')[:300]}")
        return

    txns = r.get("data", r.get("transactions", r.get("list", [])))
    if not isinstance(txns, list):
        for v in r.values():
            if isinstance(v, list):
                txns = v
                break

    print(f"  Records returned: {len(txns)}")
    for t in txns[:SAMPLE_SIZE]:
        tid = t.get("id") or "(unknown)"
        amount = t.get("amount") or t.get("total") or "(missing)"
        currency = t.get("currency", "")
        status = t.get("status", "")
        date = t.get("date") or t.get("createdAt") or t.get("created_at") or ""
        entity_id = t.get("entityId") or t.get("subscriptionId") or t.get("invoiceId") or ""
        entity_type = t.get("entityType") or t.get("entity_type") or ""
        print(f"\n  [{tid}]  {amount} {currency}  status={status}  date={date}")
        print(f"    linked_to: {entity_type} {entity_id}")


def probe_invoices():
    section("4. INVOICES  /invoices/")
    params = {"locationId": LOCATION_ID, "limit": SAMPLE_SIZE}
    r = ghl_get("/invoices/", params)

    if "_error" in r:
        print(f"  LIST ERROR: {r['_error']} — {r.get('_body','')[:300]}")
        return

    invoices = r.get("data", r.get("invoices", r.get("list", [])))
    if not isinstance(invoices, list):
        for v in r.values():
            if isinstance(v, list):
                invoices = v
                break

    print(f"  Records returned: {len(invoices)}")
    for inv in invoices[:SAMPLE_SIZE]:
        inv_id = inv.get("id") or "(unknown)"
        amount = inv.get("total") or inv.get("amount") or "(missing)"
        currency = inv.get("currency", "")
        status = inv.get("status", "")
        contact_id = inv.get("contactId") or inv.get("contact_id")
        name = contact_name(contact_id) if contact_id else "(no contact)"
        is_recurring = inv.get("recurring") or inv.get("isRecurring") or inv.get("scheduleId")
        print(f"\n  [{inv_id}] {name}  {amount} {currency}  status={status}  recurring={is_recurring}")


def verdict(sub_amount, sub_cadence, sched_amount, sched_cadence):
    section("VERDICT")
    both_from_subs = sub_amount and sub_cadence
    both_from_schedules = sched_amount and sched_cadence
    any_amount = sub_amount or sched_amount
    any_cadence = sub_cadence or sched_cadence

    if both_from_subs or both_from_schedules:
        rating = "GREEN"
        source = "subscriptions" if both_from_subs else "invoice schedules"
        detail = (
            f"Both recurring amount AND cadence are present in the {source} endpoint.\n"
            "  Build the MRR task to read GHL directly, normalize intervals to monthly,\n"
            "  and reconcile against Stripe transactions."
        )
    elif any_amount and any_cadence:
        rating = "AMBER"
        detail = (
            "Amount and cadence are present but split across endpoints, or one is thin.\n"
            "  Build the MRR task to read what's reliable from each endpoint and flag gaps.\n"
            "  Confirm totals against the GHL dashboard."
        )
    elif any_amount or any_cadence:
        rating = "AMBER"
        detail = (
            f"Only {'amount' if any_amount else 'cadence'} is present. The other is missing.\n"
            "  Read what's available; manually confirm the missing dimension from the GHL dashboard."
        )
    else:
        rating = "RED"
        detail = (
            "Neither endpoint returns clean per-client amount + cadence.\n"
            "  Fall back to the GHL dashboard as the truth number.\n"
            "  The MRR task only reconciles Stripe actuals against a manually confirmed figure."
        )

    print(f"\n  RATING: {rating}")
    print(f"\n  {detail}")
    print(f"\n  Subscriptions   → amount: {'YES' if sub_amount else 'NO'}  cadence: {'YES' if sub_cadence else 'NO'}")
    print(f"  Inv. schedules  → amount: {'YES' if sched_amount else 'NO'}  cadence: {'YES' if sched_cadence else 'NO'}")
    print()


def main():
    print(f"GHL MRR Probe  —  location={LOCATION_ID}  —  {datetime.utcnow().isoformat()}Z")

    sub_rows, sub_amount, sub_cadence = probe_subscriptions()
    sched_rows, sched_amount, sched_cadence = probe_invoice_schedules()
    probe_transactions()
    probe_invoices()
    verdict(sub_amount, sub_cadence, sched_amount, sched_cadence)


if __name__ == "__main__":
    main()
