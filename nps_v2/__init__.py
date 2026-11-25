"""NPS Operations Center V2 — Claude-native engine.

Deterministic, read-only building blocks used by the Claude skill. The package never
calls Salesforce, Slack or any other system itself: Claude runs the queries this
package generates and hands back the raw connector JSON. See
documentation/V2_CLAUDE_NATIVE_ARCHITECTURE.md.
"""

__version__ = "0.1.0"
