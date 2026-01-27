"""Categorization prompts for AI assistant.

Validates: AI Assistant Requirements 5.1
"""

CATEGORIZATION_PROMPT = """Categorize the incoming job request.

CATEGORIES:
1. **ready_to_schedule** - Standard services with known pricing:
   - Spring startups
   - Summer tune-ups
   - Fall winterizations
   - Simple repairs (broken heads, minor leaks)

2. **requires_estimate** - Complex work needing site assessment:
   - New installations
   - Major repairs (pipe replacement, valve issues)
   - System redesigns
   - Landscaping projects
   - Unknown scope of work

3. **urgent** - Emergency situations:
   - Active flooding/leaks
   - System failures during extreme weather
   - Safety hazards

CONFIDENCE SCORING:
- Provide a confidence score (0-100%)
- If confidence >= 85%, auto-categorize
- If confidence < 85%, flag for human review

OUTPUT:
- category: The assigned category
- confidence: Confidence score (0-100)
- reasoning: Brief explanation of the categorization
- suggested_services: List of likely services needed
- estimated_duration: Rough time estimate if known
"""

CATEGORIZATION_REVIEW_PROMPT = """Review the AI categorization and verify:
- Is the category appropriate for this job type?
- Are there any special circumstances not captured?
- Should this be escalated to Viktor for review?
"""
