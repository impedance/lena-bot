import logging
import re
import time
from datetime import datetime

import requests

from lena_bot.config import (
    BUDGET_MAX,
    ENABLE_FALLBACK_QUERY,
    EXPAND_CATALOG_PAGES,
    MAX_CATALOG_EXPAND_PER_RUN,
    MAX_CSE_CALLS_PER_DAY,
    MAX_ITEMS_PER_RUN_TO_SEND,
    MAX_LINKS_PER_CATALOG_PAGE,
    MAX_RESOLVE_PER_RUN,
    MIN_SURFACE,
    RESOLVE_DIRECT_LINKS,
    SEARCH_PROVIDER_ORDER,
    SITE_GROUPS,
    SLEEP_BETWEEN_CSE_CALLS,
    TELEGRAM_MAX_LEN,
    TG_CHAT,
    TG_TOKEN,
    build_queries,
)
from lena_bot.filters.criteria import criteria_check
from lena_bot.outputs.csv_export import write_run_csv
from lena_bot.outputs.telegram import telegram_send
from lena_bot.providers import BraveProvider, GoogleCSEProvider, TavilyProvider, chunk_sites
from lena_bot.storage.db import ensure_db, get_cse_calls, inc_cse_calls, insert_listing
from lena_bot.utils.url_tools import (
    domain_of,
    expand_catalog_page,
    extract_direct_url_from_query,
    is_catalog_url,
    is_known_direct_url,
    normalize_url,
    resolve_direct_url_soft,
)

logger = logging.getLogger(__name__)


PROVIDER_REGISTRY = {
    "google_cse": GoogleCSEProvider,
    "tavily": TavilyProvider,
    "brave": BraveProvider,
}


def build_enabled_providers():
    order = [x.strip().lower() for x in SEARCH_PROVIDER_ORDER.split(",") if x.strip()]
    providers = []
    seen = set()
    for name in order:
        if name in seen:
            continue
        provider_cls = PROVIDER_REGISTRY.get(name)
        if not provider_cls:
            logger.warning("Unknown provider in SEARCH_PROVIDER_ORDER: %s. Skip.", name)
            continue
        provider = provider_cls()
        if not provider.is_enabled():
            logger.info("Provider disabled (missing credentials): %s", name)
            continue
        providers.append(provider)
        seen.add(name)
    return providers


