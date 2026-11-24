/* Smart Malaysia Travel: History page enhancements (loads AFTER app.js) */
const HISTORY_FESTIVALS = [
    {id:'chinese_new_year',name:'Chinese New Year',emoji:'🧧'},
    {id:'hari_raya',name:'Hari Raya',emoji:'🌙'},
    {id:'deepavali',name:'Deepavali',emoji:'🪔'},
    {id:'christmas',name:'Christmas',emoji:'🎄'}
];
let historyAllRecords = [];
let historySelectedFestival = '';
let historyFiltersReady = false;

function historyLocalParts(entry) {
    const time = new Date(entry.timestamp);
    if (Number.isNaN(time.getTime())) return null;
    return {
        year: String(time.getFullYear()),
        month: String(time.getMonth() + 1),
        date: `${time.getFullYear()}-${String(time.getMonth()+1).padStart(2,'0')}-${String(time.getDate()).padStart(2,'0')}`
    };
}

function updateHistoryChoices() {
    const yearField = document.getElementById('history-year');
    const monthField = document.getElementById('history-month');
    if (!yearField || !monthField) return;
    const oldYear = yearField.value;
    const oldMonth = monthField.value;
    const dates = historyAllRecords.map(historyLocalParts).filter(Boolean);
    const years = [...new Set(dates.map(x=>x.year))].sort((a,b)=>Number(b)-Number(a));
    yearField.replaceChildren(new Option('All Years',''));
    years.forEach(y=>yearField.add(new Option(y,y)));
    yearField.value = years.includes(oldYear) ? oldYear : '';
    const months = [...new Set(dates.filter(x=>!yearField.value || x.year===yearField.value).map(x=>x.month))].sort((a,b)=>Number(a)-Number(b));
    monthField.replaceChildren(new Option('All Months',''));
    months.forEach(m=>monthField.add(new Option(new Date(2024,Number(m)-1,1).toLocaleString('en-MY',{month:'long'}),m)));
    monthField.value = months.includes(oldMonth) ? oldMonth : '';
}

function historyTheme() {
    return festivalMode ? historySelectedFestival : 'normal';
}
function displayFestivalSelectors() {
    const area=document.getElementById('history-festival-options');
    if (!area) return;
    area.classList.toggle('hidden',!festivalMode);
    document.getElementById('history-tab')?.setAttribute('data-history-theme',historyTheme());
    if (!festivalMode) return;
    area.innerHTML = HISTORY_FESTIVALS.map(f=>`
        <button type="button" class="history-festival-card ${historySelectedFestival===f.id?'selected':''}"
            data-history-festival="${f.id}" data-festival-theme="${f.id}"
            aria-pressed="${historySelectedFestival===f.id}">
            <span class="history-festival-emoji">${f.emoji}</span>
            <span>${f.name}</span>
            <small>${historyAllRecords.filter(r=>r.mode==='festival' && r.festival_id===f.id).length} record(s)</small>
        </button>`).join('');
}

function filteredHistory() {
    const year=document.getElementById('history-year')?.value || '';
    const month=document.getElementById('history-month')?.value || '';
    const day=document.getElementById('history-date')?.value || '';
    return historyAllRecords.filter(r=>{
        // Older records had no recorded mode: retain them under Normal as legacy.
        if (festivalMode) {
            if (r.mode!=='festival' || r.festival_id!==historySelectedFestival) return false;
        } else if (r.mode==='festival') return false;
        const d=historyLocalParts(r);
        if (!d) return !year && !month && !day;
        return (!year||year===d.year) && (!month||month===d.month) && (!day||day===d.date);
    });
}


