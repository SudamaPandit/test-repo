"""Free official job-board API discovery. No applications are ever submitted."""
from __future__ import annotations
import html, json, os, re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import httpx

TITLE = re.compile(r"\b(?:data\s+(?:platform\s+|cloud\s+|pipeline\s+)?engineer|data\s+architect|analytics\s+engineer|etl\s+(?:developer|engineer)|big\s+data\s+engineer|databricks\s+engineer|spark\s+engineer|ing[eé]nieur\s+(?:de\s+)?donn[eé]es|dataingenj[oö]r)\b", re.I)
EXCLUDE_TITLE = re.compile(r"\b(?:intern|internship|working student|graduate|junior|trainee)\b", re.I)
NEGATIVE = re.compile(r"\b(?:no|without|not\s+(?:offer(?:ing)?|provid(?:e|ing)|available|eligible\s+for)|cannot|unable\s+to)\s+(?:work\s+)?visa\s+sponsorship\b|\bvisa\s+sponsorship\s+(?:not\s+(?:available|offered|provided)|is\s+unavailable)\b|\b(?:we\s+)?(?:do\s+not|don't|cannot|can't|won't|unable\s+to)\s+sponsor\b|\bmust\s+(?:already\s+)?(?:have|possess)\s+(?:the\s+)?(?:unrestricted\s+)?(?:right|authorization|authorisation)\s+to\s+work\b", re.I)
POSITIVE = re.compile(r"\b(?:visa\s+sponsorship\s+(?:is\s+)?(?:available|offered|provided)|(?:provide|offer|support|eligible\s+for)\s+(?:a\s+)?(?:work\s+)?visa\s+sponsorship|(?:we\s+)?(?:can|will|do)\s+sponsor\s+(?:work\s+)?visas?|(?:we\s+)?(?:can|will)\s+(?:provide|offer|support)\s+(?:a\s+)?(?:work\s+)?visa|(?:skilled\s+worker|subclass\s+482|employer)\s+(?:visa\s+)?sponsorship|sponsorship\s+(?:for\s+)?(?:work\s+)?visas?\s+(?:is\s+)?available|visa\s+(?:and\s+)?relocation\s+support)\b", re.I)
RELOCATION = re.compile(r"\b(?:relocation\s+(?:support|assistance|package)|visa\s+support|work\s+permit\s+support)\b", re.I)

def plain(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()

def extract_sponsorship(description: str) -> tuple[str, str]:
    content = plain(description)
    no, yes = NEGATIVE.search(content), POSITIVE.search(content)
    if no and (not yes or no.start() < yes.start() + 180):
        return "excluded_no_sponsorship", content[max(0, no.start()-60):no.end()+80].strip()
    if yes:
        return "explicit_description_claim", content[max(0, yes.start()-60):yes.end()+80].strip()
    rel = RELOCATION.search(content)
    if rel:
        return "relocation_only_unverified", content[max(0, rel.start()-40):rel.end()+60].strip()
    return "sponsorship_unverified", ""

def normalized_url(url: str) -> str:
    try:
        p = urlsplit(url)
        if p.scheme not in ("https", "http") or not p.netloc:
            return ""
        query = urlencode([(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                           if not k.casefold().startswith("utm_") and k.casefold() not in {"gclid", "fbclid", "ref", "source"}])
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), query, ""))
    except (ValueError, TypeError):
        return ""

