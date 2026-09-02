"""Reading a markdown file's YAML frontmatter. Independent of any schema."""

from pathlib import Path

import frontmatter
import yaml


def split_frontmatter(text: str, source: Path | str | None = None) -> tuple[dict, str]:
    """The frontmatter mapping and the body that follows it.

    Frontmatter that does not parse raises. Returning no fields would be worse
    than failing: the fields are what a thread is indexed and resumed by, so a
    decision would come back without its summary, or an index without its
    windows, and nothing would say why. An error names the file, and whoever
    reads it can open that file and fix it.

    `source` is only for the message. Pass the path when there is one, since a
    YAML error reports a line and column against an anonymous string.
    """
    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError as e:
        where = f" in {source}" if source else ""
        raise ValueError(f"Frontmatter{where} is not valid YAML. {e}") from e
    fields = post.metadata if isinstance(post.metadata, dict) else {}
    return fields, post.content