def run():
    if not TG_TOKEN or not TG_CHAT:
        raise SystemExit("❌ Mets TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID en variables d’environnement.")

    providers = build_enabled_providers()
    if not providers:
        raise SystemExit("❌ No enabled search providers. Configure at least one provider API key.")

    conn = ensure_db()
    new_rows_all = []
    new_rows_tg = []

    try:
        calls_today = get_cse_calls(conn)
        has_google = any(p.name == "google_cse" for p in providers)
        if has_google and calls_today >= MAX_CSE_CALLS_PER_DAY:
            logger.warning(
                "Google CSE quota already reached today (%d/%d); Google provider will be skipped.",
                calls_today,
                MAX_CSE_CALLS_PER_DAY,
            )

        session = requests.Session()
        resolve_left = MAX_RESOLVE_PER_RUN
        expand_left = MAX_CATALOG_EXPAND_PER_RUN

        levels = ["STRICT"]
        if ENABLE_FALLBACK_QUERY:
            levels.append("FALLBACK")

        safe_neg = '-"résultats" -"resultats" -"recherche" -"search"'

        for level in levels:
            queries = build_queries(level)

            for site_group, domains, group_hint in SITE_GROUPS:
                chunks = chunk_sites(domains, max_len=1600)

                for chunk_idx, chunk in enumerate(chunks, start=1):
                    sites_part = " OR ".join([f"site:{d}" for d in chunk])
                    hint = f"{group_hint} {safe_neg}"

                    for group_name, q in queries:
                        full_query = f"({sites_part}) {q} {hint}"

                        provider_succeeded = False
                        for provider in providers:
                            if provider.name == "google_cse" and get_cse_calls(conn) >= MAX_CSE_CALLS_PER_DAY:
                                logger.warning("Google quota reached during run, skipping provider google_cse.")
                                continue

                            provider_inserted = 0
                            inserted_page1 = 0

                            def handle_result(
                                res,
                                _level=level,
                                _site_group=site_group,
                                _group_name=group_name,
                                _full_query=full_query,
                            ):
                                nonlocal resolve_left, expand_left, inserted_page1, provider_inserted

                                raw_url = (res.url or "").strip()
                                url = normalize_url(raw_url)
                                title = (res.title or "").strip()
                                snippet = (res.snippet or "").strip()
                                domain = re.sub(r"^www\.", "", (res.display_domain or "").lower())

                                if not url:
                                    return

                                extracted = extract_direct_url_from_query(url)
                                if extracted:
                                    url = extracted
                                    domain = domain or domain_of(url)

                                cr = criteria_check(url, title, snippet, _level)
                                if cr.status == "EXCLUDED":
                                    return

                                suspect_catalog = is_catalog_url(url, title)

                                url_status = "DIRECT"
                                resolved_url = ""
                                resolved_note = ""
                                final_url_to_store = url

                                if is_known_direct_url(url):
                                    url_status = "DIRECT"
                                else:
                                    if suspect_catalog:
                                        url_status = "A_VERIFIER"
                                        resolved_note = "catalog_suspect"

                                        if EXPAND_CATALOG_PAGES and expand_left > 0 and domain_of(url) in (
                                            "immomarcq.fr",
                                            "abrinor.fr",
                                            "vacherand.fr",
                                            "immobiliere-duvieuxlille.com",
                                            "wasquehal-immobilier.fr",
                                        ):
                                            expand_left -= 1
                                            expanded = expand_catalog_page(url, session, MAX_LINKS_PER_CATALOG_PAGE)
                                            for eurl in expanded:
                                                edom = domain_of(eurl)
                                                ecr = criteria_check(eurl, title, snippet, _level)
                                                if ecr.status == "EXCLUDED":
                                                    continue
                                                erow = {
                                                    "date_detection": datetime.now().strftime("%Y-%m-%d"),
                                                    "heure_detection": datetime.now().strftime("%H:%M:%S"),
                                                    "site_group": _site_group,
                                                    "query_group": _group_name,
                                                    "query_level": _level,
                                                    "query_text": _full_query,
                                                    "source_domain": edom,
                                                    "title": title,
                                                    "snippet": snippet,
                                                    "raw_url": raw_url,
                                                    "url": eurl,
                                                    "url_status": "DIRECT" if is_known_direct_url(eurl) else "A_VERIFIER",
                                                    "resolved_url": "",
                                                    "resolved_note": f"expanded_from_catalog:{domain_of(url)}",
                                                    "criteria_status": ecr.status,
                                                    "criteria_note": ecr.note,
                                                }
                                                if insert_listing(conn, erow) == 1:
                                                    new_rows_all.append(erow)
                                                    provider_inserted += 1
                                                    if _level == "STRICT" and ecr.status == "OK":
                                                        new_rows_tg.append(erow)

                                        if RESOLVE_DIRECT_LINKS and resolve_left > 0:
                                            resolved, reason = resolve_direct_url_soft(url, session)
                                            resolve_left -= 1
                                            if resolved:
                                                final_url_to_store = normalize_url(resolved)
                                                resolved_url = final_url_to_store
                                                url_status = "DIRECT"
                                                resolved_note = f"resolved_{reason}"
                                            else:
                                                resolved_note = f"catalog_{reason}"

                                row = {
                                    "date_detection": datetime.now().strftime("%Y-%m-%d"),
                                    "heure_detection": datetime.now().strftime("%H:%M:%S"),
                                    "site_group": _site_group,
                                    "query_group": _group_name,
                                    "query_level": _level,
                                    "query_text": _full_query,
                                    "source_domain": domain or domain_of(final_url_to_store),
                                    "title": title,
                                    "snippet": snippet,
                                    "raw_url": raw_url,
                                    "url": final_url_to_store,
                                    "url_status": url_status,
                                    "resolved_url": resolved_url,
                                    "resolved_note": resolved_note,
                                    "criteria_status": cr.status,
                                    "criteria_note": cr.note,
                                }

                                if insert_listing(conn, row) == 1:
                                    inserted_page1 += 1
                                    provider_inserted += 1
                                    new_rows_all.append(row)
                                    if _level == "STRICT" and cr.status == "OK":
                                        new_rows_tg.append(row)

                            try:
                                page1_results = provider.search(full_query, start_index=1, site_domains=chunk)
                                if provider.name == "google_cse":
                                    inc_cse_calls(conn, 1)
                            except requests.RequestException as e:
                                logger.warning(
                                    "Provider error (%s, page1, level=%s, site_group=%s, chunk=%d): %s",
                                    provider.name,
                                    level,
                                    site_group,
                                    chunk_idx,
                                    e,
                                )
                                time.sleep(SLEEP_BETWEEN_CSE_CALLS)
                                continue

                            for item in page1_results:
                                handle_result(item)

                            time.sleep(SLEEP_BETWEEN_CSE_CALLS)

                            if provider.should_fetch_page11(len(page1_results), inserted_page1):
                                if provider.name == "google_cse" and get_cse_calls(conn) >= MAX_CSE_CALLS_PER_DAY:
                                    logger.warning("Google quota reached before page11; skipping second page.")
                                else:
                                    try:
                                        page11_results = provider.search(
                                            full_query,
                                            start_index=11,
                                            site_domains=chunk,
                                        )
                                        if provider.name == "google_cse":
                                            inc_cse_calls(conn, 1)
                                    except requests.RequestException as e:
                                        logger.warning(
                                            "Provider error (%s, page11, level=%s, site_group=%s, chunk=%d): %s",
                                            provider.name,
                                            level,
                                            site_group,
                                            chunk_idx,
                                            e,
                                        )
                                        time.sleep(SLEEP_BETWEEN_CSE_CALLS)
                                        page11_results = []

                                    for item in page11_results:
                                        handle_result(item)

                                    time.sleep(SLEEP_BETWEEN_CSE_CALLS)

                            logger.info(
                                "Provider %s -> + %d new rows (level=%s, site_group=%s, chunk=%d, query_group=%s)",
                                provider.name,
                                provider_inserted,
                                level,
                                site_group,
                                chunk_idx,
                                group_name,
                            )

                            if provider_inserted > 0:
                                provider_succeeded = True
                                break

                        if not provider_succeeded:
                            logger.info(
                                "No provider yielded new rows (level=%s, site_group=%s, chunk=%d, query_group=%s).",
                                level,
                                site_group,
                                chunk_idx,
                                group_name,
                            )

            if level == "STRICT" and ENABLE_FALLBACK_QUERY and len(new_rows_tg) >= 8:
                break

    finally:
        try:
            conn.close()
        except Exception:  # intentional: cleanup should never propagate
            pass

    if not new_rows_all:
        logger.info("Rien de nouveau.")
        return

    csv_file = write_run_csv(new_rows_all)
    if csv_file:
        logger.info("CSV créé : %s", csv_file)

    if not new_rows_tg:
        logger.info("Rien à envoyer sur Telegram (STRICT OK uniquement).")
        return

    to_send = new_rows_tg[:MAX_ITEMS_PER_RUN_TO_SEND]

    header = (
        f"🏡 Nouvelles annonces (STRICT + filtres forts) : {len(to_send)} / {len(new_rows_tg)}\n"
        f"Budget ≤ {BUDGET_MAX}€ | surface ≥{MIN_SURFACE}m² | ≥3 ch | terrain/jardin | gaz | garage | semi-mitoyenne | expo sud (selon texte indexé)\n"
        f"⚠️ A_VERIFIER = lien pas confirmé (Google a renvoyé une page liste / lien indirect).\n"
    )

    lines = [header]
    for sg in [g[0] for g in SITE_GROUPS]:
        sg_items = [x for x in to_send if x["site_group"] == sg]
        if not sg_items:
            continue
        lines.append(f"\n🌐 {sg} :")
        for group in ["GROUPE_A", "GROUPE_B"]:
            group_items = [x for x in sg_items if x["query_group"] == group]
            if not group_items:
                continue
            lines.append(f"  📍 {group} :")
            for r in group_items:
                tag = "⚠️ A_VERIFIER" if r["url_status"] == "A_VERIFIER" else ""
                dom = r["source_domain"]
                title = (r["title"] or "").strip()
                url = r["url"]
                lines.append(f"• [{dom}] {title} {tag}\n{url}")

    message = "\n".join(lines)

    if len(message) <= TELEGRAM_MAX_LEN:
        telegram_send(message)
    else:
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) + 1 > TELEGRAM_MAX_LEN:
                telegram_send(chunk)
                chunk = line
            else:
                chunk = chunk + ("\n" if chunk else "") + line
        if chunk:
            telegram_send(chunk)

    logger.info("Envoyé sur Telegram : %d annonces (STRICT OK).", len(to_send))
