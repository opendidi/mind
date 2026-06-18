/**
 * HTML sanitizer using the browser's DOMParser API.
 * Prevents XSS when rendering markdown/agent output via v-html.
 */
const ALLOWED_TAGS = new Set([
  'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's', 'del', 'ins',
  'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li', 'a', 'blockquote', 'span', 'table', 'thead',
  'tbody', 'tr', 'th', 'td', 'hr', 'img', 'div',
]);

const ALLOWED_ATTRS = new Set([
  'href', 'target', 'rel', 'src', 'alt', 'width', 'height',
  'class', 'id', 'title', 'colspan', 'rowspan',
]);

function sanitizeNode(node: Node): void {
  if (node.nodeType === Node.COMMENT_NODE) {
    node.remove();
    return;
  }
  if (node.nodeType === Node.ELEMENT_NODE) {
    const el = node as HTMLElement;
    const tag = el.tagName.toLowerCase();
    if (!ALLOWED_TAGS.has(tag)) {
      // Replace with its children
      while (el.firstChild) {
        el.parentNode?.insertBefore(el.firstChild, el);
      }
      el.remove();
      return;
    }
    // Strip dangerous attributes
    for (let i = el.attributes.length - 1; i >= 0; i--) {
      const attr = el.attributes[i];
      const name = attr.name.toLowerCase();
      if (!ALLOWED_ATTRS.has(name)) {
        el.removeAttribute(name);
      } else if (name === 'href' && /^\s*javascript:/i.test(attr.value)) {
        el.removeAttribute(name);
      }
    }
    // Add rel for external links
    if (tag === 'a' && el.hasAttribute('href')) {
      el.setAttribute('rel', 'noopener noreferrer');
    }
  }
  // Recurse into children (use a static copy since nodes may be removed)
  let child = node.firstChild;
  while (child) {
    const next = child.nextSibling;
    sanitizeNode(child);
    child = next;
  }
}

export function sanitizeHtml(html: string): string {
  if (!html) return '';
  try {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    sanitizeNode(doc.body);
    return doc.body.innerHTML;
  } catch {
    // Fallback: strip all tags
    return html.replace(/<[^>]*>/g, '');
  }
}
