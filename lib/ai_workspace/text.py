"""Reading a markdown file's YAML frontmatter. Independent of any schema."""

import io
from pathlib import Path

import frontmatter
import yaml
from frontmatter.default_handlers import YAMLHandler
from ruamel.yaml import YAML

# PyYAML alphabetises keys and drops quoting on dump, so a file written back
# through it comes out reordered. ruamel keeps both.
_ROUND_TRIP = YAML()
_ROUND_TRIP.preserve_quotes = True


class _Handler(YAMLHandler):
    """`frontmatter`'s own handler, dumping through ruamel."""

    def load(self, fm, **kwargs):
        return _ROUND_TRIP.load(fm)

    def export(self, metadata, **kwargs):
        out = io.StringIO()
        _ROUND_TRIP.dump(metadata, out)
        return out.getvalue().rstrip("\n")


def set_frontmatter_field(path: Path, key: str, value: str) -> bool:
    """Set one frontmatter field in place. False if the file has no such field.

    The body is untouched because nothing here reads it: `frontmatter` splits
    it off and hands it back unexamined, so a line in the body that looks like
    the field cannot be hit. Raises ValueError on frontmatter that does not
    parse, as `split_frontmatter` does.
    """
    try:
        post = frontmatter.loads(path.read_text(), handler=_Handler())
    except yaml.YAMLError as e:
        raise ValueError(f"Frontmatter in {path} is not valid YAML. {e}") from e
    if not isinstance(post.metadata, dict) or key not in post.metadata:
        return False
    post[key] = value
    path.write_text(frontmatter.dumps(post, handler=_Handler()) + "\n")
    return True


def split_frontmatter(text: str, source: Path | str | None = None) -> tuple[dict, str]:
    """The frontmatter mapping and the body that follows it.

    Frontmatter that does not parse raises. Returning no fields would be worse
    than failing: the fields are what a thread is indexed and resumed by, so a
    decision would come back without its summary or its state, and nothing
    would say why. An error names the file, and whoever reads it can open that
    file and fix it.

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


def yaml_value(text: str) -> str:
    """A scalar safe to interpolate into a frontmatter line.

    Always quoted, rather than quoted only when it has to be. The rules for
    when a bare YAML scalar is safe are long enough that getting them wrong is
    likelier than anyone minding the quotes, and getting them wrong writes a
    file the reader then refuses.
    """
    escaped = str(text).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
