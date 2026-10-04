"""Local MCP server exposing four TheMealDB recipe tools over STDIO."""

from __future__ import annotations

import logging
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


BASE_URL = "https://www.themealdb.com/api/json/v1/1"
REQUEST_TIMEOUT_SECONDS = 10.0

logger = logging.getLogger("meals")
if not logger.handlers:
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(stderr_handler)
logger.setLevel(logging.INFO)
logger.propagate = False

mcp = FastMCP("meals")


def _required_text(value: str, field_name: str) -> str:
    """Return a stripped required string or raise a client-friendly error."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _bounded_limit(limit: int, maximum: int = 25) -> int:
    """Validate a result limit shared by the two list tools."""
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if not 1 <= limit <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return limit


def _meal_id(value: str | int) -> str:
    """Validate and normalize a TheMealDB numeric meal identifier."""
    if isinstance(value, bool):
        raise ValueError("id must be a numeric meal id")
    normalized = str(value).strip()
    if not normalized.isdigit():
        raise ValueError("id must be a numeric meal id")
    return normalized


async def _fetch(endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Fetch and validate one JSON object from TheMealDB."""
    url = f"{BASE_URL}/{endpoint}"
    try:
        timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as error:
        logger.warning("TheMealDB request timed out: %s", error)
        raise RuntimeError("TheMealDB request timed out; please try again") from error
    except httpx.HTTPStatusError as error:
        logger.warning("TheMealDB HTTP error: %s", error)
        raise RuntimeError(
            f"TheMealDB returned HTTP {error.response.status_code}"
        ) from error
    except httpx.RequestError as error:
        logger.warning("TheMealDB network error: %s", error)
        raise RuntimeError("TheMealDB could not be reached; please try again") from error
    except ValueError as error:
        logger.warning("TheMealDB returned invalid JSON: %s", error)
        raise RuntimeError("TheMealDB returned invalid JSON") from error

    if not isinstance(payload, dict):
        raise RuntimeError("TheMealDB returned an unexpected JSON response")
    return payload


def _summary(meal: dict[str, Any]) -> dict[str, Any]:
    """Convert a search result into the required summary schema."""
    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "area": meal.get("strArea"),
        "category": meal.get("strCategory"),
        "thumb": meal.get("strMealThumb"),
    }


def _ingredient_card(meal: dict[str, Any]) -> dict[str, Any]:
    """Convert an ingredient-filter result into the required card schema."""
    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "thumb": meal.get("strMealThumb"),
    }


def _details(meal: dict[str, Any]) -> dict[str, Any]:
    """Convert a full API meal object into the required recipe schema."""
    ingredients: list[dict[str, str]] = []
    for number in range(1, 21):
        name = str(meal.get(f"strIngredient{number}") or "").strip()
        measure = str(meal.get(f"strMeasure{number}") or "").strip()
        if name:
            ingredients.append({"name": name, "measure": measure})

    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "category": meal.get("strCategory"),
        "area": meal.get("strArea"),
        "instructions": meal.get("strInstructions"),
        "image": meal.get("strMealThumb"),
        "source": meal.get("strSource"),
        "youtube": meal.get("strYoutube"),
        "ingredients": ingredients,
    }


def _meal_rows(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Validate the API's meals field while preserving its null no-match signal."""
    meals = payload.get("meals")
    if meals is None:
        return None
    if not isinstance(meals, list) or not all(isinstance(row, dict) for row in meals):
        raise RuntimeError("TheMealDB returned an unexpected meals response")
    return meals


@mcp.tool()
async def search_meals_by_name(
    query: str, limit: int = 5
) -> list[dict[str, Any]] | dict[str, Any]:
    """Search meal names and return up to 25 compact recipe summaries."""
    clean_query = _required_text(query, "query")
    clean_limit = _bounded_limit(limit)
    rows = _meal_rows(await _fetch("search.php", {"s": clean_query}))
    if rows is None:
        return {"results": [], "message": "no matches"}
    return [_summary(row) for row in rows[:clean_limit]]


@mcp.tool()
async def meals_by_ingredient(
    ingredient: str, limit: int = 12
) -> list[dict[str, Any]] | dict[str, Any]:
    """Find meals by one main ingredient and return compact recipe cards."""
    clean_ingredient = _required_text(ingredient, "ingredient")
    clean_limit = _bounded_limit(limit)
    rows = _meal_rows(await _fetch("filter.php", {"i": clean_ingredient}))
    if rows is None:
        return {"results": [], "message": "no matches"}
    return [_ingredient_card(row) for row in rows[:clean_limit]]


@mcp.tool()
async def random_meal() -> dict[str, Any]:
    """Return one random meal with full recipe details."""
    rows = _meal_rows(await _fetch("random.php"))
    if not rows:
        return {"result": None, "message": "no matches"}
    return _details(rows[0])


@mcp.tool()
async def meal_details(id: str | int) -> dict[str, Any]:
    """Look up one meal id and return its full recipe details."""
    clean_id = _meal_id(id)
    rows = _meal_rows(await _fetch("lookup.php", {"i": clean_id}))
    if not rows:
        return {"result": None, "message": "no matches"}
    return _details(rows[0])


if __name__ == "__main__":
    mcp.run(transport="stdio")
