# -*- coding: UTF-8 -*-
"""Shared utilities for canvas tool package."""
import uuid


def new_pen_id() -> str:
    """Generate a unique pen ID using UUID4 (12 hex chars)."""
    return uuid.uuid4().hex[:12]


def resolve_pen_ids(args: dict) -> list:
    """Extract pen_ids from args, supporting single pen_id or list of pen_ids."""
    pen_ids = args.get("pen_ids", [])
    if not pen_ids and args.get("pen_id"):
        pen_ids = [args.get("pen_id")]
    return pen_ids


def get_shadow(args: dict):
    """Get CanvasShadow from tool args if available."""
    return args.get("_canvas_shadow")
