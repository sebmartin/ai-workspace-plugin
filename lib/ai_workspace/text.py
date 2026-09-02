"""Reading a markdown file's YAML frontmatter. Independent of any schema."""

import frontmatter
import yaml


def split_frontmatter(text: str) -> tuple[dict, str]:
    """The frontmatter mapping and the body that follows it.

    Hand-edited frontmatter is normal in a workspace, so a block that will not
    parse degrades to "no fields" rather than failing whatever operation
    happened to read the file. A block that parses to something other than a
    mapping, such as a bare list, is treated the same way.
    """
    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError:
        return {}, text
    fields = post.metadata if isinstance(post.metadata, dict) else {}
    return fields, post.content
