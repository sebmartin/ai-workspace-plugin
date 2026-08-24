"""Schema 2: the indexes are the record, the README is a view.

This is the schema's whole surface. Imports name only v1, the schema directly
below, never anything older, so retiring v1 later means collapsing what is
still used into this module and nothing above it changes.
"""

# changed in v2
from ai_workspace.threads.v2.thread import create, resume

__all__ = ["create", "resume"]
