# Implement Property-Based Test

Implement a property-based test following the Grins Platform patterns.

## Template Structure

```python
import pytest
from hypothesis import given, strategies as st, settings

class TestPropertyBased:
    """Property-based tests for {Component}."""
    
    @given(st.{strategy}())
    @settings(max_examples=100)
    def test_{property_name}_property(self, value: {Type}) -> None:
        """
        Property: {Description of the property being tested}
        
        **Validates: Requirement {X.Y}**
        """
        # Arrange
        {setup}
        
        # Act
        result = {operation}
        
        # Assert - the property that must always hold
        assert {property_assertion}, f"Property violated: {description}"
```

## Common Properties

### Idempotence
```python
@given(st.text())
def test_normalize_idempotent(self, value: str) -> None:
    """normalize(normalize(x)) == normalize(x)"""
    result1 = normalize(value)
    result2 = normalize(result1)
    assert result1 == result2
```

### Uniqueness
```python
@given(st.lists(st.text(), min_size=2, unique=True))
def test_no_duplicates(self, values: list[str]) -> None:
    """No two items share the same key"""
    keys = [get_key(v) for v in values]
    assert len(keys) == len(set(keys))
```

### Bounds
```python
@given(st.integers(min_value=1, max_value=100))
def test_value_in_bounds(self, value: int) -> None:
    """All values within valid range are accepted"""
    result = validate(value)
    assert result.is_valid
```

### Round-Trip
```python
@given(st.builds(MyModel))
def test_serialization_roundtrip(self, obj: MyModel) -> None:
    """serialize(deserialize(x)) == x"""
    serialized = obj.model_dump_json()
    deserialized = MyModel.model_validate_json(serialized)
    assert obj == deserialized
```

## Strategies Reference

| Type | Strategy |
|------|----------|
| Integers | `st.integers(min_value=0, max_value=100)` |
| Text | `st.text(min_size=1, max_size=50)` |
| Email | `st.emails()` |
| Phone | `st.from_regex(r'\d{10}')` |
| Lists | `st.lists(st.integers(), min_size=1)` |
| Optional | `st.none() \| st.text()` |
| Enum | `st.sampled_from(MyEnum)` |

## Checklist

- [ ] @given decorator with appropriate strategy
- [ ] @settings with max_examples
- [ ] Validates comment linking to requirement
- [ ] Clear property description in docstring
- [ ] Meaningful assertion message