def make_job(source: str, title: str, company: str, location: str, url: str,
             description: str, posted: str = "", provider_tagged: bool = False) -> dict:
    status, evidence = extract_sponsorship(description)
    # Job-fit signals drawn from the non-sensitive parts of the user's current CV.
    searchable = f"{title} {description}"
    skills = {
        "Python": r"\bpython\b",
        "SQL": r"\bsql\b",
        "PySpark/Spark": r"\b(?:pyspark|apache spark|spark structured streaming)\b",
        "AWS": r"\b(?:aws|amazon web services|s3|glue|redshift)\b",
        "GCP/BigQuery": r"\b(?:gcp|google cloud|bigquery|pub/sub)\b",
        "Azure/Databricks": r"\b(?:azure|databricks)\b",
        "Snowflake": r"\bsnowflake\b",
        "Airflow": r"\bairflow\b",
        "Kafka": r"\bkafka\b",
        "ETL/ELT": r"\b(?:etl|elt|data pipeline)\b",
    }
    matched = [name for name, rx in skills.items() if re.search(rx, searchable, re.I)]
    senior = bool(re.search(r"\b(?:senior|lead|staff|principal)\b", title, re.I))
    fit_score = min(100, 25 + 7 * len(matched) + (12 if senior else 0))
    return {"fit_score": fit_score, "matched_skills": matched,
            "source": source, "title": plain(title), "company": plain(company),
            "location": plain(location), "url": normalized_url(url), "posted": str(posted or ""),
            "sponsorship_status": status, "sponsorship_evidence": evidence,
            "provider_visa_tag": bool(provider_tagged),
            "verification": "Verify this vacancy and sponsorship on the employer website before applying."}

def get_json(client: httpx.Client, url: str, *, params=None, auth=None) -> dict:
    resp = client.get(url, params=params, auth=auth)
    resp.raise_for_status()
    result = resp.json()
    if not isinstance(result, dict):
        raise ValueError("API returned non-object JSON")
    return result

def fetch_arbeitnow(client: httpx.Client, uk: bool = False) -> list[dict]:
    host = "https://www.arbeitnow.co.uk" if uk else "https://www.arbeitnow.com"
    data = get_json(client, f"{host}/api/job-board-api", params={"visa_sponsorship": "true"})
    output = []
    for j in data.get("data", []):
        if not isinstance(j, dict):
            continue
        posted = j.get("created_at", "")
        if isinstance(posted, (int, float)):
            posted = datetime.fromtimestamp(posted, tz=timezone.utc).date().isoformat()
        output.append(make_job("Arbeitnow UK" if uk else "Arbeitnow Europe",
                              j.get("title",""),j.get("company_name",""),j.get("location",""),
                              j.get("url",""),j.get("description",""),posted,True))
    return output

def fetch_jobtech(client: httpx.Client, query: str) -> list[dict]:
    data = get_json(client, "https://jobsearch.api.jobtechdev.se/search",
                    params={"q":query,"limit":50,"offset":0})
    output = []
    for j in data.get("hits", []):
        desc, addr = j.get("description") or {}, j.get("workplace_address") or {}
        application, org = j.get("application_details") or {}, j.get("employer") or {}
        if not all(isinstance(z, dict) for z in [desc,addr,application,org]):
            continue
        loc = ", ".join(filter(None, [addr.get("municipality"),addr.get("region"),"Sweden"]))
        output.append(make_job("JobTech Sweden",j.get("headline",""),org.get("name",""),loc,
                               j.get("webpage_url") or application.get("url") or "",
                               desc.get("text") or desc.get("text_formatted") or "",
                               j.get("publication_date","")))
    return output

