const API = '';
const $ = (id) => document.getElementById(id);
let currentUser = null;
let activeView = 'assistant';
let pollingTimer = null;

$('role').addEventListener('change', () => {
  const isEmployee = $('role').value === 'employee';
  $('employeeFields').classList.toggle('hidden', !isEmployee);
  $('itFields').classList.toggle('hidden', isEmployee);
  $('personName').required = isEmployee;
  $('personEmail').required = isEmployee;
  $('itName').required = !isEmployee;
});

$('loginForm').addEventListener('submit', (event) => {
  event.preventDefault();
  const role = $('role').value;
  currentUser = role === 'employee'
    ? { role, name: $('personName').value.trim(), email: $('personEmail').value.trim().toLowerCase() }
    : { role, name: $('itName').value.trim() };
  $('loginScreen').classList.add('hidden');
  $('appScreen').classList.remove('hidden');
  $('userNameLabel').textContent = currentUser.name;
  $('userRoleLabel').textContent = role === 'employee' ? 'Employee account' : 'Technical team';
  $('avatar').textContent = currentUser.name.charAt(0).toUpperCase();
  $('topAvatar').textContent = currentUser.name.charAt(0).toUpperCase();
  $('employeeNav').classList.toggle('hidden', role !== 'employee');
  $('itNav').classList.toggle('hidden', role !== 'it');
  showView(role === 'employee' ? 'assistant' : 'itTickets');
  loadTickets();
  clearInterval(pollingTimer);
  // pollingTimer = setInterval(loadTickets, 5000);
});

$('logoutBtn').addEventListener('click', () => {
  clearInterval(pollingTimer);
  currentUser = null;
  $('appScreen').classList.add('hidden');
  $('loginScreen').classList.remove('hidden');
});

document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => showView(btn.dataset.view)));
function showView(view) {
  activeView = view;
  ['assistantView', 'myTicketsView', 'itTicketsView'].forEach(id => $(id).classList.add('hidden'));
  const map = { assistant: ['assistantView', 'AI Assistant', 'EMPLOYEE WORKSPACE'], myTickets: ['myTicketsView', 'My Tickets', 'EMPLOYEE WORKSPACE'], itTickets: ['itTicketsView', 'Ticket Queue', 'IT SUPPORT WORKSPACE'] };
  const selected = map[view];
  $(selected[0]).classList.remove('hidden');
  $('pageTitle').textContent = selected[1];
  $('pageEyebrow').textContent = selected[2];
  document.querySelectorAll('.nav-item').forEach(btn => btn.classList.toggle('active', btn.dataset.view === view));
  if (view !== 'assistant') loadTickets();
}

function addChatMessage(text, role) {
  const wrap = document.createElement('div');
  wrap.className = `message ${role === 'user' ? 'user-message' : 'bot-message'}`;
  if (role === 'bot') {
    const icon = document.createElement('div'); icon.className = 'message-avatar'; icon.textContent = '✦'; wrap.appendChild(icon);
  }
  const body = document.createElement('div');
  const label = document.createElement('strong'); label.textContent = role === 'user' ? 'You' : 'Service Desk Agent';
  const p = document.createElement('p'); p.textContent = text;
  body.append(label, p); wrap.appendChild(body); $('chatBox').appendChild(wrap); $('chatBox').scrollTop = $('chatBox').scrollHeight;
}

async function sendMessage() {
  const input = $('userInput'); const message = input.value.trim();
  if (!message || !currentUser || currentUser.role !== 'employee') return;
  addChatMessage(message, 'user'); input.value = ''; $('sendBtn').disabled = true; $('sendBtn').textContent = 'Thinking...';
  try {
    const res = await fetch(`${API}/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Assistant request failed');
    addChatMessage(data.response || 'I could not generate a response. You can raise a ticket for the IT team.', 'bot');
  } catch (err) { addChatMessage(`I couldn't reach the assistant (${err.message}). You can still raise a ticket for IT support.`, 'bot'); }
  finally { $('sendBtn').disabled = false; $('sendBtn').textContent = 'Send ↑'; }
}
$('sendBtn').addEventListener('click', sendMessage);
$('userInput').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });

