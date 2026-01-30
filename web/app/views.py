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
        return render(request, "home.html", {"api_result": api_result})
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
