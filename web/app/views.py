import os
from django.shortcuts import render, redirect
from .api_client import api_get, WooferAPIError, api_post

# Create your views here.

def home(request):
    """
    Disposable web landing page.
    Calls backend /api/health and prints the enveloped response.
    """
    try:
        api_result = api_get("/api/v1/pets?limit=5")
        WHY_SHOWN_COPY = {
    "LONG_STAY_BOOST": {
        "label": "Waiting longer",
        "blurb": "This pet has been listed for longer than most and deserves extra visibility."
    },
    "SENIOR_BOOST": {
        "label": "Senior",
        "blurb": "Senior pets are often overlooked, so we help them get seen."
    },
    "MEDICAL_BOOST": {
        "label": "Medical needs",
        "blurb": "Pets with medical needs can be harder to place, so we give them a boost."
    },
    "OVERLOOKED_GROUP_BOOST": {
        "label": "Often overlooked",
        "blurb": "Some pets are historically under-selected, so we correct for that bias."
    },
    "RECENTLY_RETURNED_BOOST": {
        "label": "Recently returned",
        "blurb": "This pet was returned and may need extra visibility to find a stable home."
    },
}

        return render(request, "home.html", {"api_result": api_result, "why_shown_copy": WHY_SHOWN_COPY})
    except WooferAPIError as e:
        # Canon: display API errors verbatim
        return render(request, "error.html", {"status_code": e.status_code, "payload": e.payload}, status=502)
    
def like_pet(request, pet_id):
    try:
        api_post(f"/api/v1/pets/{pet_id}/interest", {})
        return redirect("home")
    except WooferAPIError as e:
        return render(
            request,
            "error.html",
            {"status_code": e.status_code, "payload": e.payload},
            status=502,
        )

def apply_pet(request, pet_id, org_id):
    try:
        api_post(
            "/api/v1/applications",
            {
                "pet_id": str(pet_id),
                "organization_id": str(org_id),
                "payload": {},
            },
        )
        return render(
            request,
            "confirmation.html",
            {
                "message": "Application submitted.",
                "disclaimer": "This is not an approval. The rescue will contact you directly."
            },
        )
    except WooferAPIError as e:
        return render(
            request,
            "error.html",
            {"status_code": e.status_code, "payload": e.payload},
            status=502,
        )
