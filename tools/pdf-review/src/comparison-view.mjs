import { compareSnapshots } from './compare.mjs';
import { displayDestination } from './review.mjs';
import { formatFileSize } from './upload-limits.mjs';

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/** Keep one reference extraction in memory while the main viewer opens revisions. */
export function createComparisonView(panel, onForget = () => {}) {
  const keep = panel.querySelector('#keep-before');
  const clear = panel.querySelector('#clear-before');
  const status = panel.querySelector('#comparison-status');
  const files = panel.querySelector('#comparison-files');
  const results = panel.querySelector('#comparison-results');
  let before;
  let current;

  function fileSummary(label, snapshot) {
    const card = element('div');
    card.append(element('h3', '', label), element('p', 'comparison-filename', displayDestination(snapshot.filename)));
    const pages = snapshot.pageCount === null ? 'Page count unavailable'
      : `${snapshot.pageCount} ${snapshot.pageCount === 1 ? 'page' : 'pages'}`;
    const size = snapshot.bytes === null ? 'File size unavailable' : formatFileSize(snapshot.bytes);
    card.append(element('p', 'field-hint', `${pages} · ${size}`));
    return card;
  }

  function render() {
    panel.hidden = !before && !current;
    keep.disabled = !current || current === before;
    clear.hidden = !before;
    keep.textContent = before ? 'Use current PDF as before' : 'Keep this PDF as before';
    files.replaceChildren();
    results.replaceChildren();
    if (!before) {
      status.textContent = 'Keep this export as the before copy, then open a revised PDF above.';
      return;
    }
    files.append(fileSummary('Before', before));
    if (!current || current === before) {
      status.textContent = 'Before copy kept in this tab. Open the revised PDF above to compare.';
      return;
    }
    files.append(fileSummary('After', current));
    status.textContent = 'Comparing original PDF text and link destinations. Application-form edits are excluded.';
    const comparison = compareSnapshots(before, current);
    const text = element('section', 'comparison-section');
    text.append(element('h3', '', 'Text changes'));
    if (comparison.text.status === 'same') {
      text.append(element('p', '', 'No differences in extracted text.'));
    } else if (comparison.text.status === 'changed') {
      const legend = element('p', 'field-hint comparison-legend');
      legend.append(element('del', '', 'Removed from before'), document.createTextNode(' · '), element('ins', '', 'Added in after'));
      const difference = element('p', 'comparison-text');
      difference.tabIndex = 0;
      difference.setAttribute('role', 'region');
      difference.setAttribute('aria-label', 'Text differences');
      for (const change of comparison.text.changes) {
        if (difference.childNodes.length) difference.append(document.createTextNode(' '));
        const tag = change.type === 'removed' ? 'del' : change.type === 'added' ? 'ins' : 'span';
        if (change.type !== 'equal') difference.append(element('span', 'visually-hidden', `${change.type === 'added' ? 'Added' : 'Removed'}: `));
        difference.append(element(tag, '', displayDestination(change.text)));
      }
      text.append(legend, difference);
    } else {
      text.append(element('p', 'notice notice--warning', `Text comparison is incomplete. ${comparison.text.reason}`));
    }
    const links = element('section', 'comparison-section');
    links.append(element('h3', '', 'Link changes'));
    if (comparison.links.status === 'same') {
      links.append(element('p', '', 'No differences in external link destinations or their counts.'));
    } else {
      if (comparison.links.status === 'incomplete') {
        links.append(element('p', 'notice notice--warning', `Link comparison is incomplete. ${comparison.links.reason} Any changes below cover only inspected destinations.`));
      }
      const list = element('ul', 'comparison-links');
      for (const [label, changes] of [['Removed', comparison.links.removed], ['Added', comparison.links.added]]) {
        for (const link of changes) {
          const item = element('li');
          item.append(element('span', 'link-type', `${label} · ${link.count} ${link.count === 1 ? 'occurrence' : 'occurrences'}`),
            element('code', 'link-destination', displayDestination(link.destination)));
          if (link.resolvedDestination !== null && link.resolvedDestination !== link.destination) {
            item.append(element('span', 'field-hint', 'PDF reader resolves this to:'),
              element('code', 'link-destination', displayDestination(link.resolvedDestination) || '(empty destination)'));
          }
          list.append(item);
        }
      }
      links.append(list);
    }
    results.append(text, links);
  }

  keep.addEventListener('click', () => {
    if (!current) return;
    before = current;
    render();
  });
  clear.addEventListener('click', () => {
    before = null;
    render();
    onForget();
    if (panel.hidden || keep.disabled) document.getElementById('pdf-file').focus();
    else keep.focus();
  });
  return {
    setCurrent(snapshot) {
      current = snapshot;
      render();
    },
    clear({ keepBefore = false } = {}) {
      current = null;
      if (!keepBefore) {
        before = null;
        panel.open = false;
      }
      render();
    },
  };
}
