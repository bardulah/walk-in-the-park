"""
Robust JSON parsing utilities with multiple fallback strategies
"""
import json
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


def extract_json_from_markdown(text: str) -> str:
    """Extract JSON from markdown code blocks"""
    # Try to find JSON in ```json...``` or ```...``` blocks
    patterns = [
        r'```json\s*\n(.*?)\n```',
        r'```\s*\n(.*?)\n```',
        r'```json\s*(.*?)```',
        r'```\s*(.*?)```',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

    return text


def extract_json_from_text(text: str) -> str:
    """Extract JSON object or array from text"""
    # Try to find the first { or [ and match to closing } or ]

    # Find JSON object
    obj_start = text.find('{')
    if obj_start != -1:
        brace_count = 0
        for i in range(obj_start, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[obj_start:i+1]

    # Find JSON array
    arr_start = text.find('[')
    if arr_start != -1:
        bracket_count = 0
        for i in range(arr_start, len(text)):
            if text[i] == '[':
                bracket_count += 1
            elif text[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    return text[arr_start:i+1]

    return text


def clean_json_string(text: str) -> str:
    """Clean common JSON formatting issues"""
    # Remove BOM and other invisible characters
    text = text.strip().lstrip('\ufeff')

    # Fix common issues like trailing commas (basic cleanup)
    # Note: This is not comprehensive, just handles obvious cases
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    return text


def safe_json_parse(
    llm_response: str,
    schema: Optional[Type[T]] = None,
    default: Optional[Dict[str, Any]] = None
) -> Dict[str, Any] | T:
    """
    Parse JSON from LLM response with multiple fallback strategies

    Args:
        llm_response: The raw response from LLM
        schema: Optional Pydantic model to validate against
        default: Default value to return if all parsing fails

    Returns:
        Parsed JSON as dict or validated Pydantic model

    Raises:
        ValueError: If parsing fails and no default provided
    """
    if not llm_response or not llm_response.strip():
        if default is not None:
            return default
        raise ValueError("Empty LLM response")

    parsing_errors = []

    # Strategy 1: Direct JSON parse
    try:
        data = json.loads(llm_response)
        logger.debug("Parsed JSON directly")
        return _validate_with_schema(data, schema) if schema else data
    except json.JSONDecodeError as e:
        parsing_errors.append(f"Direct parse failed: {e}")

    # Strategy 2: Extract from markdown code blocks
    try:
        extracted = extract_json_from_markdown(llm_response)
        data = json.loads(extracted)
        logger.debug("Parsed JSON from markdown code block")
        return _validate_with_schema(data, schema) if schema else data
    except json.JSONDecodeError as e:
        parsing_errors.append(f"Markdown extraction failed: {e}")

    # Strategy 3: Extract JSON object/array from text
    try:
        extracted = extract_json_from_text(llm_response)
        data = json.loads(extracted)
        logger.debug("Parsed JSON by extracting from text")
        return _validate_with_schema(data, schema) if schema else data
    except json.JSONDecodeError as e:
        parsing_errors.append(f"Text extraction failed: {e}")

    # Strategy 4: Clean and retry
    try:
        cleaned = clean_json_string(llm_response)
        data = json.loads(cleaned)
        logger.debug("Parsed JSON after cleaning")
        return _validate_with_schema(data, schema) if schema else data
    except json.JSONDecodeError as e:
        parsing_errors.append(f"Cleaned parse failed: {e}")

    # Strategy 5: Clean extracted JSON
    try:
        extracted = extract_json_from_text(llm_response)
        cleaned = clean_json_string(extracted)
        data = json.loads(cleaned)
        logger.debug("Parsed JSON after extraction and cleaning")
        return _validate_with_schema(data, schema) if schema else data
    except json.JSONDecodeError as e:
        parsing_errors.append(f"Extract+clean failed: {e}")

    # All strategies failed
    if default is not None:
        logger.warning(f"All JSON parsing strategies failed, using default. Errors: {parsing_errors}")
        return default

    error_msg = f"Failed to parse JSON from LLM response. Tried 5 strategies:\n" + "\n".join(parsing_errors)
    error_msg += f"\n\nResponse preview: {llm_response[:500]}"
    raise ValueError(error_msg)


def _validate_with_schema(data: Dict[str, Any], schema: Type[T]) -> T:
    """Validate data against Pydantic schema"""
    try:
        return schema(**data)
    except ValidationError as e:
        logger.error(f"Schema validation failed: {e}")
        raise ValueError(f"JSON validation failed: {e}")


def parse_llm_json_array(llm_response: str, item_schema: Optional[Type[T]] = None) -> list:
    """
    Parse JSON array from LLM response

    Args:
        llm_response: The raw response from LLM
        item_schema: Optional Pydantic model for array items

    Returns:
        List of parsed items (dicts or validated models)
    """
    data = safe_json_parse(llm_response, default=[])

    if not isinstance(data, list):
        # Sometimes LLM wraps array in an object
        if isinstance(data, dict):
            # Try to find array in common wrapper keys
            for key in ['items', 'results', 'data', 'recommendations', 'trades']:
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                # No array found, return empty
                logger.warning(f"Expected array but got dict with keys: {data.keys()}")
                return []
        else:
            logger.warning(f"Expected array but got {type(data)}")
            return []

    if item_schema:
        validated_items = []
        for i, item in enumerate(data):
            try:
                validated_items.append(_validate_with_schema(item, item_schema))
            except ValueError as e:
                logger.warning(f"Item {i} validation failed: {e}")
                continue
        return validated_items

    return data
