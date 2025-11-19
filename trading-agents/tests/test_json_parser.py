"""
Tests for JSON parser utility with robust fallback strategies
"""
import pytest
import json
from utils.json_parser import (
    safe_json_parse,
    extract_json_from_markdown,
    extract_json_from_text,
    clean_json_string,
    parse_llm_json_array,
)


class TestExtractJsonFromMarkdown:
    """Test markdown extraction functionality"""

    def test_extract_from_json_block(self, markdown_wrapped_json):
        """Test extraction from ```json block"""
        result = extract_json_from_markdown(markdown_wrapped_json)
        assert "result" in result
        assert "success" in result

    def test_extract_from_plain_block(self):
        """Test extraction from ``` block without json tag"""
        text = """```
        {"key": "value"}
        ```"""
        result = extract_json_from_markdown(text)
        assert "key" in result

    def test_no_markdown_returns_original(self):
        """Test that non-markdown text is returned as-is"""
        text = '{"plain": "json"}'
        result = extract_json_from_markdown(text)
        assert result == text


class TestExtractJsonFromText:
    """Test JSON extraction from mixed text"""

    def test_extract_json_object(self):
        """Test extraction of JSON object from text"""
        text = 'Here is the data: {"name": "test", "value": 123} and more text'
        result = extract_json_from_text(text)
        parsed = json.loads(result)
        assert parsed["name"] == "test"
        assert parsed["value"] == 123

    def test_extract_json_array(self):
        """Test extraction of JSON array from text"""
        text = 'Results: [{"a": 1}, {"b": 2}] done'
        result = extract_json_from_text(text)
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["a"] == 1

    def test_nested_braces(self):
        """Test extraction with nested objects"""
        text = 'Data: {"outer": {"inner": {"value": 42}}} end'
        result = extract_json_from_text(text)
        parsed = json.loads(result)
        assert parsed["outer"]["inner"]["value"] == 42

    def test_no_json_returns_original(self):
        """Test that text without JSON is returned as-is"""
        text = "No JSON here"
        result = extract_json_from_text(text)
        assert result == text


class TestCleanJsonString:
    """Test JSON cleaning functionality"""

    def test_remove_trailing_comma_object(self):
        """Test removal of trailing comma in object"""
        dirty = '{"key": "value",}'
        clean = clean_json_string(dirty)
        parsed = json.loads(clean)
        assert parsed["key"] == "value"

    def test_remove_trailing_comma_array(self):
        """Test removal of trailing comma in array"""
        dirty = '[1, 2, 3,]'
        clean = clean_json_string(dirty)
        parsed = json.loads(clean)
        assert parsed == [1, 2, 3]

    def test_remove_bom(self):
        """Test removal of BOM character"""
        dirty = '\ufeff{"key": "value"}'
        clean = clean_json_string(dirty)
        assert '\ufeff' not in clean
        parsed = json.loads(clean)
        assert parsed["key"] == "value"

    def test_strip_whitespace(self):
        """Test whitespace stripping"""
        dirty = '  \n  {"key": "value"}  \n  '
        clean = clean_json_string(dirty)
        parsed = json.loads(clean)
        assert parsed["key"] == "value"


class TestSafeJsonParse:
    """Test the main safe_json_parse function"""

    def test_parse_valid_json(self, valid_json_response):
        """Test parsing of valid JSON"""
        result = safe_json_parse(valid_json_response)
        assert result["portfolio_health_score"] == 75
        assert result["concentration_risk"] == "MODERATE"

    def test_parse_markdown_wrapped(self, markdown_wrapped_json):
        """Test parsing JSON wrapped in markdown"""
        result = safe_json_parse(markdown_wrapped_json)
        assert result["result"] == "success"
        assert result["data"]["value"] == 42

    def test_parse_with_trailing_comma(self):
        """Test parsing JSON with trailing comma"""
        malformed = '{"key": "value", "num": 123,}'
        result = safe_json_parse(malformed)
        assert result["key"] == "value"
        assert result["num"] == 123

    def test_parse_mixed_text(self):
        """Test parsing JSON from mixed text"""
        text = 'Analysis complete. Result: {"score": 85, "status": "good"} End.'
        result = safe_json_parse(text)
        assert result["score"] == 85
        assert result["status"] == "good"

    def test_empty_response_with_default(self):
        """Test empty response returns default"""
        default = {"error": "no data"}
        result = safe_json_parse("", default=default)
        assert result == default

    def test_empty_response_raises_without_default(self):
        """Test empty response raises ValueError without default"""
        with pytest.raises(ValueError, match="Empty LLM response"):
            safe_json_parse("")

    def test_unparseable_with_default(self):
        """Test unparseable content returns default"""
        default = {"error": "parse failed"}
        result = safe_json_parse("This is not JSON at all!", default=default)
        assert result == default

    def test_unparseable_raises_without_default(self):
        """Test unparseable content raises ValueError without default"""
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            safe_json_parse("Not JSON")


class TestParseLlmJsonArray:
    """Test array parsing functionality"""

    def test_parse_simple_array(self):
        """Test parsing simple JSON array"""
        response = '[{"id": 1}, {"id": 2}]'
        result = parse_llm_json_array(response)
        assert len(result) == 2
        assert result[0]["id"] == 1

    def test_parse_wrapped_array(self):
        """Test parsing array wrapped in object"""
        response = '{"items": [{"id": 1}, {"id": 2}]}'
        result = parse_llm_json_array(response)
        assert len(result) == 2
        assert result[0]["id"] == 1

    def test_parse_recommendations_key(self):
        """Test parsing with 'recommendations' key"""
        response = '{"recommendations": [{"ticker": "AAPL"}]}'
        result = parse_llm_json_array(response)
        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"

    def test_non_array_returns_empty(self):
        """Test non-array returns empty list"""
        response = '{"key": "value"}'
        result = parse_llm_json_array(response)
        assert result == []

    def test_empty_returns_default(self):
        """Test empty response returns empty list"""
        result = parse_llm_json_array("")
        assert result == []


class TestRobustness:
    """Test robustness of parser with edge cases"""

    def test_multiple_json_objects(self):
        """Test extraction of first JSON object when multiple exist"""
        text = '{"first": 1} some text {"second": 2}'
        result = safe_json_parse(text)
        assert result["first"] == 1

    def test_unicode_handling(self):
        """Test proper Unicode handling"""
        text = '{"message": "Hello 世界 🌍"}'
        result = safe_json_parse(text)
        assert "世界" in result["message"]
        assert "🌍" in result["message"]

    def test_deeply_nested_object(self):
        """Test parsing deeply nested JSON"""
        text = '{"a": {"b": {"c": {"d": {"e": "deep"}}}}}'
        result = safe_json_parse(text)
        assert result["a"]["b"]["c"]["d"]["e"] == "deep"

    def test_large_numbers(self):
        """Test handling of large numbers"""
        text = '{"big_int": 9007199254740991, "big_float": 1.7976931348623157e+308}'
        result = safe_json_parse(text)
        assert result["big_int"] == 9007199254740991

    def test_special_characters_in_strings(self):
        """Test special characters in string values"""
        text = '{"text": "Line 1\\nLine 2\\tTabbed"}'
        result = safe_json_parse(text)
        assert "\\n" in result["text"] or "\n" in result["text"]
