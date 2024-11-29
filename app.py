# File: app.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import re
from typing import List, Dict, Optional
import logging

# Initialize FastAPI app
app = FastAPI()

# PostgreSQL connection configuration
DB_CONFIG = {
    "dbname": "Baby Products",
    "user": "postgres",
    "password": "Nikola2007$#",
    "host": "localhost",
    "port": 5432
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Input schema for the query
class QueryInput(BaseModel):
    last_utterance: str

# Connect to the PostgreSQL database
def connect_to_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Database connection established successfully.")
        return conn
    except Exception as e:
        logger.error("Failed to connect to the database: %s", e)
        raise HTTPException(status_code=500, detail="Database connection failed") from e
    
    # Normalize range or single values with units
def normalize_range(value: str, unit: str) -> Optional[str]:
    """
    Normalize a range or single value with a unit.
    Example: "4-10 кг." becomes "4-10кг", "7 кг." becomes "7кг".
    """
    # Match ranges like "4-10 кг." or "4 – 10 кг."
    range_match = re.match(r"(\d+)\s*[-–]\s*(\d+)", value)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}{unit}"
    
    # Match single values like "7 кг."
    single_match = re.match(r"(\d+)", value)
    if single_match:
        return f"{single_match.group(1)}{unit}"
    
    # If no match is found, return None
    return None

# Extract keywords based on the query
def extract_keywords(query: str) -> Dict:
    # Synonym mappings
    synonym_mapping = {
        "product_name": {
            "шише": "шишета",
            "шишенца": "шишета",
            "бутилка": "шишета",
            "лигавник": "лигавник",
            "памперси": "памперси",
            "бебешки крем": "бебешки крем",
        },
        "allergens": {
            "без": "Без",
            "без алергени": "Без",
            "без парфюм": "Без",
            "без латекс": "Без",
        },
    }

    # Extract patterns
    product_pattern = r"\b(шише|шишенца|бутилка|лигавник|памперси|бебешки крем)\b"
    allergen_pattern = r"\b(без|без алергени|без парфюм|без латекс)\b"
    weight_pattern = r"\b(\d+\s*кг\.?)\b"
    age_pattern = r"\b(\d+\s*м\.?)\b"

    product = re.search(product_pattern, query, re.IGNORECASE)
    allergen = re.search(allergen_pattern, query, re.IGNORECASE)
    weight = re.search(weight_pattern, query, re.IGNORECASE)
    age = re.search(age_pattern, query, re.IGNORECASE)

    # Map and normalize values
    filters = {
        "product_name": synonym_mapping["product_name"].get(
            product.group(0).lower(), product.group(0)
        ) if product else None,
        "allergens": synonym_mapping["allergens"].get(
            allergen.group(0).lower(), allergen.group(0)
        ) if allergen else None,
        "weight": normalize_range(weight.group(0), "кг") if weight else None,
        "recommended_age": normalize_range(age.group(0), "месеца") if age else None,
    }

    


def extract_keywords(query: str) -> Dict:
    # Synonym mappings
    synonym_mapping = {
        "product_name": {
            "шише": "шишета",
            "шишенца": "шишета",
            "бутилка": "шишета",
            "лигавник": "лигавник",
            "памперси": "памперси",
            "бебешки крем": "бебешки крем",
        },
        "allergens": {
            "без": "Без",
            "без алергени": "Без",
            "без парфюм": "Без",
            "без латекс": "Без",
        },
    }

    # Extract patterns
    product_pattern = r"\b(шише|шишенца|бутилка|лигавник|памперси|бебешки крем)\b"
    allergen_pattern = r"\b(без|без алергени|без парфюм|без латекс)\b"
    weight_pattern = r"\b(\d+\s*кг\.?)\b"
    age_pattern = r"\b(\d+\s*м\.?)\b"

    product = re.search(product_pattern, query, re.IGNORECASE)
    allergen = re.search(allergen_pattern, query, re.IGNORECASE)
    weight = re.search(weight_pattern, query, re.IGNORECASE)
    age = re.search(age_pattern, query, re.IGNORECASE)

    # Map and normalize values
    filters = {
        "product_name": synonym_mapping["product_name"].get(
            product.group(0).lower(), product.group(0)
         ) if product else None,
         "allergens": synonym_mapping["allergens"].get(
            allergen.group(0).lower(), allergen.group(0)
         ) if allergen else None,
         "weight": normalize_range(weight.group(0), "кг") if weight else None,
         "recommended_age": normalize_range(age.group(0), "месеца") if age else None,
    }

    logger.info("Extracted filters: %s", filters)
    return filters







def query_database(filters: Dict) -> List[Dict]:
    """
    Query the database using normalized filters.
    """
    conn = connect_to_db()
    cursor = conn.cursor()

    # Build SQL dynamically
    sql = "SELECT * FROM babys_products WHERE 1=1"
    params = []

    if filters["product_name"]:
        sql += " AND LOWER(product_name) = LOWER(%s)"
        params.append(filters["product_name"])

    if filters["recommended_age"]:
        sql += """
            AND (
                substring(recommended_age FROM '^(\\d+)')::int <= %s AND
                substring(recommended_age FROM '(\\d+)$')::int >= %s
            )
        """
        range_match = re.match(r"(\d+)-(\d+)", filters["recommended_age"])
        if range_match:
            params.extend([range_match.group(1), range_match.group(2)])

    if filters["weight"]:
        sql += """
            AND (
                substring(weight FROM '^(\\d+)')::int <= %s AND
                substring(weight FROM '(\\d+)$')::int >= %s
            )
        """
        range_match = re.match(r"(\d+)-(\d+)", filters["weight"])
        if range_match:
            params.extend([range_match.group(1), range_match.group(2)])

    if filters["allergens"]:
        sql += " AND LOWER(allergens) = LOWER(%s)"
        params.append(filters["allergens"])

    # Exclude products with inventory = 0
    sql += " AND inventory > 0"

    sql += " LIMIT 3"

    try:
        logger.info("Executing SQL: %s with params: %s", sql, params)
        cursor.execute(sql, tuple(params))
        results = cursor.fetchall()
    except Exception as e:
        logger.error("Failed to execute query: %s", e)
        raise HTTPException(status_code=500, detail="Query execution failed") from e
    finally:
        conn.close()

    # Map to JSON-friendly format
    products = [
        {
            "product_name": row[0],
            "brand": row[1],
            "recommended_age": row[2],
            "weight": row[3],
            "price": row[4],
            "inventory": row[5],
            "allergens": row[6]
        }
        for row in results
    ]

    logger.info("Query results: %s", products)
    return products

@app.post("/process_query/")
async def process_query(input_data: QueryInput):
    """
    Process the user query, extract keywords, and query the database.
    """
    logger.info("Processing query: %s", input_data.last_utterance)

    # Step 1: Extract keywords
    keywords = extract_keywords(input_data.last_utterance)

    if not any(keywords.values()):
        logger.warning("No valid filters extracted from the query.")
        raise HTTPException(status_code=400, detail="No valid filters extracted from the query.")

    # Step 2: Query the database
    try:
        products = query_database(keywords)
        if not products:
            logger.info("No matching products found for filters: %s", keywords)
            return {"message": "No matching products found"}

        # Step 3: Return the results
        logger.info("Returning results: %s", products)
        return {"results": products}
    except Exception as e:
        logger.error("Error processing query: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
