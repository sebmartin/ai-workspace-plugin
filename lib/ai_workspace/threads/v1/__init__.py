"""Schema 1: the README is the thread.

This is the schema's whole surface. Every operation a thread-scoped tool can
reach is named here, and dispatch resolves against this module rather than
against the files below it. A later schema imports what it keeps from here and
defines only what it changes.
"""

from ai_workspace.threads.v1.thread import create, resume

__all__ = ["create", "resume"]
