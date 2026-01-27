"""Estimate prompts for AI assistant.

Validates: AI Assistant Requirements 9.1
"""

ESTIMATE_PROMPT = """Generate an estimate for the requested irrigation work.

PRICING GUIDELINES:
- Spring startup: $15/zone (base) + $30 service call
- Summer tune-up: $15/zone (base) + $30 service call
- Fall winterization: $20/zone (base) + $30 service call
- Head replacement: $50/head (parts + labor)
- Diagnostic fee: $100 (first hour)
- Hourly rate: $85/hour (after first hour)
- New installation: $700/zone (for builder partners)

LABOR ESTIMATES:
- Startup/Winterization: 30 min base + 5 min/zone
- Simple repair: 30 min
- Complex repair: 1-2 hours
- Installation: 4-8 hours per zone

ESTIMATE COMPONENTS:
1. Labor costs
2. Materials/parts
3. Equipment rental (if needed)
4. Travel/service call fee
5. Contingency (10% for unknowns)

OUTPUT FORMAT:
- line_items: Itemized list of costs
- subtotal: Sum before tax
- tax: Applicable tax (if any)
- total: Final estimate
- valid_until: Estimate expiration date (30 days)
- notes: Any assumptions or conditions
- confidence: How confident in this estimate (0-100%)

Always flag estimates over $1000 for Viktor's review.
"""

ESTIMATE_REVIEW_PROMPT = """Review the generated estimate:
- Are all necessary items included?
- Is the pricing accurate for this customer?
- Are there any special circumstances?
- Should any discounts apply?
"""