def fetch_adzuna(client: httpx.Client, query: str, country: str) -> list[dict]:
    if not (os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY")):
        return []
    params = {"app_id":os.environ["ADZUNA_APP_ID"],"app_key":os.environ["ADZUNA_APP_KEY"],
              "what":query,"results_per_page":50,"sort_by":"date"}
    if country == "au":
        params["where"]="Queensland"
    data = get_json(client,f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",params=params)
    output = []
    for j in data.get("results", []):
        location = j.get("location") or {}
        loc = location.get("display_name","") if isinstance(location,dict) else ""
        if country == "au" and not re.search(r"\b(?:Queensland|Brisbane|Gold Coast|Cairns|Townsville|Toowoomba|Sunshine Coast|Rockhampton|Mackay|Ipswich|Logan)\b",loc,re.I):
            continue
        org = j.get("company") or {}
        output.append(make_job(f"Adzuna {country.upper()}", j.get("title",""),
                               org.get("display_name","") if isinstance(org,dict) else "",
                               loc,j.get("redirect_url",""),j.get("description",""),j.get("created","")))
    return output

def fetch_reed(client: httpx.Client, query: str) -> list[dict]:
    key = os.getenv("REED_API_KEY")
    if not key:
        return []
    data = get_json(client,"https://www.reed.co.uk/api/1.0/search",
                    params={"keywords":query,"resultsToTake":40},auth=httpx.BasicAuth(key,""))
    return [make_job("Reed UK",j.get("jobTitle",""),j.get("employerName",""),
                     j.get("locationName","UK"),j.get("jobUrl",""),
                     j.get("jobDescription",""),j.get("date",""))
            for j in data.get("results",[])]

def fetch_jooble(client: httpx.Client, query: str, country: str) -> list[dict]:
    keys = json.loads(os.getenv("JOOBLE_KEYS_JSON","{}"))
    key = keys.get(country)
    if not key:
        return []
    domain = {"gb":"uk","au":"au","de":"de","fr":"fr","nl":"nl","ie":"ie"}.get(country)
    if not domain:
        return []
    payload = {"keywords":query,"page":"1"}
    if country == "au":
        payload["location"]="Queensland"
    resp = client.post(f"https://{domain}.jooble.org/api/{key}",json=payload)
    resp.raise_for_status()
    result = []
    for j in resp.json().get("jobs",[]):
        loc = j.get("location","")
        if country=="au" and not re.search(r"\b(?:QLD|Queensland|Brisbane|Gold Coast|Cairns|Townsville|Toowoomba|Sunshine Coast|Rockhampton|Mackay|Ipswich|Logan)\b",loc,re.I):
            continue
        result.append(make_job(f"Jooble {country.upper()}",j.get("title",""),
                               j.get("company",""),loc,j.get("link",""),j.get("snippet",""),j.get("updated","")))
    return result

def search_jobs(query: str = "senior data engineer", *, include_unverified=False,
                max_results: int = 25, client: httpx.Client | None = None) -> dict:
    if not 1 <= max_results <= 100:
        raise ValueError("max_results must be between 1 and 100")
    if not isinstance(query,str) or len(query)>100:
        raise ValueError("query must be a string of <= 100 characters")
    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=20,follow_redirects=True,headers={
            "User-Agent":"PersonalVisaJobFinder/1.0","Accept":"application/json"})
    sources = [("Arbeitnow Europe",lambda:fetch_arbeitnow(client)),
               ("Arbeitnow UK",lambda:fetch_arbeitnow(client,True)),
               ("JobTech Sweden",lambda:fetch_jobtech(client,query))]
    if os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"):
        sources.extend((f"Adzuna {c}",lambda c=c:fetch_adzuna(client,query,c))
                       for c in ["au","gb","de","nl","fr","ie"])
    if os.getenv("REED_API_KEY"):
        sources.append(("Reed UK",lambda:fetch_reed(client,query)))
    if os.getenv("JOOBLE_KEYS_JSON"):
        sources.extend((f"Jooble {c}",lambda c=c:fetch_jooble(client,query,c))
                       for c in ["au","gb","de","nl","fr","ie"])
    errors, jobs = {}, []
    try:
        for name, fetch in sources:
            try:
                jobs.extend(fetch())
            except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
                errors[name]=type(exc).__name__+": "+str(exc).split("?",1)[0][:160]
    finally:
        if owns_client:
            client.close()
    seen,results=set(),[]
    for j in jobs:
        if not TITLE.search(j["title"]) or EXCLUDE_TITLE.search(j["title"]):
            continue
        if j["sponsorship_status"]=="excluded_no_sponsorship":
            continue
        if not include_unverified and j["sponsorship_status"]!="explicit_description_claim":
            continue
        if not j["url"]:
            continue
        identity=(j["company"].casefold(),j["title"].casefold(),j["location"].casefold())
        if j["url"] in seen or identity in seen:
            continue
        seen.update((j["url"],identity))
        results.append(j)
    results.sort(key=lambda j:(j["sponsorship_status"]=="explicit_description_claim", j["fit_score"], j["posted"]),reverse=True)
    return {"jobs":results[:max_results],"total_matches":len(results),
            "searched_sources":[x[0] for x in sources],"source_errors":errors,
            "scope":"Europe + Queensland only in Australia",
            "submission_status":"No applications sent. Employer verification required."}
