"""Scheduling prompts for AI assistant.

Validates: AI Assistant Requirements 4.1
"""

SCHEDULE_GENERATION_PROMPT = """Generate an optimized schedule for the given date.

SCHEDULING RULES:
1. Batch jobs by geographic location (same city/area together)
2. Batch jobs by type (seasonal services together, repairs together)
3. Assign appropriate staff based on job requirements:
   - Small appointments: 1 person (Dad, Vas)
   - Major jobs/installations: 2+ people (Vas, Steven, Vitallik)
4. Respect time windows (2-hour windows preferred)
5. Account for travel time between locations (15 min buffer)
6. Consider equipment requirements (compressor for winterizations, etc.)

OUTPUT FORMAT:
Return a schedule with:
- Time slots for each job
- Staff assignments
- Route order optimized for minimal travel
- Any conflicts or warnings

Always present the schedule for Viktor's review before sending confirmations.
"""

SCHEDULE_REVIEW_PROMPT = """Review the proposed schedule and identify any issues:
- Overlapping appointments
- Unrealistic travel times
- Missing equipment requirements
- Staff availability conflicts
- Customer preferences not met
"""
