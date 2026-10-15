'use strict';
const $ = id => document.getElementById(id);
let current = null, dirty = false, saving = false, listRequest = 0, detailRequest = 0;
let visibleIds = [];
const date = value => new Intl.DateTimeFormat('nl-NL', {day:'2-digit', month:'short', year:'numeric', timeZone:'UTC'}).format(new Date(value));
async function api(path, options = {}) {
  const response = await fetch(path, {...options, signal: AbortSignal.timeout(7000)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Het verzoek is mislukt.');
  return data;
}
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function markSelection() {
  for (const button of document.querySelectorAll('.message')) {
    const selected = Number(button.dataset.id) === current?.id;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  }
}
function renderStats(counts, visible) {
  $('stats').replaceChildren();
  for (const [label, value] of [['Totaal', counts.total], ['Info', counts.categories.info || 0],
                               ['Verkoop', counts.categories.verkoop || 0], ['Support', counts.categories.support || 0],
                               ['Zichtbaar', visible]]) {
    const item = node('div', undefined, 'stat');
    item.append(node('span', label), node('strong', String(value)));
    $('stats').append(item);
  }
}
function showEmpty(title, description) {
  ++detailRequest;
  current = null; dirty = false;
  $('detail').hidden = true; $('empty').hidden = false;
  $('empty-title').textContent = title; $('empty-description').textContent = description;
  $('draft').value = ''; $('save').disabled = true;
  markSelection();
}
async function loadList() {
  const request = ++listRequest;
  ++detailRequest; // A previous detail response must not cross a filter change.
  $('draft').disabled = false; $('save').disabled = saving || !current;
  $('list-status').textContent = 'Berichten laden…';
  const filters = {q:$('search').value, category:$('category').value, folder:$('folder').value};
  try {
    const result = await api('/api/messages?' + new URLSearchParams(filters));
    if (request !== listRequest) return;
    visibleIds = result.items.map(mail => mail.id);
    $('messages').replaceChildren();
    $('result-count').textContent = result.items.length + (result.items.length === 1 ? ' bericht' : ' berichten');
    renderStats(result.counts, result.items.length);
    document.querySelector('.pane-heading h2').textContent = filters.folder === 'inbox' ? 'Inbox' : filters.folder === 'sent' ? 'Uitgaande voorbeelden' : 'Alle berichten';
    for (const mail of result.items) {
      const button = node('button', undefined, 'message'); button.type = 'button'; button.dataset.id = mail.id;
      const meta = node('div', undefined, 'row-meta'); meta.append(node('span', mail.category, 'tag'), node('span', date(mail.received_at), 'muted'));
      button.append(meta, node('strong', mail.subject), node('p', mail.sender), node('p', mail.preview));
      button.addEventListener('click', () => openMail(mail.id));
      $('messages').append(button);
    }
    markSelection();
    const selectedVisible = current && visibleIds.includes(current.id);
    if (selectedVisible) {
      $('list-status').textContent = 'Bericht geselecteerd · kies een ander bericht om verder te lezen.';
    } else if (dirty || saving) {
      $('list-status').textContent = result.items.length
        ? 'Uw open concept valt buiten dit filter. Sla het op of kies bewust een ander bericht.'
        : 'Geen berichten gevonden. Uw niet-opgeslagen concept blijft open totdat u het opslaat of verlaat.';
    } else if (result.items.length) {
      $('list-status').textContent = 'Eerste bericht openen…';
      await openMail(result.items[0].id, {automatic:true, listVersion:request});
    } else {
      $('list-status').textContent = 'Geen berichten gevonden. Pas uw zoekopdracht of filters aan.';
      showEmpty('Geen berichten gevonden', 'Pas de zoektekst, afdeling of berichtsoort aan om weer berichten te zien.');
    }
  } catch (error) {
    if (request !== listRequest) return;
    visibleIds = []; $('messages').replaceChildren(); $('result-count').textContent = '';
    $('list-status').textContent = error.name === 'TimeoutError' ? 'De lokale demo reageert niet op tijd.' : error.message;
    if (!dirty && !saving) showEmpty('Berichten niet beschikbaar', 'Probeer opnieuw met de knop Filters wissen. Uw opgeslagen concepten blijven bewaard.');
  }
}
async function openMail(id, {automatic = false, listVersion = listRequest} = {}) {
  if (listVersion !== listRequest || saving) return false;
  if (current?.id === id) return true;
  if (dirty && (automatic || !window.confirm('Uw concept bevat niet-opgeslagen wijzigingen. Wilt u die verlaten?'))) return false;
  const request = ++detailRequest;
  $('draft').disabled = true; $('save').disabled = true;
  try {
    const mail = await api('/api/messages/' + id);
    if (request !== detailRequest || listVersion !== listRequest) return false;
    current = mail; dirty = false;
    $('empty').hidden = true; $('detail').hidden = false;
    $('detail-category').textContent = mail.category + ' · ' + (mail.folder === 'inbox' ? 'inkomend' : 'uitgaand voorbeeld');
    $('detail-date').textContent = date(mail.received_at);
    $('subject').textContent = mail.subject; $('sender').textContent = 'Van: ' + mail.sender;
    $('recipient').textContent = 'Aan: ' + mail.recipient;
    $('body').textContent = mail.body; $('summary').textContent = mail.summary; $('draft').value = mail.draft;
    $('edited').textContent = mail.edited ? 'Door medewerker bewerkt' : 'Voorbeeldconcept';
    $('save-status').textContent = ''; $('save').disabled = false;
    $('list-status').textContent = 'Bericht geselecteerd · kies een ander bericht om verder te lezen.';
    markSelection();
    return true;
  } catch (error) {
    if (request === detailRequest && listVersion === listRequest) {
      $('list-status').textContent = error.message;
      if (!current) showEmpty('Bericht niet beschikbaar', 'Kies een ander bericht of probeer opnieuw.');
    }
    return false;
  } finally {
    if (request === detailRequest) { $('draft').disabled = false; $('save').disabled = saving || !current; }
  }
}
$('draft').addEventListener('input', () => { dirty = true; $('save-status').textContent = 'Niet-opgeslagen wijzigingen'; });
async function saveDraft() {
  if (!current || saving) return;
  const id = current.id, text = $('draft').value, version = current.draft_version;
  saving = true;
  $('save').disabled = true; $('save-status').textContent = 'Concept opslaan…';
  let saved = false;
  try {
    const result = await api('/api/messages/' + id + '/draft', {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text, version})});
    if (current?.id !== id) return;
    current = result; dirty = $('draft').value !== text; saved = true;
    $('edited').textContent = 'Door medewerker bewerkt';
    $('save-status').textContent = dirty ? 'Vorige versie opgeslagen; er zijn nieuwere lokale wijzigingen.' : 'Concept lokaal opgeslagen. Er is niets verzonden.';
  } catch (error) {
    if (current?.id === id) $('save-status').textContent = error.message;
  } finally {
    saving = false; $('save').disabled = !current;
  }
  if (saved && !dirty && !visibleIds.includes(id)) await loadList();
}
$('save').addEventListener('click', saveDraft);
let timer;
$('search').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(loadList, 180); });
$('category').addEventListener('change', loadList);
$('folder').addEventListener('change', loadList);
$('clear-filters').addEventListener('click', () => {
  clearTimeout(timer); $('search').value = ''; $('category').value = ''; $('folder').value = 'inbox'; loadList();
});
$('to-list').addEventListener('click', () => { $('messages').scrollIntoView({behavior:'smooth', block:'start'}); document.querySelector('.message')?.focus(); });
window.addEventListener('beforeunload', event => { if (dirty) {event.preventDefault(); event.returnValue = ''; } });
loadList();