function renderHistoryRecords() {
    const list = document.getElementById('history-list');
    if (!list) return;

    displayFestivalSelectors();

    // Sort ALL saved records from oldest to newest.
    // This keeps numbering continuous even when filtering.
    const allSorted = [...historyAllRecords].sort(
        (a, b) => new Date(a.timestamp) - new Date(b.timestamp)
    );

    const recordNumbers = new Map();

    allSorted.forEach((record, index) => {
        recordNumbers.set(record, index + 1);
    });

    // Display newest records at the TOP.
    const records = filteredHistory().sort(
        (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );

    const count = document.getElementById('history-results-count');

    if (count) {
        count.textContent =
            `Showing ${records.length} matching record(s) · ` +
            `${historyAllRecords.length} total saved`;
    }

    list.replaceChildren();

    if (!records.length) {
        showEmpty(
            list,
            'No recommendations found for this mode, festival or date.'
        );
        return;
    }

    records.forEach((r) => {
        const p = r.preferences || {};

        const names = (r.destination_ids || []).map(id => {
            const destination = allDestinations.find(
                d => d.id === id
            );

            return destination ? destination.name : id;
        });

        // Horizontal destination names with middle dots.
        const destinationsText = names.length
            ? names.map(name => escapeHTML(name)).join(' · ')
            : 'No destinations recommended';

        const d = new Date(r.timestamp);

        const dateText = Number.isNaN(d.getTime())
            ? 'Date unavailable'
            : d.toLocaleString('en-MY');

        // Number #1 = oldest record.
        // Highest number = newest record.
        const number = recordNumbers.get(r);

        const card = document.createElement('div');
        card.className = 'history-item';

        card.innerHTML = `
            <h4>Travel Recommendation #${number}</h4>

            <p>🕒 ${escapeHTML(dateText)}</p>

            <p>
                <strong>Budget:</strong>
                ${escapeHTML(formatMoney(p.budget_rm))}
            </p>

            <p>
                <strong>Duration:</strong>
                ${escapeHTML(p.duration_days)} days
            </p>

            <p>
                <strong>Category:</strong>
                ${escapeHTML(p.destination_category)}
            </p>

            <p>
                <strong>Activities:</strong>
                ${escapeHTML((p.activities || []).join(', ') || 'Any')}
            </p>

            <p>
                <strong>Travel Style:</strong>
                ${escapeHTML(p.travel_style)}
            </p>

            <p>
                <strong>Recommended Destinations:</strong>
            </p>

            <p class="history-destination-names">
                ${destinationsText}
            </p>
        `;

        list.appendChild(card);
    });
}

function initHistoryControls() {
    if (historyFiltersReady) return;
    historyFiltersReady=true;
    document.getElementById('history-year')?.addEventListener('change',()=>{updateHistoryChoices();renderHistoryRecords();});
    document.getElementById('history-month')?.addEventListener('change',renderHistoryRecords);
    document.getElementById('history-date')?.addEventListener('change',renderHistoryRecords);
    document.getElementById('clear-history-filters')?.addEventListener('click',()=>{
        ['history-year','history-month','history-date'].forEach(id=>{
            const el=document.getElementById(id); if(el)el.value='';
        });
        updateHistoryChoices(); renderHistoryRecords();
    });
    document.getElementById('history-festival-options')?.addEventListener('click',event=>{
        const btn=event.target.closest('[data-history-festival]');
        if (!btn) return;
        historySelectedFestival=btn.dataset.historyFestival;
        renderHistoryRecords();
    });
}

// Replaces only the previous History renderer; other app.js functionality is untouched.
loadHistory = async function loadHistoryEnhanced() {
    const list=document.getElementById('history-list');
    if (!list || !currentUser) return;
    showLoading(list);
    initHistoryControls();
    if (!historySelectedFestival) historySelectedFestival=selectedFestivalId || 'deepavali';
    try {
        const records=await apiRequest('/api/user/history');
        historyAllRecords=Array.isArray(records)?records:[];
        if (!allDestinations.length) allDestinations=await apiRequest('/api/travel/destinations');
        updateHistoryChoices();
        renderHistoryRecords();
    } catch(error) {
        showEmpty(list,'Unable to load recommendation history: '+error.message);
        console.error('History load failed:',error);
    }
};
