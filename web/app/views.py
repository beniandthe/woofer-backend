import os
from django.shortcuts import render, redirect
from .api_client import api_get, WooferAPIError, api_post, api_put

# Create your views here.

def home(request):
    """
    Disposable web landing page.
    Calls backend /api/health and prints the enveloped response.
    """
    try:
        api_result = api_get("/api/v1/pets?limit=1")
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
        liked = api_get("/api/v1/interests")
        liked_ids = set()
        for item in liked.get("data", {}).get("items", []):
            pet = item.get("pet", {})
            if pet.get("pet_id"):
                liked_ids.add(pet["pet_id"])

        return render(request, "home.html", {"api_result": api_result, "liked_ids": liked_ids, "why_shown_copy": WHY_SHOWN_COPY})
    except WooferAPIError as e:
        # Canon: display API errors verbatim
        return render(request, "error.html", {"status_code": e.status_code, "payload": e.payload}, status=502)

def _find_pet_in_feed(pet_id: str):
    """
    Lean MVP fallback if /api/v1/pets/{id} doesn't exist.
    Fetch first page of feed and search for a matching pet.
    """
    feed = api_get("/api/v1/pets?limit=50")
    for item in (feed.get("data", {}).get("items") or []):  
        if item.get("pet_id") == pet_id:
            return item
    return None
    
def like_pet(request, pet_id):
    try:
        before = api_get("/api/v1/interests")
        before_ids = {i.get("pet", {}).get("pet_id") for i in before.get("data", {}).get("items", [])}

        api_post(f"/api/v1/pets/{pet_id}/interest", {})
        if str(pet_id) in before_ids:
            return redirect("/?msg=already_liked")
        return redirect("/?msg=liked")
    except WooferAPIError as e:
        return render(
            request,
            "error.html",
            {"status_code": e.status_code, "payload": e.payload},
            status=502,
        )
    

def apply_pet(request, pet_id):
    """
    Controlled handoff v1 (Sprint 9.2):
    - POST backend apply endpoint
    - Render confirmation page
    - If apply_url exists, show continue link
    """
    if request.method != "POST":
        # Lean MVP: Apply is a POST-only action
        return redirect("/")

    try:
        result = api_post(
            f"/api/v1/pets/{pet_id}/apply",
            {"payload": {}},
        )
        data = result.get("data", {})

        return render(
            request,
            "apply_confirmation.html",
            {   
                "message": "Application request sent",
                "email_status": data.get("email_status"),
                "disclaimer": "This is not an approval. The rescue will contact you directly.",
                "apply_url": data.get("apply_url"),
                "apply_hint": data.get("apply_hint"),
            },
        )
    except WooferAPIError as e:
        return render(
            request,
            "error.html",
            {"status_code": e.status_code, "payload": e.payload},
            status=502,
        )

    # 2) Fallback: find in feed
    if pet is None:
        try:
            pet = _find_pet_in_feed(pet_id_str)
        except WooferAPIError as e:
            return render(
                request,
                "error.html",
                {"status_code": e.status_code, "payload": e.payload},
                status=502,
            )

    if not pet:
        return render(request, "apply_missing.html", {"pet_id": pet_id_str}, status=404)

    apply_url = (pet.get("apply_url") or "").strip()
    apply_hint = (pet.get("apply_hint") or "").strip()

    if apply_url:
        return redirect(apply_url)

    org = pet.get("organization") or {}
    return render(
        request,
        "apply_fallback.html",
        {"pet": pet, "organization": org, "apply_hint": apply_hint},
        status=200,
    )



def profile(request):
    """
    Thin client profile page.
    GET: fetch /api/v1/profile and render.
    POST: PUT /api/v1/profile with form payload.
    """
    try:
        if request.method == "POST":
            max_distance_raw = request.POST.get("max_distance_miles", "").strip()

            preferences = {}
            if max_distance_raw:
                try:
                    preferences["max_distance_miles"] = int(max_distance_raw)
                except ValueError:
                    # Lean MVP: ignore invalid input
                    preferences = {}

            payload = {
                "home_type": request.POST.get("home_type") or "OTHER",
                "has_kids": request.POST.get("has_kids") == "on",
                "has_dogs": request.POST.get("has_dogs") == "on",
                "has_cats": request.POST.get("has_cats") == "on",
                "activity_level": request.POST.get("activity_level") or "MED",
                "experience_level": request.POST.get("experience_level") or "SOME",
                "home_postal_code": (request.POST.get("home_postal_code") or "").strip(),
                "preferences": preferences,
            }

            api_put("/api/v1/profile", payload)

        api_result = api_get("/api/v1/profile")
        profile_data = api_result.get("data", {})

        return render(request, "profile.html", {"profile": profile_data, "msg": request.GET.get("msg")})
    except WooferAPIError as e:
        return render(
            request,
            "error.html",
            {"status_code": e.status_code, "payload": e.payload},
            status=502,
        )

def applications(request):
    try:
        api_result = api_get("/api/v1/applications")
        return render(request, "applications.html", {
            "items": api_result.get("data", {}).get("items", [])
        })
    except WooferAPIError as e:
        return render(
            request,
            "error.html",
            {"status_code": e.status_code, "payload": e.payload},
            status=502,
        )

def pass_pet(request, pet_id):
    try:
        api_post(f"/api/v1/pets/{pet_id}/pass", {})
        return redirect("/?msg=passed")
    except WooferAPIError as e:
        return render(
            request,
            "error.html",
            {"status_code": e.status_code, "payload": e.payload},
            status=502,
        )

def interests(request):
    """
    Saved / liked pets list.
    Uses backend /api/v1/interests (already canonical + enveloped).
    """
    try:
        api_result = api_get("/api/v1/interests")
        return render(request, "interests.html", {
            "items": api_result.get("data", {}).get("items", [])
        })
    except WooferAPIError as e:
        return render(
            request,
            "error.html",
            {"status_code": e.status_code, "payload": e.payload},
            status=502,
        )

