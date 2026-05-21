"""
notion_reader.py — Чтение данных о криптосделках из базы данных Notion.
Конфигурация загружается из crypto_config.yaml (кроме API-ключа).
"""

import os
import json
import yaml
import requests
from datetime import datetime
from typing import Optional

NOTION_API_VERSION = "2022-06-28"

_config: dict = {}


def load_config(path: str = "crypto_config.yaml") -> dict:
    global _config
    base = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base, path)
    with open(full_path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    return _config


def _get_notion_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION
    }


def _extract_prop_value(prop: dict, debug_label: str = "") -> Optional[str]:
    if not prop:
        return None
    try:
        prop_type = prop.get("type", "")
        if prop_type == "title":
            title_arr = prop.get("title")
            if title_arr and title_arr[0]:
                val = title_arr[0].get("plain_text")
                return val.strip() if val else None
        elif prop_type == "rich_text":
            rt_arr = prop.get("rich_text")
            if rt_arr and rt_arr[0]:
                val = rt_arr[0].get("plain_text")
                return val.strip() if val else None
        elif prop_type == "select":
            sel = prop.get("select")
            if sel:
                val = sel.get("name")
                return val.strip() if val else None
        elif prop_type == "status":
            stat = prop.get("status")
            if stat:
                val = stat.get("name")
                return val.strip() if val else None
        elif prop_type == "formula":
            formula = prop.get("formula") or {}
            if not isinstance(formula, dict):
                formula = {}
            ftype = formula.get("type", "")
            if ftype == "string":
                val = formula.get("string")
                return val.strip() if val else None
            elif ftype == "number":
                val = formula.get("number")
                return str(val) if val is not None else None
            elif ftype == "boolean":
                val = formula.get("boolean")
                return str(val) if val is not None else None
            val = formula.get("number")
            if val is not None:
                return str(val)
            val = formula.get("string")
            if val is not None:
                return val.strip() if isinstance(val, str) else str(val)
        elif prop_type == "rollup":
            rollup = prop.get("rollup") or {}
            if not isinstance(rollup, dict):
                rollup = {}
            rtype = rollup.get("type", "")
            if rtype == "number":
                val = rollup.get("number")
                return str(val) if val is not None else None
            elif rtype == "string":
                val = rollup.get("string")
                return val.strip() if val else None
            val = rollup.get("number")
            if val is not None:
                return str(val)
            val = rollup.get("string")
            if val is not None:
                return val.strip() if isinstance(val, str) else str(val)
            arr = rollup.get("array")
            if arr and isinstance(arr, list) and len(arr) > 0:
                first = arr[0]
                if isinstance(first, dict):
                    if first.get("type") == "number":
                        val = first.get("number")
                        return str(val) if val is not None else None
        elif prop_type == "number":
            val = prop.get("number")
            return str(val) if val is not None else None
    except Exception:
        pass
    return None


def _to_float(raw: Optional[str], debug_label: str = "") -> Optional[float]:
    if raw is None:
        return None
    try:
        return float(raw.replace(',', '.').replace('%', '').replace('$', '').strip())
    except (ValueError, AttributeError):
        return None


def _is_active(props: dict) -> bool:
    field_active = _config.get("fields", {}).get("active", "").strip()
    if not field_active:
        return True
    if field_active not in props:
        return True
    raw_prop = props[field_active]
    raw = _extract_prop_value(raw_prop, debug_label=f"active/{field_active}")
    count = _to_float(raw, debug_label=f"active/{field_active}")
    if count is None:
        return True
    return count > 0


def read_deals() -> list[dict]:
    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
    database_id = _config.get("notion", {}).get("database_id", "")

    if not api_key or not database_id:
        print(f"[NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ Notion не настроен.")
        return []

    field_coin = _config.get("fields", {}).get("coin", "Монета")
    field_orders = _config.get("fields", {}).get("orders", "Ордера")
    field_profit_all = _config.get("fields", {}).get("profit_all", "").strip()

    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = _get_notion_headers(api_key)

    deals = []
    has_more = True
    start_cursor = None

    try:
        while has_more:
            payload = {"page_size": 100}
            if start_cursor:
                payload["start_cursor"] = start_cursor

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

            results = data.get("results", [])

            for idx, page in enumerate(results):
                try:
                    props = page.get("properties", {})

                    if not _is_active(props):
                        continue

                    coin_name = _extract_prop_value(props.get(field_coin), debug_label=f"coin/{field_coin}")
                    orders_raw = _extract_prop_value(props.get(field_orders), debug_label=f"orders/{field_orders}")
                    orders_val = _to_float(orders_raw, debug_label=f"orders/{field_orders}")
                    profit_all_val = None
                    if field_profit_all:
                        profit_all_raw = _extract_prop_value(props.get(field_profit_all), debug_label=f"profit_all/{field_profit_all}")
                        profit_all_val = _to_float(profit_all_raw, debug_label=f"profit_all/{field_profit_all}")

                    if coin_name:
                        deals.append({
                            "coin": coin_name,
                            "orders_usd": orders_val,
                            "profit_all_usd": profit_all_val,
                        })

                except Exception:
                    pass

        print(f"[NOTION] {datetime.now().strftime('%H:%M:%S')} ✅ Загружено {len(deals)} активных монет.")
        return deals

    except requests.exceptions.HTTPError as e:
        status = response.status_code
        print(f"[NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ HTTP {status}: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка сети: {e}")
        return []
    except Exception as e:
        print(f"[NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ Критическая ошибка: {e}")
        return []


def read_stats() -> list[dict]:
    """
    Читает базу торговой статистики (из секции stats конфига).
    Возвращает список записей: [{"name": "...", "fields": {"label": "value", ...}}, ...].
    """
    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
    stats_cfg = _config.get("stats", {})
    database_id = stats_cfg.get("database_id", "")

    if not api_key or not database_id:
        print(f"[NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ Stats DB не настроена.")
        return []

    name_field = stats_cfg.get("name_field", "Название")
    fields_cfg = stats_cfg.get("fields", [])

    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = _get_notion_headers(api_key)

    try:
        response = requests.post(url, headers=headers, json={"page_size": 100}, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception:
        print(f"[NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка чтения stats DB.")
        return []

    result = []
    for page in data.get("results", []):
        props = page.get("properties", {})
        name = _extract_prop_value(props.get(name_field), debug_label=f"stats/name/{name_field}")
        if not name:
            continue

        row = {"name": name, "fields": {}}
        for fdef in fields_cfg:
            nf = fdef.get("notion_field", "")
            label = fdef.get("label", nf)
            val = _extract_prop_value(props.get(nf), debug_label=f"stats/{nf}") or "—"
            row["fields"][label] = val
        result.append(row)

    print(f"[NOTION] {datetime.now().strftime('%H:%M:%S')} ✅ Stats: {len(result)} записей.")
    return result