function openTicketModal() {
  $('ticketTitle').value = '';
  const userMessages = [...$('chatBox').querySelectorAll('.user-message p')].map(p => p.textContent);
  $('ticketDescription').value = userMessages.length ? `Issue details:\n${userMessages[userMessages.length - 1]}\n\nWhat I have tried: ` : '';
  $('ticketModal').classList.remove('hidden');
}
$('raiseTicketBtn').addEventListener('click', openTicketModal);
$('newTicketBtn').addEventListener('click', openTicketModal);
$('closeModal').addEventListener('click', () => $('ticketModal').classList.add('hidden'));
$('cancelTicket').addEventListener('click', () => $('ticketModal').classList.add('hidden'));
$('ticketModal').addEventListener('click', e => { if (e.target === $('ticketModal')) $('ticketModal').classList.add('hidden'); });
$('ticketForm').addEventListener('submit', async e => {
  e.preventDefault(); if (!currentUser || currentUser.role !== 'employee') return;
  try {
    const res = await fetch(`${API}/tickets`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: $('ticketTitle').value.trim(), description: $('ticketDescription').value.trim(), employee_name: currentUser.name, employee_email: currentUser.email }) });
    const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Ticket creation failed');
    $('ticketModal').classList.add('hidden'); toast(`Ticket #${data.id} submitted successfully.`); showView('myTickets'); await loadTickets();
  } catch (err) { toast(`Could not submit ticket: ${err.message}`); }
});
$('refreshTicketsBtn').addEventListener('click', loadTickets);

async function loadTickets() {
  if (!currentUser) return;
  try {
    const query = currentUser.role === 'employee' ? `role=employee&email=${encodeURIComponent(currentUser.email)}` : 'role=it';
    const res = await fetch(`${API}/tickets?${query}`); if (!res.ok) throw new Error('Could not load tickets');
    const tickets = await res.json();
    if (currentUser.role === 'employee') {
      $('ticketCount').textContent = tickets.length;
      renderEmployeeTickets(tickets);
    } else renderITTickets(tickets);
  } catch (err) { if (activeView !== 'assistant') toast(err.message); }
}

