# Implement Service Method

Implement a service layer method following the Grins Platform patterns.

## Template Structure

```python
from grins_platform.log_config import LoggerMixin

class {ServiceName}Service(LoggerMixin):
    DOMAIN = "business"
    
    def __init__(self, repository: {Repository}Repository) -> None:
        self.repository = repository
    
    async def {method_name}(self, {params}) -> {ReturnType}:
        """
        {Description}
        
        Args:
            {param}: {description}
        
        Returns:
            {ReturnType}: {description}
        
        Raises:
            {ExceptionType}: {when}
        """
        self.log_started("{method_name}", {log_params})
        
        try:
            # 1. Validate inputs
            if not self._validate_{method_name}({params}):
                self.log_rejected("{method_name}", reason="validation_failed")
                raise ValidationError("Invalid input")
            
            # 2. Business logic
            result = await self.repository.{repo_method}({params})
            
            # 3. Transform to response
            response = {ResponseSchema}.model_validate(result)
            
            self.log_completed("{method_name}", result_id=result.id)
            return response
            
        except {ExpectedException} as e:
            self.log_rejected("{method_name}", reason=str(e))
            raise
        except Exception as e:
            self.log_failed("{method_name}", error=e)
            raise ServiceError(f"Failed to {method_name}: {e}") from e
```

## Checklist

- [ ] LoggerMixin inherited
- [ ] DOMAIN set to "business"
- [ ] log_started at method entry
- [ ] log_completed on success
- [ ] log_rejected for validation failures
- [ ] log_failed for unexpected errors
- [ ] Type hints on all parameters and return
- [ ] Docstring with Args, Returns, Raises
- [ ] Input validation before processing
- [ ] Proper exception handling
