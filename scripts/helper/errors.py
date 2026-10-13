class ScriptError(RuntimeError):
    """Base error for Vulniverse maintenance scripts."""

class UpdateError(ScriptError):
    """Updating upstream schemas failed."""

class GenerationError(ScriptError):
    """Generating editor schemas failed."""