function escapeText(value) { return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function dateLabel(value) { try { return new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }); } catch { return value; } }
function statusClass(status) { return status.toLowerCase().replace(/\s+/g, '-'); }
function renderEmployeeTickets(tickets) {
  const host = $('myTicketsList');
  if (!tickets.length) { host.innerHTML = '<div class="empty-state"><div class="empty-icon">▤</div><h3>No tickets yet</h3><p>If the AI assistant cannot resolve your issue, raise a ticket and the technical team will respond here.</p><button class="primary" onclick="openTicketModal()">＋ Raise your first ticket</button></div>'; return; }
  host.innerHTML = tickets.map(t => `<article class="ticket-card"><div class="ticket-top"><div><span class="ticket-id">TICKET #${t.id}</span><h3>${escapeText(t.title)}</h3></div><span class="status-badge ${statusClass(t.status)}">${escapeText(t.status)}</span></div><p class="ticket-description">${escapeText(t.description)}</p><div class="ticket-meta">Created ${escapeText(dateLabel(t.created_at))}</div><div class="conversation"><h4>Conversation with IT</h4>${t.messages.map(m => `<div class="ticket-message ${m.author_role === 'it' ? 'from-it' : ''}"><div class="message-meta"><strong>${escapeText(m.author_name)} ${m.author_role === 'it' ? '· IT Support' : m.author_role === 'employee' ? '· Employee' : ''}</strong><span>${escapeText(dateLabel(m.created_at))}</span></div><p>${escapeText(m.body)}</p></div>`).join('')}</div></article>`).join('');
}
function renderITTickets(tickets) {
    const host = $('itTicketsList');

    // Save currently typed replies before refreshing
    const drafts = {};

    host.querySelectorAll('.reply-form').forEach(form => {
        const id = form.dataset.ticketId;

        drafts[id] = {
            body: form.querySelector('textarea').value,
            status: form.querySelector('select').value
        };
    });

    $('queueSummary').textContent =
        `${tickets.length} ticket${tickets.length === 1 ? '' : 's'} · ${tickets.filter(t => t.status !== 'Resolved').length} need attention`;

    if (!tickets.length) {
        host.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">✓</div>
                <h3>Queue is clear</h3>
                <p>Employee tickets will appear here as soon as they are submitted.</p>
            </div>`;
        return;
    }

    host.innerHTML = tickets.map(t => `
        <article class="ticket-card">
            <div class="ticket-top">
                <div>
                    <span class="ticket-id">TICKET #${t.id}</span>
                    <h3>${escapeText(t.title)}</h3>
                </div>
                <span class="status-badge ${statusClass(t.status)}">
                    ${escapeText(t.status)}
                </span>
            </div>

            <div class="requester">
                <div class="avatar">
                    ${escapeText(t.employee_name.charAt(0).toUpperCase())}
                </div>
                <div>
                    <strong>${escapeText(t.employee_name)}</strong>
                    <small>${escapeText(t.employee_email)}</small>
                </div>
                <span class="ticket-date">
                    ${escapeText(dateLabel(t.created_at))}
                </span>
            </div>

            <p class="ticket-description">
                ${escapeText(t.description)}
            </p>

            <div class="conversation">
                <h4>Ticket conversation</h4>

                ${t.messages.map(m => `
                    <div class="ticket-message ${m.author_role === 'it' ? 'from-it' : ''}">
                        <div class="message-meta">
                            <strong>
                                ${escapeText(m.author_name)} ·
                                ${m.author_role === 'it' ? 'IT Support' : 'Employee'}
                            </strong>
                            <span>${escapeText(dateLabel(m.created_at))}</span>
                        </div>
                        <p>${escapeText(m.body)}</p>
                    </div>
                `).join('')}
            </div>

            <form class="reply-form" data-ticket-id="${t.id}">
                <label for="reply-${t.id}">Reply to employee</label>

                <textarea
                    id="reply-${t.id}"
                    rows="2"
                    required
                    placeholder="Write an update or solution..."
                ></textarea>

                <div class="reply-actions">
                    <select aria-label="Ticket status" class="status-select">
                        <option ${t.status === 'Open' ? 'selected' : ''}>Open</option>
                        <option ${t.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                        <option ${t.status === 'Resolved' ? 'selected' : ''}>Resolved</option>
                    </select>

                    <button class="primary" type="submit">
                        Send reply ↑
                    </button>
                </div>
            </form>
        </article>
    `).join('');

    // Restore previously typed replies
    host.querySelectorAll('.reply-form').forEach(form => {
        const id = form.dataset.ticketId;

        if (drafts[id]) {
            form.querySelector('textarea').value = drafts[id].body;
            form.querySelector('select').value = drafts[id].status;
        }

        form.addEventListener('submit', async e => {
            e.preventDefault();

            const body = form.querySelector('textarea').value.trim();
            const status = form.querySelector('select').value;

            if (!body) return;

            const button = form.querySelector('button');
            button.disabled = true;

            try {
                const res = await fetch(`${API}/tickets/${id}/reply`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        author_name: currentUser.name,
                        body,
                        status
                    })
                });

                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.detail || 'Reply failed');
                }

                toast(`Reply sent to employee for ticket #${id}.`);

                await loadTickets();

            } catch (err) {
                toast(err.message);
                button.disabled = false;
            }
        });
    });
}
let toastTimer;
function toast(message) { $('toast').textContent = message; $('toast').classList.remove('hidden'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.add('hidden'), 3500); }
